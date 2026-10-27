"""Scoring counterexamples: hashes, exact spans, overlaps and split leakage."""

import pytest
from runner import aggregate, coverage, fusion, score_question, validate_questions


def evidence(start=100, end=200):
    return {"source_id": "s1", "source_hash": "abc", "locator": "pdf:page:2",
            "start": start, "end": end, "quote": "x" * (end-start)}


def hit(start=100, end=200, **changes):
    return {**evidence(start, end), "key": f"{start}-{end}", **changes}


def question(**changes):
    return {"query_id": "q1", "query": "a question", "family": "f1", "split": "dev",
            "evidence": [evidence()], **changes}


def test_wrong_page_source_and_hash_cannot_match():
    for change in ({"locator": "pdf:page:3"}, {"source_id": "s2"}, {"source_hash": "old"}):
        assert coverage(evidence(), [hit(**change)]) == 0
    assert coverage(evidence(), [hit(0, 99)]) == 0


def test_union_overlap_is_not_double_counted():
    assert coverage(evidence(), [hit(100, 140), hit(120, 160)]) == 0.6
    assert coverage(evidence(), [hit(100, 140), hit(140, 180)]) == 0.8
    assert coverage(evidence(), [hit(0, 300)]) == 1.0


def test_union_success_is_separate_from_single_chunk_hit():
    row = score_question(question(), [hit(100, 140), hit(140, 180)])
    assert row["union_any5"] == 1
    assert row["all_evidence5"] == 1
    assert row["hit5"] == 0
    assert row["reciprocal_rank10"] == 0


def test_any_hit_and_all_spans_differ():
    q = question(evidence=[evidence(), evidence(300, 400)])
    row = score_question(q, [hit()])
    assert row["hit5"] == 1
    assert row["all_evidence5"] == 0
    assert row["evidence_coverage5"] == 0.5


def test_rank_cutoffs_and_duplicates():
    misses = [hit(i, i+1) for i in range(6)]
    row = score_question(question(), [misses[0], misses[0], *misses[1:], hit()])
    assert row["hit5"] == 0
    assert row["hit10"] == 1
    assert row["reciprocal_rank10"] == pytest.approx(1/7)


def test_diagnostics_do_not_inflate_denominator():
    rows = [score_question(question(), [hit()]),
            score_question(question(query_id="absent", evidence=[]), [hit()])]
    metrics = aggregate(rows)
    assert metrics["questions"] == 1
    assert metrics["diagnostics"] == 1
    assert metrics["hit5"] == 1
    assert metrics["hit5_successes"] == 1
    assert metrics["hit5_wilson95"][0] < 0.3


def test_validator_rejects_mutated_gold_and_split_leakage():
    unit = {"source_id": "s1", "source_hash": "abc", "locator": "pdf:page:2",
            "text": "x" * 500}
    validate_questions([question()], [unit])
    for changed in ({"quote": "wrong"}, {"source_hash": "stale"}, {"end": 999}):
        with pytest.raises(ValueError):
            validate_questions([question(evidence=[{**evidence(), **changed}])], [unit])
    with pytest.raises(ValueError, match="crosses splits"):
        validate_questions([question(), question(query_id="q2", split="test")], [unit])


def test_fusion_deduplicates_and_is_deterministic():
    assert fusion([[1, 1, 2], [2, 3]]) == [2, 1, 3]


def test_family_requires_both_styles_to_hit():
    from runner import family_aggregate
    questions = [question(), question(query_id="q2")]
    rows = [score_question(questions[0], [hit()]), score_question(questions[1], [])]
    assert aggregate(rows)["hit5"] == 0.5
    result = family_aggregate(questions, rows)
    assert result["families"] == 1
    assert result["hit5"] == 0
    assert result["reciprocal_rank10"] == 0


def test_inventory_verifies_original_and_extracted_hashes(tmp_path):
    import hashlib
    import json

    from runner import validate_inventory
    path = tmp_path / "original.txt"
    path.write_text("source")
    source_hash = hashlib.sha256(path.read_bytes()).hexdigest()
    (tmp_path / "inventory.json").write_text(json.dumps([
        {"source_id": "s1", "sha256": source_hash, "path": str(path)}]))
    units = [{"source_id": "s1", "source_hash": source_hash, "locator": "page1"}]
    validate_inventory(tmp_path, units)
    with pytest.raises(ValueError, match="corpus source hash"):
        validate_inventory(tmp_path, [{**units[0], "source_hash": "wrong"}])
    path.write_text("changed")
    with pytest.raises(ValueError, match="Original source hash"):
        validate_inventory(tmp_path, units)


def test_snapshot_requires_immutable_identifier(monkeypatch, tmp_path):
    import sys
    from types import SimpleNamespace

    from runner import resolve_snapshot

    huggingface_hub = SimpleNamespace(snapshot_download=None)
    monkeypatch.setitem(sys.modules, "huggingface_hub", huggingface_hub)
    calls = []

    def fake_download(repo, **kwargs):
        calls.append((repo, kwargs))
        return str(tmp_path / "snapshots" / ("a" * 40))

    monkeypatch.setattr(huggingface_hub, "snapshot_download", fake_download)
    assert resolve_snapshot("organization/model", tmp_path)[1] == "a" * 40
    assert calls[0][1] == {"cache_dir": str(tmp_path), "local_files_only": True,
                           "allow_patterns": ["config.json"]}
    monkeypatch.setattr(huggingface_hub, "snapshot_download", lambda *a, **kw: "/cache/main")
    with pytest.raises(ValueError, match="immutable"):
        resolve_snapshot("organization/model")


def test_token_lengths_report_truncation_without_truncating():
    from runner import token_lengths

    class Tokenizer:
        def __call__(self, texts, **kwargs):
            assert kwargs["truncation"] is False
            return {"length": [len(text) for text in texts]}

    result = token_lengths(Tokenizer(), ["a" * 511, "b" * 513], 512)
    assert result["over_limit"] == 1
    assert result["maximum_tokens"] == 513


def test_union_preserves_tail_dense_and_lexical_candidates():
    from runner import candidate_coverage, candidate_union
    # Gold appears at dense rank 48 and lexical rank 5; dense top30 misses it.
    dense = list(range(50))
    lexical = [50, 51, 52, 53, 47, *range(54, 99)]
    combined = candidate_union([dense, lexical])
    assert len(combined) == 99
    assert combined.count(47) == 1
    assert set(dense).issubset(combined)
    assert set(lexical).issubset(combined)
    passages = [hit(i, i+1, key=str(i)) for i in range(99)]
    passages[47] = hit(key="gold")
    assert candidate_coverage([question()], [dense[:30]], passages)["candidate_any_hit"] == 0
    result = candidate_coverage([question()], [combined], passages)
    assert result["candidate_any_hit"] == 1
    assert result["candidate_all_evidence"] == 1
    assert result["maximum_candidates"] == 99


def test_union_candidate_coverage_requires_all_gold_spans():
    from runner import candidate_coverage, candidate_union
    q = question(evidence=[evidence(), evidence(300, 400)])
    passages = [hit(), hit(300, 400), hit(0, 10)]
    combined = candidate_union([[0, 2], [1, 2]])
    assert combined == [0, 2, 1]
    result = candidate_coverage([q], [combined], passages)
    assert result["candidate_any_hit"] == result["candidate_all_evidence"] == 1
    result = candidate_coverage([q], [[0]], passages)
    assert result["candidate_any_hit"] == 1
    assert result["candidate_all_evidence"] == 0
