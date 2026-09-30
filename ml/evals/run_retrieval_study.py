"""Offline, same-fixture model/chunk ablation; never publish held source text."""

import argparse
import asyncio
import csv
import hashlib
import json
import os
import resource
from pathlib import Path
from statistics import mean
from time import perf_counter
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

import httpx
from app.infrastructure.ingestion.chunking import chunk_text
from app.infrastructure.ingestion.isolated_pdf import extract_pdf_isolated
from app.infrastructure.vector.text_vectors import _model
from fastembed import TextEmbedding
from retrieval_eval import load_cases, summarize
from study_chunking import block_token_windows, docling_pages, sentence_token_windows, token_count

ROOT = Path(__file__).resolve().parents[2]
MODELS = {
    "e5-small": ("intfloat/multilingual-e5-small", 384, 512),
    "e5-large-fp16": ("intfloat/multilingual-e5-large", 1024, 512),
    "qwen3-0.6b-int8": ("Qwen/Qwen3-Embedding-0.6B-Q", 1024, 32768),
    "bge-m3-fp16": ("BAAI/bge-m3", 1024, 8192),
}
INSTRUCTION = "Retrieve evidence from Russian scholarly cultural sources for the user question."


def _load_model(name: str):  # type: ignore[no-untyped-def]
    if name == "e5-small":
        return _model()
    if name in {"e5-large-fp16", "bge-m3-fp16"}:
        import torch
        from sentence_transformers import SentenceTransformer

        if not torch.cuda.is_available():
            raise RuntimeError("FP16 GPU experiment requires CUDA")
        return SentenceTransformer(
            MODELS[name][0], device="cuda", model_kwargs={"torch_dtype": torch.float16}
        )
    return TextEmbedding(model_name=MODELS[name][0], cache_dir=os.getenv("EMBEDDING_CACHE_ROOT"))


def _prefix(name: str, text: str, *, query: bool) -> str:
    if name == "bge-m3-fp16":
        return text
    if name.startswith("e5-"):
        return f"{'query' if query else 'passage'}: {text}"
    return f"Instruct: {INSTRUCTION}\nQuery: {text}" if query else text


def _encode(model, model_name: str, inputs: list[str]):  # type: ignore[no-untyped-def]
    if model_name in {"e5-large-fp16", "bge-m3-fp16"}:
        return list(model.encode(inputs, batch_size=8, normalize_embeddings=True))
    return list(model.embed(inputs))


