import csv
from pathlib import Path

import pytest
from evaluate_passage_review import FIELDS, load_review, row_digest, summarize_review
from retrieval_eval import Case, EvaluationFailure

CASES = [
    Case("q1", "Synthetic question", "en", "pdf_page", "test", "test", {}),
    Case("q2", "Synthetic no-evidence question", "en", "pdf_page", "test", "test", {}),
]
MANIFEST = {"source_files": {"PDF-01": "private/source.pdf"},
            "source_hashes": {"PDF-01": "synthetic-hash"}}


def _rows() -> list[dict[str, str]]:
    return [
        {
            "query_id": query_id, "query": query, "candidate_key": f"PDF-01:p1:c{rank}",
            "source_id": "PDF-01", "source_file": "private/source.pdf",
            "source_sha256": "synthetic-hash", "physical_page": "1", "rank": str(rank),
            "cosine_score": score, "excerpt": "Synthetic excerpt", "relevance_grade_0_1_2": grade,
            "notes": "",
        }
        for query_id, query, ranks in (
            ("q1", "Synthetic question", [(1, "0.8", "0"), (2, "0.7", "2")]),
            ("q2", "Synthetic no-evidence question", [(1, "0.75", "0"), (2, "0.6", "0")]),
        )
        for rank, score, grade in ranks
    ]


def _write(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=sorted(FIELDS))
        writer.writeheader()
        writer.writerows(rows)


def test_review_requires_complete_exact_packet_and_reports_pool_limits(tmp_path: Path) -> None:
    path = tmp_path / "review.csv"
    rows = _rows()
    _write(path, rows)
    packet = {f"{row['query_id']}:{row['rank']}": row_digest(row) for row in rows}
    ranked = load_review(path, CASES, MANIFEST, k=2, packet=packet)
    report = summarize_review(CASES, ranked)
    assert report["overall"]["queries_with_direct_candidate"] == 1
    assert report["overall"]["conditional_direct_mrr"] == 0.5
    assert report["overall"]["all_unsupported_query_count"] == 1
    assert report["overall"]["top1_score_abstention_separable_in_pool"] is False
    assert report["by"]["language"]["en"]["queries"] == 2
    assert "no corpus recall" in report["limits"]
    assert "Synthetic excerpt" not in str(report)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("relevance_grade_0_1_2", "", "incomplete or invalid rating"),
        ("source_sha256", "changed", "source locator or hash changed"),
        ("physical_page", "2", "source locator or hash changed"),
        ("rank", "1", "duplicate or invalid rank"),
    ],
)
def test_review_rejects_edited_identity_or_incomplete_rating(
    tmp_path: Path, field: str, value: str, message: str
) -> None:
    rows = _rows()
    rows[1][field] = value
    path = tmp_path / "review.csv"
    _write(path, rows)
    with pytest.raises(EvaluationFailure, match=message):
        load_review(path, CASES, MANIFEST, k=2)


def test_review_rejects_changed_excerpt_without_disclosing_it(tmp_path: Path) -> None:
    rows = _rows()
    packet = {f"{row['query_id']}:{row['rank']}": row_digest(row) for row in rows}
    rows[0]["excerpt"] = "Changed synthetic excerpt"
    path = tmp_path / "review.csv"
    _write(path, rows)
    with pytest.raises(EvaluationFailure, match="review packet content changed") as error:
        load_review(path, CASES, MANIFEST, k=2, packet=packet)
    assert "Changed synthetic excerpt" not in str(error.value)
