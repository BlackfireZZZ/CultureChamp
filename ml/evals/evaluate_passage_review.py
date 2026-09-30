"""Validate private passage judgments and report pooled, in-sample diagnostics."""

import argparse
import csv
import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path
from statistics import mean
from typing import Any

from retrieval_eval import Case, EvaluationFailure, load_cases

ROOT = Path(__file__).resolve().parents[2]
FIELDS = {
    "query_id", "query", "candidate_key", "source_id", "source_file",
    "source_sha256", "physical_page", "rank", "cosine_score", "excerpt",
    "relevance_grade_0_1_2", "notes",
}
LOCKED_FIELDS = sorted(FIELDS - {"relevance_grade_0_1_2", "notes"})


def row_digest(row: dict[str, str]) -> str:
    locked = {field: row[field] for field in LOCKED_FIELDS}
    return hashlib.sha256(
        json.dumps(locked, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()


def verify_source_files(manifest: dict[str, Any]) -> None:
    for source_id, relative_path in manifest["source_files"].items():
        try:
            with (ROOT / relative_path).open("rb") as stream:
                digest = hashlib.file_digest(stream, "sha256").hexdigest()
        except OSError as exc:
            raise EvaluationFailure(f"source unavailable: {source_id}") from exc
        if digest != manifest["source_hashes"][source_id]:
            raise EvaluationFailure(f"source bytes changed: {source_id}")


def load_review(
    path: Path, cases: list[Case], manifest: dict[str, Any], k: int = 5,
    packet: dict[str, str] | None = None,
) -> dict[str, list[tuple[str, float, int]]]:
    if k <= 0:
        raise ValueError("k must be positive")
    case_by_id = {case.query_id: case for case in cases}
    ranked: dict[str, dict[int, tuple[str, float, int]]] = defaultdict(dict)
    seen: set[tuple[str, str]] = set()
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames is None or not FIELDS.issubset(reader.fieldnames):
            raise EvaluationFailure("review CSV columns do not match the export contract")
        for row in reader:
            query_id = row["query_id"]
            if query_id not in case_by_id or row["query"] != case_by_id[query_id].query:
                raise EvaluationFailure(f"unknown or modified query: {query_id}")
            key = row["candidate_key"]
            source_id = row["source_id"]
            if (query_id, key) in seen:
                raise EvaluationFailure(f"duplicate candidate: {query_id}/{key}")
            seen.add((query_id, key))
            if packet is not None and packet.get(f"{query_id}:{row['rank']}") != row_digest(row):
                raise EvaluationFailure(f"review packet content changed: {query_id}/{row['rank']}")
            if source_id in manifest["source_files"]:
                if (row["source_file"] != manifest["source_files"][source_id]
                    or row["source_sha256"] != manifest["source_hashes"][source_id]
                    or not key.startswith(f"{source_id}:p")
                    or not row["physical_page"].isdigit()
                    or not key.startswith(f"{source_id}:p{row['physical_page']}:c")):
                    raise EvaluationFailure(f"source locator or hash changed: {query_id}/{key}")
            elif (source_id != "synthetic-table:Mechanics!B2"
                  or key != source_id or row["source_sha256"] != "synthetic"
                  or row["physical_page"] or row["source_file"]):
                raise EvaluationFailure(f"unknown or modified source: {query_id}/{key}")
            try:
                rank = int(row["rank"])
                score = float(row["cosine_score"])
                grade = int(row["relevance_grade_0_1_2"])
            except (TypeError, ValueError) as exc:
                raise EvaluationFailure(f"incomplete or invalid rating: {query_id}/{key}") from exc
            if rank not in range(1, k + 1) or rank in ranked[query_id]:
                raise EvaluationFailure(f"duplicate or invalid rank: {query_id}/{rank}")
            if not math.isfinite(score) or not -1 <= score <= 1 or grade not in {0, 1, 2}:
                raise EvaluationFailure(f"invalid score or grade: {query_id}/{key}")
            ranked[query_id][rank] = (key, score, grade)
    for case in cases:
        if set(ranked[case.query_id]) != set(range(1, k + 1)):
            raise EvaluationFailure(f"missing rated ranks: {case.query_id}")
    return {
        query_id: [items[rank] for rank in range(1, k + 1)]
        for query_id, items in ranked.items()
    }


def _dcg(grades: list[int]) -> float:
    return sum((2**grade - 1) / math.log2(rank + 2) for rank, grade in enumerate(grades))


def summarize_review(
    cases: list[Case], ranked: dict[str, list[tuple[str, float, int]]]
) -> dict[str, Any]:
    positive_direct: list[float] = []
    direct_not_first = False
    negative_top: list[float] = []
    result: dict[str, Any] = {
        "label_status": "user_review_of_previously_seen_queries",
        "pool_limit": len(next(iter(ranked.values()))),
        "limits": "Top-k judged pool only; no corpus recall, held-out score, or release threshold",
        "queries": {},
    }
    for case in cases:
        rows = ranked[case.query_id]
        grades = [grade for _, _, grade in rows]
        direct = [rank for rank, grade in enumerate(grades, 1) if grade == 2]
        ideal = _dcg(sorted(grades, reverse=True))
        result["queries"][case.query_id] = {
            "language": case.language,
            "format": case.format,
            "slice": case.slice,
            "direct_hit": bool(direct),
            "direct_mrr": 1 / direct[0] if direct else 0.0,
            "judged_pool_ndcg": _dcg(grades) / ideal if ideal else None,
            "context_only_count": grades.count(1),
            "unsupported_count": grades.count(0),
        }
        if direct:
            positive_direct.append(rows[0][1])
            direct_not_first |= grades[0] != 2
        if all(grade == 0 for grade in grades):
            negative_top.append(rows[0][1])
    values = list(result["queries"].values())
    direct_values = [row for row in values if row["direct_hit"]]
    ranked_values = [row for row in values if row["judged_pool_ndcg"] is not None]
    result["overall"] = {
        "query_count": len(values),
        "queries_with_direct_candidate": len(direct_values),
        "conditional_direct_mrr": mean(row["direct_mrr"] for row in direct_values)
        if direct_values else None,
        "conditional_judged_pool_ndcg": mean(
            row["judged_pool_ndcg"] for row in ranked_values
        ) if ranked_values else None,
        "all_unsupported_query_count": len(negative_top),
        "top1_score_abstention_separable_in_pool": (
            not direct_not_first and min(positive_direct) > max(negative_top)
            if (positive_direct and negative_top
                and len(positive_direct) + len(negative_top) == len(values))
            else None
        ),
    }
    result["by"] = {}
    for dimension in ("language", "format", "slice"):
        groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in values:
            groups[row[dimension]].append(row)
        result["by"][dimension] = {
            name: {
                "queries": len(group),
                "queries_with_direct_candidate": sum(bool(row["direct_hit"]) for row in group),
                "conditional_direct_mrr": mean(
                    row["direct_mrr"] for row in group if row["direct_hit"]
                ) if any(row["direct_hit"] for row in group) else None,
                "conditional_judged_pool_ndcg": mean(
                    row["judged_pool_ndcg"] for row in group
                    if row["judged_pool_ndcg"] is not None
                ) if any(row["judged_pool_ndcg"] is not None for row in group) else None,
            }
            for name, group in sorted(groups.items())
        }
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("review_csv", type=Path)
    parser.add_argument("--k", type=int, default=5)
    args = parser.parse_args()
    cases = load_cases(ROOT / "ml/evals/qrels.jsonl")
    manifest = json.loads((ROOT / "ml/evals/manifest.json").read_text(encoding="utf-8"))
    packet = json.loads(
        (ROOT / "ml/evals/review_packet_e5_large_fixed120.json").read_text(encoding="utf-8")
    )
    try:
        verify_source_files(manifest)
        ranked = load_review(args.review_csv, cases, manifest, args.k, packet)
    except EvaluationFailure as exc:
        parser.exit(2, f"review invalid: {exc}\n")
    print(json.dumps(summarize_review(cases, ranked), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
