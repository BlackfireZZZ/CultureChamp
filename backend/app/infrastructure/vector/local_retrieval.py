"""Pinned local retrieval models and authorization-scoped Russian lexical ranking."""

import asyncio
import hashlib
import importlib
import math
import os
import threading
from collections import OrderedDict
from collections.abc import Sequence
from functools import lru_cache
from pathlib import Path
from typing import Any, NoReturn
from uuid import UUID

ENCODER_REPO = "intfloat/multilingual-e5-small"
ENCODER_REVISION = "614241f622f53c4eeff9890bdc4f31cfecc418b3"
RERANKER_REPO = "BAAI/bge-reranker-v2-m3"
RERANKER_REVISION = "953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e"
ENCODER_SHA256 = "1a55775f53449dac10a2bcbc312469fac40b96d53198c407081a831f81c98477"
RERANKER_SHA256 = "d9e3e081faff1eefb84019509b2f5558fd74c1a05a2c7db22f74174fcedb5286"
DIMENSIONS = 384
MAX_TOKENS = 512
_MODEL_LOCK = threading.RLock()


def _unavailable(message: str, error: Exception) -> NoReturn:
    # Imported only on failure so the existing adapter can delegate here lazily.
    from app.infrastructure.vector.text_vectors import VectorUnavailable
    raise VectorUnavailable(message) from error


def _snapshot(repo: str, revision: str, cache_dir: str | None) -> str:
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
    os.environ["DO_NOT_TRACK"] = "1"
    hub = importlib.import_module("huggingface_hub")
    path = str(hub.snapshot_download(repo, revision=revision, cache_dir=cache_dir,
                                   local_files_only=True, allow_patterns=["config.json"]))
    if Path(path).name != revision:
        raise ValueError("Local retrieval model revision mismatch")
    return path


def _verify_weights(snapshot: str, expected_hash: str) -> None:
    with (Path(snapshot) / "model.safetensors").open("rb") as handle:
        actual_hash = hashlib.file_digest(handle, "sha256").hexdigest()
    if actual_hash != expected_hash:
        raise ValueError("Local retrieval model weights mismatch")


@lru_cache(maxsize=4)
def _load_model(kind: str, cache_dir: str | None, device: str) -> Any:
    # Callers hold the process lock across both loading and inference.
    repo = ENCODER_REPO if kind == "encoder" else RERANKER_REPO
    revision = ENCODER_REVISION if kind == "encoder" else RERANKER_REVISION
    path = _snapshot(repo, revision, cache_dir)
    _verify_weights(path, ENCODER_SHA256 if kind == "encoder" else RERANKER_SHA256)
    torch = importlib.import_module("torch")
    sentence_transformers = importlib.import_module("sentence_transformers")
    dtype = torch.float16 if device.startswith("cuda") else torch.float32
    options = {"device": device, "local_files_only": True, "trust_remote_code": False,
               "model_kwargs": {"dtype": dtype}}
    if kind == "encoder":
        model = sentence_transformers.SentenceTransformer(path, **options)
        model.max_seq_length = MAX_TOKENS
    else:
        model = sentence_transformers.CrossEncoder(path, max_length=MAX_TOKENS, **options)
    return model


def _vectors(texts: Sequence[str], prefix: str, cache_dir: str | None,
             device: str) -> list[list[float]]:
    with _MODEL_LOCK:
        model = _load_model("encoder", cache_dir, device)
        output = model.encode([prefix + text for text in texts], batch_size=16,
                              normalize_embeddings=True, convert_to_numpy=True,
                              show_progress_bar=False)
        vectors = [[float(value) for value in row] for row in output]
        if len(vectors) != len(texts) or any(
            len(row) != DIMENSIONS or not all(math.isfinite(value) for value in row)
            or not any(row) for row in vectors
        ):
            raise ValueError("Invalid local embedding output")
        return vectors


class LocalE5Embedder:
    def __init__(self, cache_dir: str | None = None, device: str = "cpu") -> None:
        self.cache_dir = cache_dir
        self.device = device

    async def query(self, text: str) -> list[float]:
        try:
            return (await asyncio.to_thread(
                _vectors, [text], "query: ", self.cache_dir, self.device
            ))[0]
        except Exception as exc:
            _unavailable("Local text embedding unavailable", exc)

    async def passages(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []
        try:
            return await asyncio.to_thread(
                _vectors, tuple(texts), "passage: ", self.cache_dir, self.device
            )
        except Exception as exc:
            _unavailable("Local text embedding unavailable", exc)


class LocalCrossEncoderReranker:
    def __init__(self, cache_dir: str | None = None, device: str = "cpu") -> None:
        self.cache_dir = cache_dir
        self.device = device

    def _scores(self, query: str, passages: Sequence[str]) -> list[float]:
        with _MODEL_LOCK:
            model = _load_model("reranker", self.cache_dir, self.device)
            output = model.predict([(query, passage) for passage in passages],
                                   batch_size=16, show_progress_bar=False)
            scores = [float(value) for value in output]
            if len(scores) != len(passages) or not all(math.isfinite(value) for value in scores):
                raise ValueError("Invalid local reranker output")
            return scores

    async def rerank(self, query: str, passages: Sequence[str]) -> list[float]:
        if not passages:
            return []
        try:
            return await asyncio.to_thread(self._scores, query, tuple(passages))
        except Exception as exc:
            _unavailable("Local passage reranking unavailable", exc)


class RussianBM25:
    """Bounded cache keyed by the exact currently visible (ID, text) sequence.

    A changed authorization list builds a distinct index. No score threshold is
    applied; ties follow the provided row order, including zero-score neighbors.
    """

    def __init__(self, max_cached_indexes: int = 2) -> None:
        if max_cached_indexes < 1:
            raise ValueError("At least one lexical cache entry is required")
        self.max_cached_indexes = max_cached_indexes
        self._indexes: OrderedDict[tuple[tuple[UUID, str], ...], Any] = OrderedDict()
        self._lock = threading.RLock()

    def rank(self, query: str, rows: Sequence[tuple[UUID, str]], limit: int = 50) -> list[UUID]:
        if limit < 0:
            raise ValueError("Lexical limit cannot be negative")
        if not rows or limit == 0:
            return []
        immutable_rows = tuple(rows)
        if len({row[0] for row in immutable_rows}) != len(immutable_rows):
            raise ValueError("Duplicate lexical passage IDs")
        try:
            with self._lock:
                bm25s = importlib.import_module("bm25s")
                stemmer = importlib.import_module("Stemmer").Stemmer("russian")
                index = self._indexes.get(immutable_rows)
                if index is None:
                    tokens = bm25s.tokenize([text for _, text in immutable_rows],
                                            stemmer=stemmer, stopwords=[], show_progress=False)
                    index = bm25s.BM25()
                    index.index(tokens, show_progress=False)
                    self._indexes[immutable_rows] = index
                    if len(self._indexes) > self.max_cached_indexes:
                        self._indexes.popitem(last=False)
                self._indexes.move_to_end(immutable_rows)
                query_tokens = bm25s.tokenize([query], stemmer=stemmer, stopwords=[],
                                              return_ids=False, show_progress=False)
                scores = index.get_scores(query_tokens[0])
                order = sorted(range(len(immutable_rows)), key=lambda i: (-float(scores[i]), i))
                return [immutable_rows[i][0] for i in order[:limit]]
        except Exception as exc:
            _unavailable("Local lexical search unavailable", exc)
