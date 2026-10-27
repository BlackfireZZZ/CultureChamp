"""Local model contracts without weights, plus lexical authorization counterexamples."""

import asyncio
import os
import sys
import threading
import time
from types import SimpleNamespace
from uuid import UUID

import pytest

from app.infrastructure.vector import local_retrieval as local
from app.infrastructure.vector.text_vectors import VectorUnavailable


@pytest.fixture(autouse=True)
def isolated_models():
    local._load_model.cache_clear()
    yield
    local._load_model.cache_clear()


def test_embeddings_prefix_normalization_reuse_and_context(monkeypatch):
    calls = []
    constructors = []

    class Model:
        max_seq_length = 0

        def encode(self, texts, **kwargs):
            assert self.max_seq_length == 512
            calls.append((texts, kwargs))
            return [[0.25] * 384 for _ in texts]

    def constructor(path, **kwargs):
        constructors.append((path, kwargs))
        return Model()

    monkeypatch.setattr(local, "_snapshot", lambda *args: "/cached/pinned")
    hashes = []
    monkeypatch.setattr(local, "_verify_weights", lambda path, expected: hashes.append(expected))
    monkeypatch.setitem(sys.modules, "torch", SimpleNamespace(float16="fp16", float32="fp32"))
    monkeypatch.setitem(sys.modules, "sentence_transformers", SimpleNamespace(
        SentenceTransformer=constructor))

    async def run():
        first = local.LocalE5Embedder("private-models", "cuda:0")
        second = local.LocalE5Embedder("private-models", "cuda:0")
        assert len(await first.query("традиция")) == 384
        assert len(await second.passages(["один", "два"])) == 2
        assert await first.passages([]) == []
    asyncio.run(run())
    assert len(constructors) == 1
    assert hashes == [local.ENCODER_SHA256]
    assert constructors[0][1] == {"device": "cuda:0", "local_files_only": True,
                                   "trust_remote_code": False,
                                   "model_kwargs": {"dtype": "fp16"}}
    assert calls[0][0] == ["query: традиция"]
    assert calls[1][0] == ["passage: один", "passage: два"]
    assert all(options["normalize_embeddings"] for _, options in calls)


def test_pinned_snapshot_never_downloads_or_accepts_another_revision(monkeypatch):
    calls = []

    def download(repo, **kwargs):
        calls.append((repo, kwargs))
        return "/cache/snapshots/" + local.ENCODER_REVISION

    monkeypatch.setitem(sys.modules, "huggingface_hub", SimpleNamespace(snapshot_download=download))
    assert local._snapshot(local.ENCODER_REPO, local.ENCODER_REVISION, "/private") == (
        "/cache/snapshots/" + local.ENCODER_REVISION)
    assert calls == [(local.ENCODER_REPO, {"revision": local.ENCODER_REVISION,
                     "cache_dir": "/private", "local_files_only": True,
                     "allow_patterns": ["config.json"]})]
    assert os.environ["HF_HUB_OFFLINE"] == os.environ["HF_HUB_DISABLE_TELEMETRY"] == "1"
    monkeypatch.setitem(sys.modules, "huggingface_hub", SimpleNamespace(
        snapshot_download=lambda *a, **kw: "/cache/other"))
    with pytest.raises(ValueError, match="revision mismatch"):
        local._snapshot(local.ENCODER_REPO, local.ENCODER_REVISION, None)


def test_embedding_output_and_loader_fail_closed(monkeypatch):
    for output in ([], [[1.0]], [[float("nan")] * 384], [[0.0] * 384]):
        monkeypatch.setattr(local, "_load_model", lambda *a, value=output: SimpleNamespace(
            encode=lambda *a, **kw: value))
        with pytest.raises(VectorUnavailable, match="embedding unavailable"):
            asyncio.run(local.LocalE5Embedder().query("query"))


