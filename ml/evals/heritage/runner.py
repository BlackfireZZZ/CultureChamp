"""Reproducible local retrieval experiments with exact evidence-span scoring."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import resource
import time
from pathlib import Path
from typing import Any

if __package__:
    from .corpus import chunks
else:
    from corpus import chunks

MODELS = {
    "e5-small": "intfloat/multilingual-e5-small",
    "e5-large": "intfloat/multilingual-e5-large",
    "bge-m3": "BAAI/bge-m3",
}

MODEL_REVISIONS = {
    "intfloat/multilingual-e5-small": "614241f622f53c4eeff9890bdc4f31cfecc418b3",
    "intfloat/multilingual-e5-large": "3d7cfbdacd47fdda877c5cd8a79fbcc4f2a574f3",
    "BAAI/bge-m3": "5617a9f61b028005a4858fdac845db406aefb181",
    "BAAI/bge-reranker-v2-m3": "953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e",
}


def digest(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, ensure_ascii=False).encode()
    return hashlib.sha256(encoded).hexdigest()


def validate_questions(questions: list[dict], units: list[dict]) -> None:
    """Reject stale hashes, offsets and quotes before any experiment is scored."""
    lookup = {(u["source_id"], u["locator"]): u for u in units}
    ids: set[str] = set()
    family_splits: dict[str, str] = {}
    for question in questions:
        if question["query_id"] in ids:
            raise ValueError("Duplicate query_id")
        ids.add(question["query_id"])
        family = question["family"]
        if family_splits.setdefault(family, question["split"]) != question["split"]:
            raise ValueError("Question family crosses splits")
        for evidence in question["evidence"]:
            unit = lookup[(evidence["source_id"], evidence["locator"])]
            start, end = evidence["start"], evidence["end"]
            if not 0 <= start < end <= len(unit["text"]):
                raise ValueError("Invalid evidence offsets")
            if evidence["source_hash"] != unit["source_hash"]:
                raise ValueError("Stale evidence source hash")
            if unit["text"][start:end] != evidence["quote"]:
                raise ValueError("Evidence quote does not match offsets")


def coverage(evidence: dict, hits: list[dict]) -> float:
    """Character union coverage; overlapping chunks cannot count characters twice."""
    intervals = []
    for hit in hits:
        if any(hit[k] != evidence[k] for k in ("source_id", "source_hash", "locator")):
            continue
        start = max(hit["start"], evidence["start"])
        end = min(hit["end"], evidence["end"])
        if end > start:
            intervals.append((start, end))
    total, previous_end = 0, evidence["start"]
    for start, end in sorted(intervals):
        total += max(0, end - max(start, previous_end))
        previous_end = max(previous_end, end)
    return total / (evidence["end"] - evidence["start"])


def score_question(question: dict, hits: list[dict]) -> dict:
    evidence = question["evidence"]
    if not evidence:
        return {"query_id": question["query_id"], "diagnostic": True}
    unique = list({h["key"]: h for h in hits}.values())
    first = next((rank for rank, hit in enumerate(unique[:10], 1)
                  if any(coverage(e, [hit]) >= 0.8 for e in evidence)), None)
    result: dict[str, Any] = {"query_id": question["query_id"], "diagnostic": False,
                              "reciprocal_rank10": 1 / first if first else 0.0}
    for k in (5, 10, 50):
        selected = unique[:k]
        values = [coverage(e, selected) for e in evidence]
        result[f"hit{k}"] = float(any(coverage(e, [h]) >= 0.8
                                      for h in selected for e in evidence))
        result[f"union_any{k}"] = float(any(v >= 0.8 for v in values))
        result[f"all_evidence{k}"] = float(all(v >= 0.8 for v in values))
        result[f"evidence_coverage{k}"] = sum(values) / len(values)
    return result


def aggregate(rows: list[dict]) -> dict:
    scored = [r for r in rows if not r["diagnostic"]]
    result: dict[str, Any] = {"questions": len(scored),
                              "diagnostics": len(rows) - len(scored)}
    if not scored:
        return result
    for metric in scored[0]:
        if metric not in {"query_id", "diagnostic"}:
            result[metric] = sum(r[metric] for r in scored) / len(scored)
    for k in (5, 10):
        successes = int(sum(r[f"hit{k}"] for r in scored))
        n, z = len(scored), 1.96
        p = successes / n
        midpoint = (p + z*z / (2*n)) / (1 + z*z/n)
        radius = z * (p*(1-p)/n + z*z/(4*n*n))**0.5 / (1 + z*z/n)
        result[f"hit{k}_successes"] = successes
        result[f"hit{k}_wilson95"] = [midpoint - radius, midpoint + radius]
    return result


def fusion(rankings: list[list[int]], limit: int = 50) -> list[int]:
    scores: dict[int, float] = {}
    for ranking in rankings:
        for rank, index in enumerate(dict.fromkeys(ranking), 1):
            scores[index] = scores.get(index, 0.0) + 1 / (60 + rank)
    return sorted(scores, key=lambda i: (-scores[i], i))[:limit]


def candidate_union(rankings: list[list[int]], per_retriever: int = 50) -> list[int]:
    """Preserve each retriever's top candidates without rank-fusion truncation."""
    return list(dict.fromkeys(index for ranking in rankings for index in ranking[:per_retriever]))


