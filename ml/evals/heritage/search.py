"""Search the private corpus locally with the frozen retrieval configuration.

Excerpts are printed only to stdout. Redirect stdout only into private storage.
"""

from __future__ import annotations

import argparse
import gc
import json
import os
import sys
import time
from pathlib import Path

if __package__:
    from .corpus import chunks
    from .runner import candidate_union, digest, resolve_snapshot, validate_inventory
else:
    from corpus import chunks
    from runner import candidate_union, digest, resolve_snapshot, validate_inventory


def pinned_snapshot(repo: str, revision: str, cache_dir: Path) -> str:
    """Use the selected immutable revision even if the local main ref has moved."""
    if len(revision) != 40 or any(c not in "0123456789abcdef" for c in revision):
        raise ValueError("Selection must contain immutable model revisions")
    try:
        current, current_revision = resolve_snapshot(repo, cache_dir)
    except (FileNotFoundError, OSError):
        current, current_revision = "", ""
    if current_revision == revision:
        return current
    from huggingface_hub import snapshot_download
    path = Path(snapshot_download(repo, revision=revision, cache_dir=str(cache_dir),
                                  local_files_only=True, allow_patterns=["config.json"]))
    if path.name != revision:
        raise ValueError("Resolved model snapshot differs from frozen selection")
    return str(path)