def test_model_calls_are_serialized_across_instances(monkeypatch):
    state = {"active": 0, "maximum": 0}
    guard = threading.Lock()

    def encode(texts, **kwargs):
        with guard:
            state["active"] += 1
            state["maximum"] = max(state["maximum"], state["active"])
        time.sleep(0.01)
        with guard:
            state["active"] -= 1
        return [[0.25] * 384 for _ in texts]

    monkeypatch.setattr(local, "_load_model", lambda *a: SimpleNamespace(encode=encode))

    async def run():
        await asyncio.gather(*(local.LocalE5Embedder().query(str(i)) for i in range(4)))
    asyncio.run(run())
    assert state["maximum"] == 1


def test_reranker_preserves_pair_order_and_validates_scores(monkeypatch):
    calls = []

    def predict(pairs, **kwargs):
        calls.append((pairs, kwargs))
        return [0.2, 0.8]

    monkeypatch.setattr(local, "_load_model", lambda *a: SimpleNamespace(predict=predict))
    reranker = local.LocalCrossEncoderReranker()
    assert asyncio.run(reranker.rerank("query", ["first", "second"])) == [0.2, 0.8]
    assert calls[0][0] == [("query", "first"), ("query", "second")]
    assert asyncio.run(reranker.rerank("query", [])) == []
    for values in ([0.1], [0.1, float("inf")]):
        monkeypatch.setattr(local, "_load_model", lambda *a, output=values: SimpleNamespace(
            predict=lambda *a, **kw: output))
        with pytest.raises(VectorUnavailable, match="reranking unavailable"):
            asyncio.run(reranker.rerank("query", ["first", "second"]))


def test_bm25_russian_morphology_visibility_and_bounded_cache():
    pytest.importorskip("bm25s")
    pytest.importorskip("Stemmer")
    first, second, third = UUID(int=1), UUID(int=2), UUID(int=3)
    ranker = local.RussianBM25(max_cached_indexes=1)
    rows = [(first, "река широкая"), (second, "народная культура"), (third, "птица")]
    assert ranker.rank("культуры", rows, 1) == [second]
    cached = next(iter(ranker._indexes.values()))
    assert ranker.rank("культуры", rows, 3)[0] == second
    assert next(iter(ranker._indexes.values())) is cached
    # Revoked second row must not survive the previous cached index.
    assert second not in ranker.rank("культуры", [rows[0], rows[2]])
    assert len(ranker._indexes) == 1
    changed_text = [(first, "народная культура"), rows[2]]
    assert ranker.rank("культуры", changed_text, 1) == [first]
    assert len(ranker._indexes) == 1


def test_bm25_zero_score_ties_keep_input_order_without_threshold():
    pytest.importorskip("bm25s")
    pytest.importorskip("Stemmer")
    rows = [(UUID(int=i), "один") for i in (3, 2, 1)]
    ranker = local.RussianBM25()
    assert ranker.rank("несуществующий", rows) == [row[0] for row in rows]
    assert ranker.rank("query", []) == []
    assert ranker.rank("query", rows, 0) == []
    with pytest.raises(ValueError, match="Duplicate"):
        ranker.rank("query", [rows[0], rows[0]])


def test_corrupt_local_weights_fail_before_model_loading(monkeypatch, tmp_path):
    import hashlib
    weights = tmp_path / "model.safetensors"
    weights.write_bytes(b"self authored fixture")
    expected = hashlib.sha256(weights.read_bytes()).hexdigest()
    local._verify_weights(str(tmp_path), expected)
    weights.write_bytes(b"corrupted fixture")
    with pytest.raises(ValueError, match="weights mismatch"):
        local._verify_weights(str(tmp_path), expected)
    monkeypatch.setattr(local, "_snapshot", lambda *args: str(tmp_path))
    with pytest.raises(VectorUnavailable, match="embedding unavailable"):
        asyncio.run(local.LocalE5Embedder().query("query"))