def candidate_coverage(questions: list[dict], candidates: list[list[int]],
                       passages: list[dict]) -> dict:
    rows = []
    for question, indices in zip(questions, candidates, strict=True):
        if not question["evidence"]:
            continue
        hits = [passages[i] for i in dict.fromkeys(indices)]
        spans = question["evidence"]
        rows.append({"query_id": question["query_id"], "candidates": len(hits),
                     "candidate_any_hit": float(any(coverage(e, [h]) >= 0.8
                                                    for e in spans for h in hits)),
                     "candidate_all_evidence": float(all(coverage(e, hits) >= 0.8
                                                         for e in spans))})
    return {"questions": len(rows), "queries": rows,
            "candidate_any_hit": (sum(r["candidate_any_hit"] for r in rows) / len(rows)
                                  if rows else None),
            "candidate_all_evidence": (sum(r["candidate_all_evidence"] for r in rows) / len(rows)
                                       if rows else None),
            "minimum_candidates": min((r["candidates"] for r in rows), default=0),
            "maximum_candidates": max((r["candidates"] for r in rows), default=0)}


def latency_summary(seconds: list[float]) -> dict:
    ordered = sorted(seconds)
    return {"p50_ms": ordered[int((len(ordered)-1)*0.5)]*1000,
            "p95_ms": ordered[int((len(ordered)-1)*0.95)]*1000}


def resolve_snapshot(repo: str, cache_dir: Path | None = None) -> tuple[str, str]:
    """Resolve cached immutable weights without a network request."""
    from huggingface_hub import snapshot_download
    kwargs: dict[str, Any] = {"cache_dir": str(cache_dir) if cache_dir else None,
                              "local_files_only": True, "allow_patterns": ["config.json"]}
    if repo in MODEL_REVISIONS:
        kwargs["revision"] = MODEL_REVISIONS[repo]
    path = Path(snapshot_download(repo, **kwargs))
    revision = path.name
    if len(revision) != 40 or any(c not in "0123456789abcdef" for c in revision):
        raise ValueError("Model snapshot does not have an immutable commit identifier")
    if repo in MODEL_REVISIONS and revision != MODEL_REVISIONS[repo]:
        raise ValueError("Resolved model snapshot differs from the pinned revision")
    return str(path), revision


def validate_inventory(store: Path, units: list[dict]) -> None:
    inventory = json.loads((store / "inventory.json").read_text())
    hashes = {}
    for source in inventory:
        path = Path(source["path"])
        with path.open("rb") as handle:
            actual = hashlib.file_digest(handle, "sha256").hexdigest()
        if actual != source["sha256"]:
            raise ValueError("Original source hash changed")
        hashes[source["source_id"]] = actual
    if {u["source_id"] for u in units} != set(hashes):
        raise ValueError("Extracted corpus does not represent the inventory")
    locators = set()
    for unit in units:
        if unit["source_hash"] != hashes[unit["source_id"]]:
            raise ValueError("Normalized corpus source hash mismatch")
        key = (unit["source_id"], unit["locator"])
        if key in locators:
            raise ValueError("Duplicate normalized source locator")
        locators.add(key)


def family_aggregate(questions: list[dict], rows: list[dict]) -> dict:
    grouped: dict[str, list[dict]] = {}
    for question, row in zip(questions, rows, strict=True):
        if not row["diagnostic"]:
            grouped.setdefault(question["family"], []).append(row)
    family_rows = []
    for family, members in grouped.items():
        values = {key: min(member[key] for member in members)
                  for key in members[0] if key not in {"query_id", "diagnostic"}}
        family_rows.append({"query_id": family, "diagnostic": False, **values})
    result = aggregate(family_rows)
    result["families"] = result.pop("questions")
    result["definition"] = "Minimum across styles; a family hit requires all its queries to hit"
    result["interval_assumption"] = "Families treated as independent sampling units"
    return result


