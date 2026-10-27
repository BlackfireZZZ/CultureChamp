"""Download explicitly pinned public weights; never read or upload the private corpus."""

import argparse
from pathlib import Path

from .runner import MODEL_REVISIONS, MODELS


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-cache-dir", type=Path, required=True)
    parser.add_argument("--models", nargs="+", choices=[*MODELS, "reranker"],
                        default=["e5-small", "reranker"])
    args = parser.parse_args()
    from huggingface_hub import snapshot_download
    for alias in args.models:
        repo = "BAAI/bge-reranker-v2-m3" if alias == "reranker" else MODELS[alias]
        weight = "pytorch_model.bin" if alias == "bge-m3" else "model.safetensors"
        path = snapshot_download(
            repo, revision=MODEL_REVISIONS[repo], cache_dir=str(args.model_cache_dir),
            allow_patterns=[weight, "*.json", "*.txt", "*.model", "1_Pooling/*"],
            ignore_patterns=["onnx/*", "openvino/*", ".eval_results/*"],
        )
        print(f"{repo}@{MODEL_REVISIONS[repo]}: {path}")


if __name__ == "__main__":
    main()
