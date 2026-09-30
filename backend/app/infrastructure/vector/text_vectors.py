"""Versioned local text embeddings and Qdrant candidate index."""

import asyncio
import hashlib
import os
from collections.abc import Sequence
from functools import lru_cache
from pathlib import Path
from typing import Protocol
from uuid import UUID

import httpx

MODEL_REVISION = "614241f622f53c4eeff9890bdc4f31cfecc418b3"
MODEL_SHA256 = "4654c156f3e4171abc9c716cdb771bf9116455d15ac1aab364aeeede0e3205b0"
MODEL_ID = f"intfloat/multilingual-e5-small@{MODEL_REVISION}:onnx-O4:passage-query"
COLLECTION = "culture_text_e5_small_v1"
VECTOR_NAME = "text_e5_small_v1"
DIMENSIONS = 384
MIN_TEXT_COSINE = 0.84  # Provisional internal gate; replace after expert-labelled calibration.
UPSERT_BATCH_SIZE = 128
DELETE_BATCH_SIZE = 256


class VectorUnavailable(Exception):
    pass


class TextEmbedder(Protocol):
    async def query(self, text: str) -> list[float]: ...

    async def passages(self, texts: Sequence[str]) -> list[list[float]]: ...


@lru_cache(maxsize=1)
def _model():  # type: ignore[no-untyped-def]
    from fastembed import TextEmbedding
    from fastembed.common.model_description import ModelSource, PoolingType

    TextEmbedding.add_custom_model(
        model=MODEL_ID,
        pooling=PoolingType.MEAN,
        normalization=True,
        sources=ModelSource(hf="intfloat/multilingual-e5-small"),
        dim=DIMENSIONS,
        model_file="onnx/model_O4.onnx",
    )
    cache_dir = os.getenv("EMBEDDING_CACHE_ROOT")
    model = TextEmbedding(model_name=MODEL_ID, cache_dir=cache_dir)
    model_dir = Path(model.model._model_dir)
    weights = model_dir / "onnx" / "model_O4.onnx"
    if model_dir.name != MODEL_REVISION:
        raise VectorUnavailable("Embedding model revision mismatch")
    with weights.open("rb") as stream:
        if hashlib.file_digest(stream, "sha256").hexdigest() != MODEL_SHA256:
            raise VectorUnavailable("Embedding model weights mismatch")
    return model


class LocalTextEmbedder:
    async def query(self, text: str) -> list[float]:
        try:
            return await asyncio.to_thread(
                lambda: list(_model().embed([f"query: {text}"]))[0].tolist()
            )
        except Exception as exc:
            raise VectorUnavailable("Text embedding unavailable") from exc

    async def passages(self, texts: Sequence[str]) -> list[list[float]]:
        try:
            return await asyncio.to_thread(
                lambda: [vector.tolist() for vector in _model().embed(
                    [f"passage: {text}" for text in texts]
                )]
            )
        except Exception as exc:
            raise VectorUnavailable("Text embedding unavailable") from exc


