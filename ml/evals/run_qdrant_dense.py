"""Compare local dense retrieval on the frozen, internal-use provisional fixtures."""

import argparse
import asyncio
import hashlib
import json
import os
from pathlib import Path
from time import perf_counter
from uuid import NAMESPACE_URL, uuid4, uuid5

import httpx
from app.infrastructure.ingestion.chunking import chunk_text
from app.infrastructure.ingestion.isolated_pdf import extract_pdf_isolated
from app.infrastructure.vector.text_vectors import LocalTextEmbedder, QdrantTextIndex
from retrieval_eval import load_cases, summarize

ROOT = Path(__file__).resolve().parents[2]


async def run(output: Path, vector_url: str, min_score: float) -> None:
    manifest = json.loads((ROOT / "ml/evals/manifest.json").read_text(encoding="utf-8"))
    cases = load_cases(ROOT / "ml/evals/qrels.jsonl")
    rows: list[tuple[str, str]] = []
    for source_id, relative_path in manifest["source_files"].items():
        data = (ROOT / relative_path).read_bytes()
        if hashlib.sha256(data).hexdigest() != manifest["source_hashes"][source_id]:
            raise ValueError(f"fixture hash changed: {source_id}")
        for page in extract_pdf_isolated(data):
            rows.extend(
                (f"{source_id}:p{page.locator.page}:c{number}", excerpt)
                for number, excerpt in enumerate(chunk_text(page.text))
            )
    table = json.loads((ROOT / "ml/evals/synthetic_table.json").read_text(encoding="utf-8"))
    if table.get("synthetic") is not True:
        raise ValueError("table mechanics fixture must be marked synthetic")
    rows.append((table["target_locator"], "Synthetic Mechanics Count Sample A 7"))

    collection = f"culture_eval_{uuid4().hex}"
    index = QdrantTextIndex(vector_url, LocalTextEmbedder(), collection)
    id_to_key = {uuid5(NAMESPACE_URL, key): key for key, _ in rows}
    timings: list[float] = []
    top_scores: dict[str, float | None] = {}
    try:
        await index.upsert(
            [(uuid5(NAMESPACE_URL, key), uuid5(NAMESPACE_URL, key.split(":")[0]), text)
             for key, text in rows]
        )
        rankings: dict[str, list[str]] = {}
        for case in cases:
            started = perf_counter()
            ranked = await index.query(case.query, 100)
            timings.append(perf_counter() - started)
            top_scores[case.query_id] = ranked[0][1] if ranked else None
            best_by_page: dict[str, float] = {}
            for segment_id, score in ranked:
                if score < min_score:
                    continue
                key = id_to_key[segment_id]
                page_key = key.rsplit(":c", 1)[0] if ":c" in key else key
                best_by_page[page_key] = max(best_by_page.get(page_key, float("-inf")), score)
            rankings[case.query_id] = [
                key for key, _ in sorted(best_by_page.items(), key=lambda item: -item[1])[:5]
            ]
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            "".join(
                json.dumps({"query_id": query_id, "candidate_keys": keys}, ensure_ascii=False)
                + "\n"
                for query_id, keys in rankings.items()
            ),
            encoding="utf-8",
        )
        report = summarize(cases, rankings, 5)
        print(
            json.dumps(
                {
                    "report": report["overall"],
                    "min_score": min_score,
                    "mean_query_seconds": sum(timings) / len(timings),
                    "top_scores": top_scores,
                },
                indent=2,
            )
        )
    finally:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.delete(f"{vector_url.rstrip('/')}/collections/{collection}")
            response.raise_for_status()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--min-score", type=float, default=0.0)
    args = parser.parse_args()
    asyncio.run(run(args.output, os.environ["CORPUS_TEST_VECTOR_URL"], args.min_score))


if __name__ == "__main__":
    main()