def main() -> None:
    total_started = time.perf_counter()
    timings = {}
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--store", type=Path, required=True)
    parser.add_argument("--model-cache-dir", type=Path, default=Path(".private/models"))
    parser.add_argument("--selection", type=Path,
                        default=Path(__file__).parent / "round2" / "selection.json")
    parser.add_argument("--query", required=True)
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--device", default="cuda")
    args = parser.parse_args()
    if not args.query.strip():
        parser.error("Query must not be blank")
    selection = json.loads(args.selection.read_text())
    encoder_spec, reranker_spec = selection["encoder"], selection["reranker"]
    depth = reranker_spec["candidate_depth"]
    union_spec = selection.get("fusion")
    if union_spec and union_spec["method"] != "deduplicated_union":
        parser.error("Unsupported selection fusion method")
    if not 1 <= args.limit <= depth:
        parser.error("Limit must be between 1 and selected reranker candidate depth")
    if not encoder_spec["normalized"]:
        parser.error("This CLI requires the selected normalized dense encoder")
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
    os.environ["DO_NOT_TRACK"] = "1"
    import numpy as np
    import torch
    from sentence_transformers import CrossEncoder, SentenceTransformer

    started = time.perf_counter()
    units = json.loads((args.store / "units.json").read_text())
    validate_inventory(args.store, units)
    passages = chunks(units, selection["chunking"]["words"],
                      selection["chunking"]["overlap"])
    if not passages:
        parser.error("Private corpus has no passages")
    inventory = {row["source_id"]: row for row in
                 json.loads((args.store / "inventory.json").read_text())}
    corpus_hash = digest(passages)
    timings["corpus_load_and_validation_seconds"] = time.perf_counter() - started
    started = time.perf_counter()
    dtype = torch.float16 if args.device.startswith("cuda") else torch.float32
    encoder_path = pinned_snapshot(encoder_spec["repo"], encoder_spec["revision"],
                                   args.model_cache_dir)
    encoder = SentenceTransformer(encoder_path, device=args.device, local_files_only=True,
                                  model_kwargs={"dtype": dtype})
    timings["encoder_load_seconds"] = time.perf_counter() - started
    encoder.max_seq_length = encoder_spec["max_tokens"]
    prefix = encoder_spec["passage_prefix"]
    query = encoder_spec["query_prefix"] + args.query
    key = digest({"corpus": corpus_hash, "model": encoder_spec["repo"],
                  "revision": encoder_spec["revision"], "dtype": str(dtype),
                  "vector_dtype": "float32", "prefix": prefix,
                  "max_seq_length": encoder_spec["max_tokens"]})
    cache = args.store / "retrieval-cache"
    cache.mkdir(exist_ok=True)
    embedding_file = cache / f"embeddings-{key}.npy"
    started = time.perf_counter()
    cache_hit = embedding_file.exists()
    if cache_hit:
        vectors = np.load(embedding_file)
    else:
        print("Building private embedding cache", file=sys.stderr)
        vectors = np.asarray(encoder.encode([prefix + p["text"] for p in passages],
                             batch_size=16, normalize_embeddings=True, convert_to_numpy=True,
                             show_progress_bar=False), dtype=np.float32)
        np.save(embedding_file, vectors)
    timings["embedding_cache_load_or_build_seconds"] = time.perf_counter() - started
    started = time.perf_counter()
    vector = np.asarray(encoder.encode(query, normalize_embeddings=True, convert_to_numpy=True),
                        dtype=np.float32)
    if vectors.shape != (len(passages), len(vector)) or not np.isfinite(vectors).all():
        raise ValueError("Private embedding cache shape or values are invalid")
    dense_scores = vectors @ vector
    dense_depth = union_spec["dense_depth"] if union_spec else depth
    dense_candidates = np.argsort(-dense_scores, kind="stable")[:dense_depth].tolist()
    timings["dense_query_seconds"] = time.perf_counter() - started
    lexical_candidates = []
    if union_spec:
        import bm25s
        import Stemmer
        lexical_spec = selection["lexical"]
        if lexical_spec["implementation"] != "bm25s":
            parser.error("Unsupported selected lexical implementation")
        stemmer = Stemmer.Stemmer("russian")
        index_path = cache / f"bm25-russian-{corpus_hash}"
        started = time.perf_counter()
        if index_path.exists():
            lexical = bm25s.BM25.load(str(index_path), load_corpus=False)
        else:
            lexical = bm25s.BM25()
            tokens = bm25s.tokenize([p["text"] for p in passages], stemmer=stemmer,
                                    stopwords=lexical_spec["stopwords"], show_progress=False)
            lexical.index(tokens, show_progress=False)
            lexical.save(str(index_path))
        timings["lexical_index_load_or_build_seconds"] = time.perf_counter() - started
        started = time.perf_counter()
        tokens = bm25s.tokenize([args.query], stemmer=stemmer,
                                stopwords=lexical_spec["stopwords"], show_progress=False)
        indices, _ = lexical.retrieve(tokens, k=min(union_spec["lexical_depth"], len(passages)),
                                      show_progress=False)
        lexical_candidates = indices[0].tolist()
        candidates = candidate_union([dense_candidates, lexical_candidates],
                                      max(dense_depth, union_spec["lexical_depth"]))[:depth]
        timings["lexical_query_and_union_seconds"] = time.perf_counter() - started
    else:
        candidates = dense_candidates
    query_tokens = len(encoder.tokenizer(query, truncation=False)["input_ids"])
    del encoder
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    started = time.perf_counter()
    reranker_path = pinned_snapshot(reranker_spec["repo"], reranker_spec["revision"],
                                    args.model_cache_dir)
    reranker = CrossEncoder(reranker_path, device=args.device, local_files_only=True,
                           max_length=reranker_spec["max_tokens"], model_kwargs={"dtype": dtype})
    timings["reranker_load_seconds"] = time.perf_counter() - started
    started = time.perf_counter()
    pairs = [(args.query, passages[i]["text"]) for i in candidates]
    pair_tokens = reranker.tokenizer([a for a, _ in pairs], [b for _, b in pairs],
                                    truncation=False, padding=False, return_length=True)["length"]
    scores = np.asarray(reranker.predict(pairs, batch_size=16,
                                        show_progress_bar=False)).reshape(-1)
    order = np.argsort(-scores, kind="stable").tolist()
    timings["reranking_seconds"] = time.perf_counter() - started
    hits = []
    for rank, index in enumerate(order[:args.limit], 1):
        passage = passages[candidates[index]]
        locator = passage["locator"]
        hit = {"rank": rank, "source_id": passage["source_id"],
               "filename": inventory[passage["source_id"]]["filename"],
               "source_hash": passage["source_hash"], "key": passage["key"],
               "locator": locator, "start": passage["start"], "end": passage["end"],
               "snippet": passage["text"], "reranker_score": float(scores[index]),
               "dense_score": float(dense_scores[candidates[index]]),
               "reranker_input_truncated": pair_tokens[index] > reranker_spec["max_tokens"]}
        if locator.startswith("pdf:page:"):
            hit["physical_page"] = int(locator.split(":", 2)[2])
        elif locator.startswith("epub:spine:"):
            _, _, spine, member = locator.split(":", 3)
            hit["epub_spine"] = int(spine)
            hit["epub_member"] = member
        hits.append(hit)
    timings["total_seconds"] = time.perf_counter() - total_started
    output = {"query": args.query, "configuration": selection["selected_configuration"],
              "mode": ("Local dense50 and Russian BM25 lexical50 deduplicated union, "
                       "then cross-encoder reranking" if union_spec else
                       "Local exact dense candidates then cross-encoder reranking"),
              "candidate_counts": {"dense": len(dense_candidates),
                                   "lexical": len(lexical_candidates), "reranked": len(candidates)},
              "timings": timings,
              "score_interpretation": "Ranking scores; no evidence-confidence assertion",
              "corpus_sha256": corpus_hash, "embedding_cache_hit": cache_hit,
              "encoder_revision": encoder_spec["revision"],
              "reranker_revision": reranker_spec["revision"], "model_dtype": str(dtype),
              "query_truncated": query_tokens > encoder_spec["max_tokens"], "hits": hits,
              "ranked_candidates": [{"key": passages[candidates[i]]["key"],
                                      "reranker_score": float(scores[i]),
                                      "dense_score": float(dense_scores[candidates[i]])}
                                     for i in order]}
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
