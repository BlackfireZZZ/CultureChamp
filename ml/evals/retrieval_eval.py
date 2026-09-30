"""Offline page/locator retrieval evaluation for provisional and reviewed qrels."""

import argparse
import json
import math
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class EvaluationFailure(Exception):
    pass


@dataclass(frozen=True)
class Case:
    query_id: str
    query: str
    language: str
    format: str
    slice: str
    label_status: str
    grades: dict[str, int]


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise EvaluationFailure(f"{path}:{line_number}: invalid JSON") from exc
        if not isinstance(row, dict):
            raise EvaluationFailure(f"{path}:{line_number}: expected object")
        rows.append(row)
    return rows


def load_cases(path: Path) -> list[Case]:
    cases: list[Case] = []
    seen: set[str] = set()
    for row in read_jsonl(path):
        query_id = str(row["query_id"])
        if query_id in seen:
            raise EvaluationFailure(f"duplicate query_id: {query_id}")
        seen.add(query_id)
        grades: dict[str, int] = {}
        for judgement in row["judgments"]:
            key = str(judgement["candidate_key"])
            grade = judgement["grade"]
            if key in grades or not isinstance(grade, int) or grade not in {0, 1, 2}:
                raise EvaluationFailure(f"invalid or duplicate judgement: {query_id}/{key}")
            grades[key] = grade
        cases.append(
            Case(
                query_id=query_id,
                query=str(row["query"]),
                language=str(row["language"]),
                format=str(row["format"]),
                slice=str(row["slice"]),
                label_status=str(row["label_status"]),
                grades=grades,
            )
        )
    if not cases:
        raise EvaluationFailure("no judgement cases")
    return cases


def load_run(path: Path, cases: list[Case]) -> dict[str, list[str]]:
    valid_ids = {case.query_id for case in cases}
    run: dict[str, list[str]] = {}
    for row in read_jsonl(path):
        query_id = str(row["query_id"])
        keys = row["candidate_keys"]
        if query_id not in valid_ids or query_id in run:
            raise EvaluationFailure(f"unknown or duplicate run query_id: {query_id}")
        if not isinstance(keys, list) or any(not isinstance(key, str) for key in keys):
            raise EvaluationFailure(f"invalid ranking: {query_id}")
        if len(set(keys)) != len(keys):
            raise EvaluationFailure(f"duplicate retrieved key: {query_id}")
        run[query_id] = keys
    return run


def _dcg(grades: list[int]) -> float:
    return sum((2**grade - 1) / math.log2(rank + 2) for rank, grade in enumerate(grades))


def score_case(case: Case, ranking: list[str], k: int) -> dict[str, float]:
    if k <= 0:
        raise ValueError("k must be positive")
    relevant = {key for key, grade in case.grades.items() if grade > 0}
    top = ranking[:k]
    if not relevant:
        return {"recall": 0.0, "mrr": 0.0, "ndcg": 0.0, "false_positive": float(bool(top))}
    hits = sum(key in relevant for key in top)
    first_rank = next((rank for rank, key in enumerate(top, 1) if key in relevant), None)
    dcg = _dcg([case.grades.get(key, 0) for key in top])
    ideal = _dcg(sorted(case.grades.values(), reverse=True)[:k])
    return {
        "recall": hits / len(relevant),
        "mrr": 1 / first_rank if first_rank else 0.0,
        "ndcg": dcg / ideal if ideal else 0.0,
        "false_positive": 0.0,
    }


def summarize(cases: list[Case], run: dict[str, list[str]], k: int) -> dict[str, Any]:
    scored = [(case, score_case(case, run.get(case.query_id, []), k)) for case in cases]

    def aggregate(rows: list[tuple[Case, dict[str, float]]]) -> dict[str, float | int]:
        positive = [scores for case, scores in rows if any(g > 0 for g in case.grades.values())]
        negative = [scores for case, scores in rows if not any(g > 0 for g in case.grades.values())]
        return {
            "queries": len(rows),
            "positive_queries": len(positive),
            "no_evidence_queries": len(negative),
            "recall_at_k": sum(x["recall"] for x in positive) / len(positive) if positive else 0.0,
            "mrr_at_k": sum(x["mrr"] for x in positive) / len(positive) if positive else 0.0,
            "ndcg_at_k": sum(x["ndcg"] for x in positive) / len(positive) if positive else 0.0,
            "no_evidence_false_positive_rate": (
                sum(x["false_positive"] for x in negative) / len(negative) if negative else 0.0
            ),
        }

    slices: dict[str, dict[str, dict[str, float | int]]] = {}
    for dimension in ("language", "format", "slice"):
        groups: dict[str, list[tuple[Case, dict[str, float]]]] = defaultdict(list)
        for case, scores in scored:
            groups[getattr(case, dimension)].append((case, scores))
        slices[dimension] = {name: aggregate(rows) for name, rows in sorted(groups.items())}
    return {
        "k": k,
        "label_statuses": sorted({case.label_status for case in cases}),
        "overall": aggregate(scored),
        "by": slices,
    }


def assert_required_recall(cases: list[Case], run: dict[str, list[str]], k: int) -> None:
    failures: list[str] = []
    for case in cases:
        expected = {key for key, grade in case.grades.items() if grade > 0}
        returned = set(run.get(case.query_id, [])[:k])
        missing = sorted(expected - returned)
        if missing:
            failures.append(f"{case.query_id}: missing {', '.join(missing)}")
        if not expected and returned:
            failures.append(f"{case.query_id}: no-evidence case returned candidates")
    if failures:
        raise EvaluationFailure("required recall failed: " + "; ".join(failures))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("qrels", type=Path)
    parser.add_argument("run", type=Path)
    parser.add_argument("--k", type=int, default=5)
    parser.add_argument("--require-all", action="store_true")
    args = parser.parse_args()
    cases = load_cases(args.qrels)
    run = load_run(args.run, cases)
    if args.require_all:
        assert_required_recall(cases, run, args.k)
    print(json.dumps(summarize(cases, run, args.k), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