class QdrantTextIndex:
    def __init__(self, url: str, embedder: TextEmbedder, collection: str = COLLECTION) -> None:
        self.url = url.rstrip("/")
        self.embedder = embedder
        self.collection = collection

    async def ensure_collection(self, *, create: bool = True) -> None:
        async with httpx.AsyncClient(timeout=15) as client:
            try:
                response = await client.get(f"{self.url}/collections/{self.collection}")
                if response.status_code == 200:
                    result = response.json()["result"]
                    vectors = result["config"]["params"]["vectors"]
                    if vectors.get(VECTOR_NAME, {}).get("size") != DIMENSIONS:
                        raise VectorUnavailable("Vector collection model mismatch")
                    schema = result["payload_schema"].get("revision_id")
                    if schema is not None and schema.get("data_type") != "uuid":
                        raise VectorUnavailable("Vector revision index type mismatch")
                    if schema is not None:
                        return
                    if not create:
                        raise VectorUnavailable("Vector revision index is missing")
                else:
                    if response.status_code != 404:
                        response.raise_for_status()
                    if not create:
                        raise VectorUnavailable("Vector collection is missing")
                    response = await client.put(
                        f"{self.url}/collections/{self.collection}",
                        json={"vectors": {VECTOR_NAME: {"size": DIMENSIONS,
                                                        "distance": "Cosine"}}},
                    )
                    response.raise_for_status()
                response = await client.put(
                    f"{self.url}/collections/{self.collection}/index?wait=true",
                    json={"field_name": "revision_id", "field_schema": "uuid"},
                )
                response.raise_for_status()
            except (httpx.HTTPError, KeyError, TypeError, ValueError) as exc:
                raise VectorUnavailable("Vector index unavailable") from exc

    async def collection_exists(self) -> bool:
        async with httpx.AsyncClient(timeout=15) as client:
            try:
                response = await client.get(f"{self.url}/collections/{self.collection}")
                if response.status_code == 404:
                    return False
                response.raise_for_status()
                vectors = response.json()["result"]["config"]["params"]["vectors"]
                if vectors.get(VECTOR_NAME, {}).get("size") != DIMENSIONS:
                    raise VectorUnavailable("Vector collection model mismatch")
                return True
            except (httpx.HTTPError, KeyError, TypeError, ValueError) as exc:
                raise VectorUnavailable("Vector index unavailable") from exc

    async def upsert(self, segments: Sequence[tuple[UUID, UUID, str]]) -> None:
        if not segments:
            return
        await self.ensure_collection()
        async with httpx.AsyncClient(timeout=30) as client:
            try:
                for start in range(0, len(segments), UPSERT_BATCH_SIZE):
                    batch = segments[start:start + UPSERT_BATCH_SIZE]
                    vectors = await self.embedder.passages([text for _, _, text in batch])
                    if len(vectors) != len(batch) or any(
                        len(vector) != DIMENSIONS for vector in vectors
                    ):
                        raise VectorUnavailable("Embedding dimension mismatch")
                    points = [
                        {"id": str(segment_id), "vector": {VECTOR_NAME: vector},
                         "payload": {"revision_id": str(revision_id)}}
                        for (segment_id, revision_id, _), vector in zip(batch, vectors, strict=True)
                    ]
                    response = await client.put(
                        f"{self.url}/collections/{self.collection}/points?wait=true",
                        json={"points": points},
                    )
                    response.raise_for_status()
            except httpx.HTTPError as exc:
                raise VectorUnavailable("Vector indexing unavailable") from exc

    async def query(
        self, text: str, limit: int, *, allowed_revision_ids: Sequence[UUID] | None = None
    ) -> tuple[tuple[UUID, float], ...]:
        if allowed_revision_ids is not None and not allowed_revision_ids:
            return ()
        await self.ensure_collection(create=False)
        vector = await self.embedder.query(text)
        if len(vector) != DIMENSIONS:
            raise VectorUnavailable("Embedding dimension mismatch")
        async with httpx.AsyncClient(timeout=15) as client:
            try:
                body: dict[str, object] = {
                    "query": vector, "using": VECTOR_NAME, "limit": limit,
                    "with_payload": False,
                }
                if allowed_revision_ids is not None:
                    body["filter"] = {"must": [{"key": "revision_id", "match": {
                        "any": [str(item) for item in allowed_revision_ids]
                    }}]}
                response = await client.post(
                    f"{self.url}/collections/{self.collection}/points/query",
                    json=body,
                )
                response.raise_for_status()
                return tuple(
                    (UUID(str(point["id"])), float(point["score"]))
                    for point in response.json()["result"]["points"]
                )
            except (httpx.HTTPError, KeyError, TypeError, ValueError) as exc:
                raise VectorUnavailable("Vector search unavailable") from exc

    async def delete(self, segment_ids: Sequence[UUID]) -> None:
        if not segment_ids:
            return
        async with httpx.AsyncClient(timeout=15) as client:
            try:
                for start in range(0, len(segment_ids), DELETE_BATCH_SIZE):
                    batch = segment_ids[start:start + DELETE_BATCH_SIZE]
                    response = await client.post(
                        f"{self.url}/collections/{self.collection}/points/delete?wait=true",
                        json={"points": [str(item) for item in batch]},
                    )
                    response.raise_for_status()
            except httpx.HTTPError as exc:
                raise VectorUnavailable("Vector cleanup unavailable") from exc

    async def has_revision_points(self, revision_id: UUID, segment_ids: Sequence[UUID]) -> bool:
        if not segment_ids:
            return True
        async with httpx.AsyncClient(timeout=15) as client:
            try:
                for start in range(0, len(segment_ids), 256):
                    batch = segment_ids[start:start + 256]
                    response = await client.post(
                        f"{self.url}/collections/{self.collection}/points",
                        json={"ids": [str(item) for item in batch],
                              "with_payload": True, "with_vector": False},
                    )
                    response.raise_for_status()
                    found = {
                        UUID(str(point["id"])): point["payload"]["revision_id"]
                        for point in response.json()["result"]
                    }
                    if any(found.get(item) != str(revision_id) for item in batch):
                        return False
                return True
            except (httpx.HTTPError, KeyError, TypeError, ValueError) as exc:
                raise VectorUnavailable("Vector audit unavailable") from exc
