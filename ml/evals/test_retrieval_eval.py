import hashlib
import json
from pathlib import Path

import pytest
from retrieval_eval import (
    EvaluationFailure,
    assert_required_recall,
    load_cases,
    load_run,
    summarize,
)

HERE = Path(__file__).parent
RAW = HERE.parents[1] / "data/retrieval-fixtures/raw"


def test_oracle_smoke_reports_slices_and_no_evidence() -> None:
    cases = load_cases(HERE / "qrels.jsonl")
    run = load_run(HERE / "runs/oracle_smoke.jsonl", cases)
    assert_required_recall(cases, run, 5)
    report = summarize(cases, run, 5)
    assert report["overall"]["recall_at_k"] == 1.0
    assert report["overall"]["no_evidence_false_positive_rate"] == 0.0
    assert report["by"]["format"]["synthetic_table_cell"]["queries"] == 1
    assert report["by"]["language"]["ru"]["queries"] == 7
    assert report["label_statuses"] == ["provisional_agent"]


def test_missing_relevant_page_fails() -> None:
    cases = load_cases(HERE / "qrels.jsonl")
    run = load_run(HERE / "runs/oracle_smoke.jsonl", cases)
    run["S05-03"].remove("PDF-03:p4")
    with pytest.raises(EvaluationFailure, match="S05-03: missing PDF-03:p4"):
        assert_required_recall(cases, run, 5)


def test_no_evidence_false_positive_and_duplicate_ranking_fail() -> None:
    cases = load_cases(HERE / "qrels.jsonl")
    run = load_run(HERE / "runs/oracle_smoke.jsonl", cases)
    run["S05-05"] = ["PDF-01:p2"]
    assert summarize(cases, run, 5)["overall"]["no_evidence_false_positive_rate"] > 0
    with pytest.raises(EvaluationFailure, match="S05-05: no-evidence"):
        assert_required_recall(cases, run, 5)


def test_fixture_hashes_and_synthetic_locator_are_versioned() -> None:
    manifest = json.loads((HERE / "manifest.json").read_text(encoding="utf-8"))
    names = {
        "PDF-01": "51-88-1-SM.pdf",
        "PDF-02": (
            "perspektivy-etnoekologicheskih-issledovaniy-kultury-korennyh-narodov-"
            "rossiyskogo-dalnego-vostoka.pdf"
        ),
        "PDF-03": (
            "problemy-traditsionnoy-kultury-korennyh-malochislennyh-narodov-yuga-"
            "dalnego-vostoka-rossii-i-roli-gosudarstva-v-etih-protsessah-xx-nachalo-"
            "xxi-veka.pdf"
        ),
    }
    for source_id, name in names.items():
        digest = hashlib.sha256((RAW / name).read_bytes()).hexdigest()
        assert digest == manifest["source_hashes"][source_id]
    table = json.loads((HERE / "synthetic_table.json").read_text(encoding="utf-8"))
    assert table["synthetic"] is True
    assert table["target_locator"] == "synthetic-table:Mechanics!B2"