def token_lengths(tokenizer: Any, texts: list[str], max_length: int) -> dict:
    lengths = []
    for offset in range(0, len(texts), 128):
        batch = tokenizer(texts[offset:offset+128], truncation=False, padding=False,
                          return_length=True)
        lengths.extend(batch["length"])
    return {"inputs": len(lengths), "over_limit": sum(n > max_length for n in lengths),
            "maximum_tokens": max(lengths, default=0), "max_length": max_length,
            "truncation_policy": "Tokenizer truncates over-limit inputs; counted explicitly"}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--store", type=Path, required=True)
    parser.add_argument("--questions", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--split", choices=["dev", "test"], default="dev")
    parser.add_argument("--models", nargs="*", choices=MODELS, default=[])
    parser.add_argument("--stemmer", choices=["raw", "russian", "both"], default="both")
    parser.add_argument("--words", type=int, default=120)
    parser.add_argument("--overlap", type=int, default=30)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--model-cache-dir", type=Path)
    parser.add_argument("--diagnostics", type=Path)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--rrf", action="store_true")
    parser.add_argument("--union", action="store_true")
    parser.add_argument("--rerank", action="store_true")
    parser.add_argument("--rerank-top", type=int, choices=[30, 50, 100], default=30)
    parser.add_argument("--selected-config", help="Required exact frozen config name for test")
    parser.add_argument("--reference-config", nargs="*", default=[],
                        help="Frozen reference baselines scored alongside the selected test config")
    parser.add_argument("--expected-questions-hash",
                        help="Required SHA256 of frozen qrels for test")
    args = parser.parse_args()
    if args.union and args.stemmer == "raw":
        parser.error("--union requires Russian BM25 (--stemmer russian or both)")
    question_hash = hashlib.sha256(args.questions.read_bytes()).hexdigest()
    if args.expected_questions_hash and question_hash != args.expected_questions_hash:
        parser.error("Frozen questions hash mismatch")
    if args.split == "test" and not (args.selected_config and args.expected_questions_hash):
        parser.error("Test requires --selected-config and --expected-questions-hash")
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
    os.environ["DO_NOT_TRACK"] = "1"
    import numpy as np

    units = json.loads((args.store / "units.json").read_text())
    validate_inventory(args.store, units)
    manifest_path = args.questions.with_name("manifest.json")
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())
        if manifest["questions_sha256"] != question_hash:
            parser.error("Questions no longer match the frozen manifest")
        unit_hash = hashlib.sha256((args.store / "units.json").read_bytes()).hexdigest()
        if manifest["normalized_units_sha256"] != unit_hash:
            parser.error("Normalized extraction no longer matches the frozen manifest")
    questions = [json.loads(line) for line in args.questions.read_text().splitlines() if line]
    validate_questions(questions, units)
    questions = [q for q in questions if q["split"] == args.split]
    diagnostic_hash = None
    if args.diagnostics:
        diagnostic_hash = hashlib.sha256(args.diagnostics.read_bytes()).hexdigest()
        diagnostics = [json.loads(line) for line in args.diagnostics.read_text().splitlines()
                       if line]
        if any(q["evidence"] for q in diagnostics):
            parser.error("Diagnostic file must contain only unsupported-query probes")
        questions.extend(q for q in diagnostics if q.get("split", args.split) == args.split)
    if not questions:
        parser.error("No questions in requested split")
    passages = chunks(units, args.words, args.overlap)
    corpus_hash = digest(passages)
    cache = args.store / "retrieval-cache"
    cache.mkdir(exist_ok=True)
    texts = [p["text"] for p in passages]
    queries = [q["query"] for q in questions]
    config_results: dict[str, dict] = {}
    timings: dict[str, list[float]] = {}
    rankings: dict[str, list[list[int]]] = {}
    candidate_info: dict[str, dict] = {}
    index_info: dict[str, dict] = {}
    model_info: dict[str, dict] = {}

    def register(name: str, ranked: list[list[int]], elapsed: list[float]) -> None:
        rankings[name] = ranked
        timings[name] = elapsed
        candidate_info[name] = candidate_coverage(questions, ranked, passages)

    import bm25s
    modes = ["raw", "russian"] if args.stemmer == "both" else [args.stemmer]
    for mode in modes:
        started = time.perf_counter()
        stemmer = None
        if mode == "russian":
            import Stemmer
            stemmer = Stemmer.Stemmer("russian")
        tokens = bm25s.tokenize(texts, stopwords=[], stemmer=stemmer, show_progress=False)
        retriever = bm25s.BM25()
        retriever.index(tokens, show_progress=False)
        index_dir = cache / f"bm25-{mode}-{corpus_hash}"
        retriever.save(str(index_dir))
        index_info[f"bm25-{mode}"] = {
            "index_seconds": time.perf_counter() - started,
            "index_bytes": sum(p.stat().st_size for p in index_dir.rglob("*") if p.is_file())}
        qt = bm25s.tokenize(queries, stopwords=[], stemmer=stemmer, show_progress=False)
        retriever.retrieve(qt, k=min(50, len(passages)), show_progress=False)
        ranked, elapsed = [], []
        for i in range(len(queries)):
            started = time.perf_counter()
            one = bm25s.tokenize([queries[i]], stopwords=[], stemmer=stemmer,
                                show_progress=False)
            indices, _ = retriever.retrieve(one, k=min(50, len(passages)), show_progress=False)
            elapsed.append(time.perf_counter() - started)
            ranked.append(indices[0].tolist())
        register(f"bm25-{mode}", ranked, elapsed)

    for alias in args.models:
        import torch
        from sentence_transformers import SentenceTransformer
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        started = time.perf_counter()
        model_path, revision = resolve_snapshot(MODELS[alias], args.model_cache_dir)
        dtype = torch.float16 if args.device.startswith("cuda") else torch.float32
        model = SentenceTransformer(model_path, device=args.device, local_files_only=True,
                                    model_kwargs={"dtype": dtype})
        model_info[alias] = {"model": MODELS[alias], "snapshot": revision,
                             "dtype": str(dtype),
                             "model_load_seconds": time.perf_counter() - started}
        model.max_seq_length = 512
        prefix = "passage: " if alias.startswith("e5-") else ""
        query_prefix = "query: " if alias.startswith("e5-") else ""
        model_info[alias]["tokenization"] = token_lengths(
            model.tokenizer, [prefix + text for text in texts], 512)
        model_info[alias]["query_tokenization"] = token_lengths(
            model.tokenizer, [query_prefix + query for query in queries], 512)
        key = digest({"corpus": corpus_hash, "model": MODELS[alias], "revision": revision,
                      "dtype": str(dtype), "vector_dtype": "float32",
                      "prefix": prefix, "max_seq_length": 512})
        embedding_file = cache / f"embeddings-{key}.npy"
        started = time.perf_counter()
        cached = embedding_file.exists()
        if cached:
            vectors = np.load(embedding_file)
        else:
            vectors = model.encode([prefix + text for text in texts],
                                   batch_size=args.batch_size, normalize_embeddings=True,
                                   convert_to_numpy=True, show_progress_bar=True)
            vectors = np.asarray(vectors, dtype=np.float32)
            np.save(embedding_file, vectors)
        index_info[alias] = {"index_seconds": time.perf_counter() - started,
                             "cache_hit": cached, "vector_dtype": str(vectors.dtype),
                             "index_bytes": embedding_file.stat().st_size}
        model.encode([query_prefix + queries[0]], normalize_embeddings=True)
        ranked, elapsed = [], []
        for query in queries:
            started = time.perf_counter()
            vector = model.encode(query_prefix + query, normalize_embeddings=True,
                                  convert_to_numpy=True)
            scores = vectors @ np.asarray(vector, dtype=np.float32)
            ranked.append(np.argsort(-scores, kind="stable")[:50].tolist())
            elapsed.append(time.perf_counter() - started)
        register(alias, ranked, elapsed)
        del model
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        if args.rrf:
            lexical = "bm25-russian" if "russian" in modes else "bm25-raw"
            name = f"rrf-{alias}-{lexical}"
            fused, elapsed = [], []
            for i in range(len(queries)):
                started = time.perf_counter()
                fused.append(fusion([ranked[i], rankings[lexical][i]]))
                elapsed.append(timings[alias][i] + timings[lexical][i]
                               + time.perf_counter() - started)
            register(name, fused, elapsed)
        if args.union:
            name = f"union-{alias}-bm25-russian"
            combined, elapsed = [], []
            for i in range(len(queries)):
                started = time.perf_counter()
                combined.append(candidate_union([ranked[i], rankings["bm25-russian"][i]]))
                elapsed.append(timings[alias][i] + timings["bm25-russian"][i]
                               + time.perf_counter() - started)
            register(name, combined, elapsed)
    if args.rerank:
        import torch
        from sentence_transformers import CrossEncoder
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        started = time.perf_counter()
        model_path, revision = resolve_snapshot("BAAI/bge-reranker-v2-m3", args.model_cache_dir)
        dtype = torch.float16 if args.device.startswith("cuda") else torch.float32
        model = CrossEncoder(model_path, device=args.device, local_files_only=True,
                             max_length=512, model_kwargs={"dtype": dtype})
        model_info["reranker"] = {"model": "BAAI/bge-reranker-v2-m3",
                                  "snapshot": revision, "dtype": str(dtype),
                                  "model_load_seconds": time.perf_counter() - started,
                                  "max_length": 512, "pair_inputs": 0, "over_limit_pairs": 0}
        rerank_tokens = model_info["reranker"]
        model.predict([(queries[0], texts[0])])
        for name, candidate_rows in list(rankings.items()):
            rerank_name = f"{name}-rerank{args.rerank_top}"
            if args.selected_config and args.selected_config != rerank_name:
                continue
            ranked, elapsed = [], []
            for i, candidates in enumerate(candidate_rows):
                selected = candidates[:args.rerank_top]
                encoded = model.tokenizer([queries[i]] * len(selected),
                                          [texts[j] for j in selected], truncation=False,
                                          padding=False, return_length=True)
                rerank_tokens["pair_inputs"] += len(selected)
                rerank_tokens["over_limit_pairs"] += sum(n > 512 for n in encoded["length"])
                started = time.perf_counter()
                scores = model.predict([(queries[i], texts[j]) for j in selected],
                                       batch_size=args.batch_size, show_progress_bar=False)
                order = np.argsort(-np.asarray(scores).reshape(-1), kind="stable")
                ranked.append([selected[j] for j in order] + candidates[args.rerank_top:])
                elapsed.append(timings[name][i] + time.perf_counter() - started)
            register(rerank_name, ranked, elapsed)
            candidate_info[rerank_name] = candidate_coverage(
                questions, [row[:args.rerank_top] for row in candidate_rows], passages)
    for name, ranked in rankings.items():
        if (args.selected_config and name != args.selected_config
                and name not in args.reference_config):
            continue
        rows = [score_question(q, [passages[j] for j in indices])
                for q, indices in zip(questions, ranked, strict=True)]
        slices = {}
        for field in ("format", "style"):
            for value in sorted({q[field] for q in questions if field in q}):
                slices[f"{field}:{value}"] = aggregate(
                    [r for q, r in zip(questions, rows, strict=True) if q.get(field) == value])
        summary = aggregate(rows)
        summary["thresholds_pass"] = (
            summary.get("hit5", 0) >= 0.90 and summary.get("hit10", 0) >= 0.95
            and summary.get("reciprocal_rank10", 0) >= 0.75
            and all(s.get("hit5", 0) >= 0.80 for k, s in slices.items()
                    if k.startswith("format:") and s["questions"]))
        diagnostic_rows = [indices for q, indices in zip(questions, ranked, strict=True)
                           if not q["evidence"]]
        config_results[name] = {"metrics": summary, "slices": slices,
                                "family_metrics": family_aggregate(questions, rows),
                                "candidate_coverage": candidate_info[name],
                                "diagnostic_probes": {
                                    "questions": len(diagnostic_rows),
                                    "raw_hit_rate": (sum(bool(r) for r in diagnostic_rows)
                                                     / len(diagnostic_rows)
                                                     if diagnostic_rows else None),
                                    "interpretation": "Unfiltered ranking returns neighbors; "
                                    "this does not establish support, absence or abstention"},
                                "warm_query": latency_summary(timings[name]), "queries": rows,
                                "ranked_keys": {q["query_id"]: [passages[j]["key"] for j in ids]
                                                for q, ids in zip(questions, ranked, strict=True)}}
    if not config_results:
        parser.error("Selected config was not generated by requested CLI options")
    packages = {}
    for package in ("bm25s", "PyStemmer", "sentence-transformers", "torch", "numpy"):
        try:
            packages[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            packages[package] = None
    gpu = {}
    try:
        import torch
        if torch.cuda.is_available():
            gpu = {"device": torch.cuda.get_device_name(),
                   "peak_allocated_bytes": torch.cuda.max_memory_allocated(),
                   "peak_reserved_bytes": torch.cuda.max_memory_reserved()}
    except ImportError:
        pass
    result = {"schema_version": 1, "split": args.split, "questions_sha256": question_hash,
              "corpus_sha256": corpus_hash, "diagnostics_sha256": diagnostic_hash,
              "query_interval_assumption": "Descriptive; paired query styles are correlated",
              "chunk_words": args.words,
              "chunk_overlap": args.overlap, "passages": len(passages),
              "models": model_info, "packages": packages, "indexes": index_info,
              "peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
              "gpu": gpu, "configurations": config_results}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({name: item["metrics"] for name, item in config_results.items()},
                     indent=2))


if __name__ == "__main__":
    main()
