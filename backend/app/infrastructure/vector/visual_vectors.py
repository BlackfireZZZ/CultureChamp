"""Pinned local CLIP embeddings in an independent visual Qdrant collection."""

import asyncio
import hashlib
import os
from functools import lru_cache
from pathlib import Path
from uuid import UUID

import httpx

from app.infrastructure.vector.text_vectors import VectorUnavailable

MODEL_ID = "Qdrant/clip-ViT-B-32:embedded-png-rgb-v1"
COLLECTION = "culture_visual_clip_vit_b32_v1"
VECTOR_NAME = "visual_clip_vit_b32_v1"
DIMENSIONS = 512
TEXT_REVISION = "48ca1db27cb4063eb311ec2aa7f087a808112876"
TEXT_SHA256 = "4dbe762b11e36488304471e439cde89da053ad7acaddbf9e096745d142ec8d8b"
IMAGE_REVISION = "e0c24ed0fa57fa3e4f97f30de74c51d944036ace"
IMAGE_SHA256 = "c68d3d9a200ddd2a8c8a5510b576d4c94d1ae383bf8b36dd8c084f94e1fb4d63"


def _verified(model: object, revision: str, sha256: str) -> object:
    directory = Path(model.model._model_dir)  # type: ignore[attr-defined]
    if directory.name != revision:
        raise VectorUnavailable("Visual model revision mismatch")
    with (directory / "model.onnx").open("rb") as stream:
        if hashlib.file_digest(stream, "sha256").hexdigest() != sha256:
            raise VectorUnavailable("Visual model weights mismatch")
    return model


@lru_cache(maxsize=1)
def _text_model() -> object:
    from fastembed import TextEmbedding

    return _verified(
        TextEmbedding("Qdrant/clip-ViT-B-32-text", cache_dir=os.getenv("EMBEDDING_CACHE_ROOT")),
        TEXT_REVISION,
        TEXT_SHA256,
    )


@lru_cache(maxsize=1)
def _image_model() -> object:
    from fastembed import ImageEmbedding

    return _verified(
        ImageEmbedding("Qdrant/clip-ViT-B-32-vision", cache_dir=os.getenv("EMBEDDING_CACHE_ROOT")),
        IMAGE_REVISION,
        IMAGE_SHA256,
    )


class LocalVisualEmbedder:
    async def query(self, text: str) -> list[float]:
        try:
            return await asyncio.to_thread(
                lambda: next(_text_model().embed([text])).tolist()  # type: ignore[attr-defined]
            )
        except Exception as exc:
            raise VectorUnavailable("Visual text embedding unavailable") from exc

    async def images(self, paths: list[str]) -> list[list[float]]:
        try:
            return await asyncio.to_thread(
                lambda: [vector.tolist() for vector in _image_model().embed(paths)]  # type: ignore[attr-defined]
            )
        except Exception as exc:
            raise VectorUnavailable("Visual image embedding unavailable") from exc