async def run(
    model_name: str,
    chunking: str,
    vector_url: str,
    output: Path,
    docling_dir: Path | None,
    review_csv: Path | None,
) -> None:
    if review_csv is not None and review_csv.resolve().is_relative_to(ROOT):
        raise ValueError("review CSV with held source text must stay outside the repository")
    load_started = perf_counter()
    model = await asyncio.to_thread(_load_model, model_name)
    load_seconds = perf_counter() - load_started
    gpu_model = model_name in {"e5-large-fp16", "bge-m3-fp16"}
    tokenizer = model.tokenizer if gpu_model else model.model.tokenizer
    manifest = json.loads((ROOT / "ml/evals/manifest.json").read_text(encoding="utf-8"))
    cases = load_cases(ROOT / "ml/evals/qrels.jsonl")
    rows: list[tuple[str, str]] = []
    page_count = 0
    for source_id, relative_path in manifest["source_files"].items():
        data = (ROOT / relative_path).read_bytes()
        if hashlib.sha256(data).hexdigest() != manifest["source_hashes"][source_id]:
            raise ValueError(f"fixture hash changed: {source_id}")
        if docling_dir is None:
            pages = {page.locator.page: page.text for page in extract_pdf_isolated(data)}
        else:
            pages = docling_pages(docling_dir / f"{Path(relative_path).stem}.json")
        for page_number, page_text in pages.items():
            page_count += 1
            if chunking.startswith("blocks"):
                if not isinstance(page_text, list):
                    raise ValueError("block strategy requires Docling output")
                excerpts = block_token_windows(
                    page_text, tokenizer, int(chunking.removeprefix("blocks"))
                )
            elif chunking == "fixed120":
                excerpts = chunk_text(
                    " ".join(page_text) if isinstance(page_text, list) else page_text
                )
            else:
                excerpts = sentence_token_windows(
                    " ".join(page_text) if isinstance(page_text, list) else page_text,
                    tokenizer,
                    int(chunking.removeprefix("sentence")),
                )
            rows.extend(
                (f"{source_id}:p{page_number}:c{number}", excerpt)
                for number, excerpt in enumerate(excerpts)
            )
    table = json.loads((ROOT / "ml/evals/synthetic_table.json").read_text(encoding="utf-8"))
    if table.get("synthetic") is not True:
        raise ValueError("table fixture must be synthetic")
    rows.append((table["target_locator"], "Synthetic Mechanics Count Sample A 7"))
    max_input = MODELS[model_name][2]
    truncated = sum(
        token_count(tokenizer, _prefix(model_name, text, query=False)) > max_input
        for _, text in rows
    )
    if truncated:
        raise ValueError(f"{truncated} passages exceed model context")

    collection = f"culture_study_{uuid4().hex}"
    vector_name = "dense"
    dimensions = MODELS[model_name][1]
    id_to_key = {uuid5(NAMESPACE_URL, key): key for key, _ in rows}
    key_to_text = dict(rows)
    index_started = perf_counter()
    timings: list[float] = []
    rankings: dict[str, list[str]] = {}
    score_diagnostics: dict[str, dict[str, float | None]] = {}
    review_rows: list[tuple[str, str, str, str, str, str, int | None, int, float, str]] = []
    async with httpx.AsyncClient(timeout=90) as client:
        response = await client.put(
            f"{vector_url}/collections/{collection}",
            json={"vectors": {vector_name: {"size": dimensions, "distance": "Cosine"}}},
        )
        response.raise_for_status()
        try:
            for start in range(0, len(rows), 16):
                batch = rows[start : start + 16]
                inputs = [_prefix(model_name, text, query=False) for _, text in batch]
                vectors = await asyncio.to_thread(_encode, model, model_name, inputs)
                points = [
                    {"id": str(uuid5(NAMESPACE_URL, key)), "vector": {vector_name: vec.tolist()}}
                    for (key, _), vec in zip(batch, vectors, strict=True)
                ]
                response = await client.put(
                    f"{vector_url}/collections/{collection}/points?wait=true",
                    json={"points": points},
                )
                response.raise_for_status()
            index_seconds = perf_counter() - index_started
            for case in cases:
                started = perf_counter()
                query_input = _prefix(model_name, case.query, query=True)
                vector = (await asyncio.to_thread(_encode, model, model_name, [query_input]))[0]
                response = await client.post(
                    f"{vector_url}/collections/{collection}/points/query",
                    json={"query": vector.tolist(), "using": vector_name, "limit": 100},
                )
                response.raise_for_status()
                timings.append(perf_counter() - started)
                points = response.json()["result"]["points"]
                if review_csv is not None:
                    for rank, point in enumerate(points[:5], 1):
                        key = id_to_key[UUID(point["id"])]
                        source_id = key.split(":p", 1)[0]
                        review_rows.append(
                            (
                                case.query_id,
                                case.query,
                                key,
                                source_id,
                                manifest["source_files"].get(source_id, ""),
                                manifest["source_hashes"].get(source_id, "synthetic"),
                                int(key.split(":p", 1)[1].split(":", 1)[0])
                                if ":p" in key
                                else None,
                                rank,
                                float(point["score"]),
                                key_to_text[key],
                            )
                        )
                best_by_page: dict[str, float] = {}
                for point in points:
                    key = id_to_key[UUID(point["id"])]
                    page_key = key.rsplit(":c", 1)[0] if ":c" in key else key
                    best_by_page[page_key] = max(
                        best_by_page.get(page_key, float("-inf")), float(point["score"])
                    )
                rankings[case.query_id] = [
                    key for key, _ in sorted(best_by_page.items(), key=lambda item: -item[1])[:5]
                ]
                relevant_scores = [
                    best_by_page[key]
                    for key, grade in case.grades.items()
                    if grade > 0 and key in best_by_page
                ]
                score_diagnostics[case.query_id] = {
                    "top_score": max(best_by_page.values()) if best_by_page else None,
                    "best_relevant_score": max(relevant_scores) if relevant_scores else None,
                }
        finally:
            response = await client.delete(f"{vector_url}/collections/{collection}")
            response.raise_for_status()

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        "".join(
            json.dumps({"query_id": key, "candidate_keys": value}) + "\n"
            for key, value in rankings.items()
        ),
        encoding="utf-8",
    )
    gpu_memory = {}
    gpu_snapshot = None
    if gpu_model:
        import torch
        from huggingface_hub import snapshot_download

        gpu_memory = {
            "peak_cuda_allocated_mib": round(torch.cuda.max_memory_allocated() / 2**20, 1),
            "peak_cuda_reserved_mib": round(torch.cuda.max_memory_reserved() / 2**20, 1),
        }
        gpu_snapshot = getattr(model[0].auto_model.config, "_commit_hash", None)
        if not gpu_snapshot:
            gpu_snapshot = Path(
                snapshot_download(MODELS[model_name][0], local_files_only=True)
            ).name
    report = {
        "model": model_name,
        "model_snapshot": (
            gpu_snapshot if gpu_model else Path(model.model._model_dir).name
        ),
        "chunking": chunking,
        "extraction": "docling" if docling_dir else "pypdf",
        "pages": page_count,
        "segments": len(rows),
        "truncated_segments": truncated,
        "load_seconds": load_seconds,
        "index_seconds": index_seconds,
        "mean_query_seconds": mean(timings),
        "max_query_seconds": max(timings),
        "peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        **gpu_memory,
        "metrics": summarize(cases, rankings, 5)["overall"],
        "score_diagnostics": score_diagnostics,
        "label_status": "provisional_agent; same eight cases, no held-out tuning",
    }
    output.with_suffix(".report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    if review_csv is not None:
        review_csv.parent.mkdir(parents=True, exist_ok=True)
        with review_csv.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.writer(stream)
            writer.writerow(
                (
                    "query_id", "query", "candidate_key", "source_id", "source_file",
                    "source_sha256", "physical_page", "rank", "cosine_score", "excerpt",
                    "relevance_grade_0_1_2", "notes",
                )
            )
            writer.writerows((*row, "", "") for row in review_rows)
    print(json.dumps(report, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", choices=MODELS, required=True)
    parser.add_argument(
        "--chunking",
        choices=["fixed120", "sentence256", "sentence384", "blocks256", "blocks384"],
        required=True,
    )
    parser.add_argument("--docling-dir", type=Path)
    parser.add_argument("--review-csv", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    asyncio.run(
        run(
            args.model,
            args.chunking,
            os.environ["CORPUS_TEST_VECTOR_URL"].rstrip("/"),
            args.output,
            args.docling_dir,
            args.review_csv,
        )
    )


if __name__ == "__main__":
    main()
