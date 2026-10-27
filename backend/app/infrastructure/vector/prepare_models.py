"""Explicit weight provisioning; inference itself remains offline and local."""

import os
from pathlib import Path

from app.core.config import settings
from app.infrastructure.vector.local_retrieval import (
    ENCODER_REPO,
    ENCODER_REVISION,
    ENCODER_SHA256,
    RERANKER_REPO,
    RERANKER_REVISION,
    RERANKER_SHA256,
    _verify_weights,
)

PATTERNS = ["model.safetensors", "*.json", "*.txt", "*.model", "1_Pooling/*"]


def _validate_snapshot(path: str, repo: str, digest: str) -> None:
    required = ["config.json", "tokenizer.json", "tokenizer_config.json",
                "special_tokens_map.json", "sentencepiece.bpe.model"]
    if repo == ENCODER_REPO:
        required += ["modules.json", "sentence_bert_config.json", "1_Pooling/config.json"]
    for name in required:
        if not (Path(path) / name).is_file():
            raise FileNotFoundError(f"Missing local retrieval artifact: {name}")
    _verify_weights(path, digest)


def main() -> None:
    os.environ["HF_HUB_OFFLINE"] = "0"
    os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
    from huggingface_hub import snapshot_download

    for repo, revision, digest in (
        (ENCODER_REPO, ENCODER_REVISION, ENCODER_SHA256),
        (RERANKER_REPO, RERANKER_REVISION, RERANKER_SHA256),
    ):
        try:
            cached = snapshot_download(
                repo, revision=revision, cache_dir=settings.retrieval_model_cache,
                local_files_only=True, allow_patterns=PATTERNS,
                ignore_patterns=["onnx/*", "openvino/*", ".eval_results/*"],
            )
            _validate_snapshot(cached, repo, digest)
        except FileNotFoundError:
            pass
        else:
            print(f"Verified cached retrieval weights: {repo}@{revision}")
            continue
        path = snapshot_download(
            repo, revision=revision, cache_dir=settings.retrieval_model_cache,
            allow_patterns=PATTERNS,
            ignore_patterns=["onnx/*", "openvino/*", ".eval_results/*"],
        )
        _validate_snapshot(path, repo, digest)
        print(f"Prepared local retrieval weights: {repo}@{revision}")


if __name__ == "__main__":
    main()
