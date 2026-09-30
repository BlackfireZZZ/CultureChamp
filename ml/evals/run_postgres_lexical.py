"""Run an internal, temporary PostgreSQL retrieval check on held fixtures."""

import argparse
import asyncio
import hashlib
import json
import os
from pathlib import Path

import asyncpg
from app.infrastructure.db.lexical_search import search_terms
from app.infrastructure.ingestion.isolated_pdf import extract_pdf_isolated

ROOT = Path(__file__).resolve().parents[2]


async def run(config: str, output: Path, dsn: str) -> None:
    if config not in {"simple", "russian"}:
        raise ValueError("unsupported text-search configuration")
    manifest = json.loads((ROOT / "ml/evals/manifest.json").read_text(encoding="utf-8"))
    qrels = [
        json.loads(line)
        for line in (ROOT / "ml/evals/qrels.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    rows: list[tuple[str, str]] = []
    for source_id, relative_path in manifest["source_files"].items():
        data = (ROOT / relative_path).read_bytes()
        if hashlib.sha256(data).hexdigest() != manifest["source_hashes"][source_id]:
            raise ValueError(f"fixture hash changed: {source_id}")
        rows.extend(
            (f"{source_id}:p{page.locator.page}", page.text)
            for page in extract_pdf_isolated(data)
        )
    table = json.loads((ROOT / "ml/evals/synthetic_table.json").read_text(encoding="utf-8"))
    if table.get("synthetic") is not True:
        raise ValueError("table mechanics fixture must be marked synthetic")
    rows.append((table["target_locator"], "Synthetic Mechanics Count Sample A 7"))

    connection = await asyncpg.connect(dsn)
    try:
        await connection.execute(
            "CREATE TEMP TABLE eval_pages (candidate_key text PRIMARY KEY, body text NOT NULL)"
        )
        await connection.executemany(
            "INSERT INTO eval_pages (candidate_key, body) VALUES ($1, $2)", rows
        )
        await connection.execute(
            "CREATE INDEX eval_pages_fts ON eval_pages USING GIN "
            f"(to_tsvector('{config}'::regconfig, body))"
        )
        await connection.execute("ANALYZE eval_pages")
        results = []
        for case in qrels:
            terms = search_terms(case["query"])
            if not terms:
                keys: list[str] = []
            else:
                query = " | ".join(terms)
                ranked = await connection.fetch(
                    "SELECT candidate_key FROM eval_pages "
                    f"WHERE to_tsvector('{config}'::regconfig, body) "
                    f"@@ to_tsquery('{config}'::regconfig, $1) "
                    f"ORDER BY ts_rank_cd(to_tsvector('{config}'::regconfig, body), "
                    f"to_tsquery('{config}'::regconfig, $1)) DESC, candidate_key LIMIT 5",
                    query,
                )
                keys = [record["candidate_key"] for record in ranked]
            results.append({"query_id": case["query_id"], "candidate_keys": keys})
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            "".join(json.dumps(result, ensure_ascii=False) + "\n" for result in results),
            encoding="utf-8",
        )
    finally:
        await connection.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", choices=("simple", "russian"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    dsn = os.environ["CORPUS_TEST_DATABASE_URL"].replace(
        "postgresql+asyncpg://", "postgresql://", 1
    )
    asyncio.run(run(args.config, args.output, dsn))


if __name__ == "__main__":
    main()
