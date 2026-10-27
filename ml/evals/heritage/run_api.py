"""Replay frozen retrieval questions over authenticated HTTP and real SQL/Qdrant.

The corpus is seeded from frozen extracted passages, not the upload/extraction API.
Only isolated databases whose names start culturechamp_retrieval_api are accepted.
No chat/generation route is invoked; source excerpts never enter the public report.
"""

import argparse
import asyncio
import hashlib
import json
import os
import secrets
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import urlparse
from uuid import NAMESPACE_URL, uuid5

from .corpus import chunks
from .runner import aggregate, family_aggregate, latency_summary, score_question, validate_questions

ROOT = Path(__file__).resolve().parents[3]


async def run(args: argparse.Namespace) -> None:
    import httpx
    from app.application.access import Role
    from app.infrastructure.db.chat_models import GenerationAttempt
    from app.infrastructure.db.identity_store import SqlIdentityStore
    from app.infrastructure.db.source_models import (
        Source,
        SourceDecision,
        SourceProcessing,
        SourceRevision,
        SourceSegment,
        SourceTag,
    )
    from app.infrastructure.passwords import Argon2PasswordCodec
    from app.infrastructure.vector.indexing import ApprovedTextIndexer
    from app.infrastructure.vector.text_vectors import (
        COLLECTION,
        MODEL_ID,
        LocalTextEmbedder,
        QdrantTextIndex,
    )
    from sqlalchemy import func, select
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    units = json.loads((args.store / "units.json").read_text())
    question_bytes = args.questions.read_bytes()
    manifest = json.loads(args.questions.with_name("manifest.json").read_text())
    assert hashlib.sha256(question_bytes).hexdigest() == manifest["questions_sha256"]
    assert hashlib.sha256((args.store / "units.json").read_bytes()).hexdigest() == (
        manifest["normalized_units_sha256"])
    questions = [json.loads(line) for line in question_bytes.decode().splitlines() if line]
    validate_questions(questions, units)
    passages = chunks(units)
    inventory = json.loads((args.store / "inventory.json").read_text())
    for source in inventory:
        assert hashlib.sha256(Path(source["path"]).read_bytes()).hexdigest() == source["sha256"]
    engine = create_async_engine(args.database_url, pool_pre_ping=True)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    index = QdrantTextIndex(args.vector_url, LocalTextEmbedder())
    ids = {p["key"]: uuid5(NAMESPACE_URL, f"server-heritage:{p['key']}") for p in passages}
    revisions = {s["source_id"]: uuid5(NAMESPACE_URL, f"server-heritage:{s['sha256']}")
                 for s in inventory}
    by_id = {str(ids[p["key"]]): p for p in passages}
    started = time.perf_counter()
    async with factory.begin() as session:
        count = await session.scalar(select(func.count()).select_from(Source))
        if count:
            raise ValueError("Isolated database is not empty; create a fresh replay database")
        for source in inventory:
            sid = source["source_id"]
            source_id = uuid5(NAMESPACE_URL, f"server-heritage-source:{sid}")
            session.add(Source(id=source_id, origin_url=f"private:heritage/{sid}"))
            await session.flush()
            session.add(SourceRevision(
                id=revisions[sid], source_id=source_id, sha256=source["sha256"],
                byte_size=Path(source["path"]).stat().st_size,
                media_type=("application/pdf" if source["format"] == "pdf"
                            else "application/epub+zip"),
                storage_key=f"heritage/{source['sha256']}.{source['format']}",
                title=source["filename"], rights_note="Owner-authorized isolated retrieval fixture",
            ))
            await session.flush()
            session.add(SourceProcessing(revision_id=revisions[sid], state="review_pending"))
            session.add(SourceDecision(
                revision_id=revisions[sid], kind="approve", reviewer_id="isolated-api-replay",
                reason="Internal fixture visibility only; not expert cultural approval",
                evidence_url="private:owner-supplied-retrieval-study", user_text=True,
                original_file=False, provider_transfer=False, sensitivity_cleared=True,
            ))
            session.add(SourceTag(revision_id=revisions[sid], kind="region", value=sid))
            for ordinal, passage in enumerate(p for p in passages if p["source_id"] == sid):
                locator = passage["locator"]
                session.add(SourceSegment(
                    id=ids[passage["key"]], revision_id=revisions[sid], ordinal=ordinal,
                    kind="prose", included=True, text=passage["text"],
                    page=int(locator.rsplit(":", 1)[1]) if source["format"] == "pdf" else None,
                    section=locator if source["format"] == "epub" else None,
                ))
    password = secrets.token_urlsafe(24)
    username = "heritage-api-replay"
    identity = SqlIdentityStore(factory)
    codec = Argon2PasswordCodec()
    await identity.create_account(username, await codec.hash(password), Role.USER)
    indexer = ApprovedTextIndexer(factory, index)
    indexed = 0
    while await indexer.index_one() is not None:
        indexed += 1
    assert indexed == len(inventory)
    index_seconds = time.perf_counter() - started
    # A separate real HTTP process exercises normal application configuration/DI.
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT / "backend")
    log_path = args.store / "server-api.log"
    log_file = log_path.open("w")
    server = subprocess.Popen([
        sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1",
        "--port", str(urlparse(args.base_url).port), "--no-access-log",
    ], cwd=ROOT, env=env, stdout=log_file, stderr=subprocess.STDOUT)
    requests_count = 0
    ranked: dict[str, list[str]] = {}
    measured = []
    diagnostic_results = []
    try:
        async with httpx.AsyncClient(
            base_url=args.base_url, timeout=180, trust_env=False,
        ) as client:
            for _ in range(100):
                if server.poll() is not None:
                    raise RuntimeError("API process exited; inspect private server log")
                try:
                    if (await client.get("/api/v1/health/ready")).status_code == 200:
                        break
                except httpx.ConnectError:
                    pass
                await asyncio.sleep(0.2)
            else:
                raise RuntimeError("API did not become ready")
            anonymous = await client.get("/api/v1/materials/search", params={"q": "fixture"})
            assert anonymous.status_code == 401
            login = await client.post("/api/v1/auth/login", json={"username": username,
                                      "password": password}, headers={"origin": args.base_url})
            login.raise_for_status()
            # Warm on an exposed development query; exclude this from timed parity metrics.
            warm = await client.get("/api/v1/materials/search", params={"q": questions[0]["query"],
                                                                     "limit": 10})
            if warm.status_code != 200:
                raise RuntimeError(f"Search warmup failed HTTP{warm.status_code}; see private log")
            for question in questions:
                started = time.perf_counter()
                response = await client.get("/api/v1/materials/search", params={
                    "q": question["query"], "limit": 10,
                })
                seconds = time.perf_counter() - started
                requests_count += 1
                response.raise_for_status()
                assert response.headers["cache-control"] == "no-store"
                hits = []
                for result in response.json():
                    passage = by_id[result["segment_id"]]
                    assert result["revision_id"] == str(revisions[passage["source_id"]])
                    assert result["text"] == passage["text"]
                    locator = result["locator"]
                    if passage["format"] == "pdf":
                        assert locator["page"] == int(passage["locator"].rsplit(":", 1)[1])
                    else:
                        assert locator["page"] is None and locator["section"] == passage["locator"]
                    hits.append(passage)
                row = score_question(question, hits)
                row = {k: v for k, v in row.items() if not k.endswith("50")}
                row["seconds"] = seconds
                measured.append(row)
                ranked[question["query_id"]] = [p["key"] for p in hits]
            diagnostics = [json.loads(x) for x in args.diagnostics.read_text().splitlines() if x]
            for question in diagnostics:
                response = await client.get("/api/v1/materials/search", params={
                    "q": question["query"], "limit": 10})
                response.raise_for_status()
                diagnostic_results.append({"query_id": question["query_id"],
                                           "returned_neighbors": len(response.json())})
        async with factory() as session:
            generation_attempts = await session.scalar(
                select(func.count()).select_from(GenerationAttempt))
            assert generation_attempts == 0
            # Inspect the actual authorization/join plan on this corpus without exporting texts.
            from app.infrastructure.db.hybrid_search import _scope
            from app.infrastructure.db.source_models import SourceVectorIndex
            from sqlalchemy import text
            statement = _scope(select(SourceRevision), region=None, people=None,
                               for_provider=False).join(SourceVectorIndex).where(
                                   SourceVectorIndex.model_id == MODEL_ID)
            compiled = str(statement.compile(dialect=engine.dialect,
                                              compile_kwargs={"literal_binds": True}))
            plan = await session.scalar(text("EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) " + compiled))
        split_results = {}
        for split in ("dev", "test"):
            pairs = [(q, row) for q, row in zip(questions, measured, strict=True)
                     if q["split"] == split]
            qs, rows = [q for q, _ in pairs], [row for _, row in pairs]
            metrics = aggregate([{k: v for k, v in r.items() if k != "seconds"} for r in rows])
            split_results[split] = {"metrics": metrics,
                "family_metrics": family_aggregate(qs, [{k: v for k, v in r.items()
                                                         if k != "seconds"} for r in rows]),
                "http_latency": latency_summary([r["seconds"] for r in rows]),
                "format_slices": {fmt: aggregate([{k: v for k, v in r.items() if k != "seconds"}
                                                  for q, r in pairs if q["format"] == fmt])
                                  for fmt in ("pdf", "epub")}}
        final = split_results["test"]["metrics"]
        passed = (final["hit5"] >= .94 and final["hit10"] >= .96
                  and final["reciprocal_rank10"] >= .80
                  and all(s["hit5"] >= .80
                          for s in split_results["test"]["format_slices"].values()))
        result = {"kind": "HTTP API parity replay; not an independent new test",
                  "endpoint": "/api/v1/materials/search", "retrieval_depth": 10,
                  "questions_sha256": manifest["questions_sha256"], "model_id": MODEL_ID,
                  "collection": COLLECTION, "device": args.device,
                  "sources": len(inventory), "segments": len(passages),
                  "indexing_seconds": index_seconds, "timed_search_requests": requests_count,
                  "locator_checks_passed": True, "generation_attempts": generation_attempts,
                  "split_results": split_results, "api_parity_pass": passed,
                  "diagnostic_probes": diagnostic_results, "queries": measured,
                  "ranked_keys": ranked,
                  "authorization_query_plan": {"planning_ms": plan[0]["Planning Time"],
                                                "execution_ms": plan[0]["Execution Time"]}}
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
        print(json.dumps({"api_parity_pass": passed, "splits": split_results}, indent=2))
        if not passed:
            raise RuntimeError("Frozen API parity acceptance failed; report retained")
    finally:
        server.terminate()
        await asyncio.to_thread(server.wait, 30)
        log_file.close()
        await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-url", required=True)
    parser.add_argument("--vector-url", required=True)
    parser.add_argument("--base-url", default="http://127.0.0.1:18038")
    parser.add_argument("--store", type=Path, required=True)
    parser.add_argument("--model-cache-dir", type=Path, required=True)
    parser.add_argument("--device", choices=["cpu", "cuda"], default="cuda")
    parser.add_argument("--questions", type=Path,
                        default=Path(__file__).parent/"round2/questions.jsonl")
    parser.add_argument("--diagnostics", type=Path,
                        default=Path(__file__).parent/"diagnostics.jsonl")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    db = urlparse(args.database_url)
    if db.hostname != "127.0.0.1" or not db.path.startswith("/culturechamp_retrieval_api"):
        parser.error("Only isolated loopback culturechamp_retrieval_api databases may be seeded")
    if any(urlparse(url).hostname != "127.0.0.1" for url in (args.vector_url, args.base_url)):
        parser.error("API/vector replay endpoints must be loopback")
    if urlparse(args.vector_url).port == 6333 or urlparse(args.base_url).port == 8000:
        parser.error("Do not reuse the owner's running application ports")
    os.environ.update(DATABASE_URL=args.database_url, VECTOR_URL=args.vector_url,
                      RETRIEVAL_MODEL_CACHE=str(args.model_cache_dir.resolve()),
                      RETRIEVAL_DEVICE=args.device, MODEL_PROVIDER="fake",
                      MODEL_API_ENDPOINT="", MODEL_API_KEY="", MODEL_POLICY_APPROVED="false",
                      APP_ENV="development", HF_HUB_OFFLINE="1", HF_HUB_DISABLE_TELEMETRY="1")
    sys.path.insert(0, str(ROOT / "backend"))
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