class QdrantVisualIndex:
    def __init__(self, url: str, embedder: LocalVisualEmbedder) -> None:
        self.url = url.rstrip("/")
        self.embedder = embedder

    async def exists(self) -> bool:
        async with httpx.AsyncClient(timeout=15) as client:
            try:
                response = await client.get(f"{self.url}/collections/{COLLECTION}")
                if response.status_code == 404:
                    return False
                response.raise_for_status()
                vectors = response.json()["result"]["config"]["params"]["vectors"]
                if vectors.get(VECTOR_NAME, {}).get("size") != DIMENSIONS:
                    raise VectorUnavailable("Visual collection model mismatch")
                return True
            except (httpx.HTTPError, KeyError, TypeError, ValueError) as exc:
                raise VectorUnavailable("Visual collection unavailable") from exc

    async def ensure(self) -> None:
        if await self.exists():
            return
        async with httpx.AsyncClient(timeout=15) as client:
            try:
                response = await client.put(
                    f"{self.url}/collections/{COLLECTION}",
                    json={"vectors": {VECTOR_NAME: {"size": DIMENSIONS, "distance": "Cosine"}}},
                )
                response.raise_for_status()
                response = await client.put(
                    f"{self.url}/collections/{COLLECTION}/index?wait=true",
                    json={"field_name": "revision_id", "field_schema": "uuid"},
                )
                response.raise_for_status()
            except httpx.HTTPError as exc:
                raise VectorUnavailable("Visual collection unavailable") from exc

    async def upsert(self, points: list[tuple[UUID, UUID, str]]) -> None:
        if not points:
            return
        await self.ensure()
        vectors = await self.embedder.images([path for _, _, path in points])
        if len(vectors) != len(points) or any(len(vector) != DIMENSIONS for vector in vectors):
            raise VectorUnavailable("Visual embedding dimension mismatch")
        async with httpx.AsyncClient(timeout=30) as client:
            try:
                for start in range(0, len(points), 32):
                    batch = points[start : start + 32]
                    response = await client.put(
                        f"{self.url}/collections/{COLLECTION}/points?wait=true",
                        json={
                            "points": [
                                {
                                    "id": str(point_id),
                                    "vector": {VECTOR_NAME: vector},
                                    "payload": {"revision_id": str(revision_id)},
                                }
                                for (point_id, revision_id, _), vector in zip(
                                    batch, vectors[start : start + 32], strict=True
                                )
                            ]
                        },
                    )
                    response.raise_for_status()
            except httpx.HTTPError as exc:
                raise VectorUnavailable("Visual indexing unavailable") from exc

    async def delete(self, ids: list[UUID]) -> None:
        if not ids:
            return
        async with httpx.AsyncClient(timeout=15) as client:
            try:
                response = await client.post(
                    f"{self.url}/collections/{COLLECTION}/points/delete?wait=true",
                    json={"points": [str(item) for item in ids]},
                )
                response.raise_for_status()
            except httpx.HTTPError as exc:
                raise VectorUnavailable("Visual cleanup unavailable") from exc

    async def query(self, text: str, revisions: list[UUID], limit: int) -> list[tuple[UUID, float]]:
        if not revisions or not await self.exists():
            return []
        vector = await self.embedder.query(text)
        async with httpx.AsyncClient(timeout=15) as client:
            try:
                response = await client.post(
                    f"{self.url}/collections/{COLLECTION}/points/query",
                    json={
                        "query": vector,
                        "using": VECTOR_NAME,
                        "limit": limit,
                        "with_payload": False,
                        "filter": {
                            "must": [
                                {
                                    "key": "revision_id",
                                    "match": {"any": [str(item) for item in revisions]},
                                }
                            ]
                        },
                    },
                )
                response.raise_for_status()
                return [
                    (UUID(str(point["id"])), float(point["score"]))
                    for point in response.json()["result"]["points"]
                ]
            except (httpx.HTTPError, KeyError, TypeError, ValueError) as exc:
                raise VectorUnavailable("Visual search unavailable") from exc

    async def has_points(self, revision_id: UUID, ids: list[UUID]) -> bool:
        async with httpx.AsyncClient(timeout=15) as client:
            try:
                response = await client.post(
                    f"{self.url}/collections/{COLLECTION}/points/count",
                    json={
                        "filter": {
                            "must": [{"key": "revision_id", "match": {"value": str(revision_id)}}]
                        },
                        "exact": True,
                    },
                )
                response.raise_for_status()
                if int(response.json()["result"]["count"]) != len(ids):
                    return False
                if not ids:
                    return True
                response = await client.post(
                    f"{self.url}/collections/{COLLECTION}/points",
                    json={
                        "ids": [str(item) for item in ids],
                        "with_payload": True,
                        "with_vector": False,
                    },
                )
                response.raise_for_status()
                found = {
                    UUID(str(point["id"])): point["payload"]["revision_id"]
                    for point in response.json()["result"]
                }
                return all(found.get(item) == str(revision_id) for item in ids)
            except (httpx.HTTPError, KeyError, TypeError, ValueError) as exc:
                raise VectorUnavailable("Visual audit unavailable") from exc
