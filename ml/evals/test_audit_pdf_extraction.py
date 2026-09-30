import pytest
from audit_pdf_extraction import compare_texts, normalized_tokens


def test_normalization_joins_line_hyphenation_without_joining_regular_words() -> None:
    assert normalized_tokens("Тради-\nция, и другая традиция") == [
        "традиция", "и", "другая", "традиция"
    ]


def test_order_and_content_disagreement_are_distinct() -> None:
    reordered = compare_texts("alpha beta gamma delta", "gamma delta alpha beta")
    assert reordered["unordered_first_coverage"] == 1.0
    assert reordered["ordered_first_coverage"] == 0.5
    missing = compare_texts("alpha beta gamma delta", "alpha beta")
    assert missing["unordered_first_coverage"] == 0.5
    assert missing["ordered_first_coverage"] == 0.5


def test_empty_text_layer_fails_instead_of_reporting_zero_coverage() -> None:
    with pytest.raises(ValueError):
        compare_texts("text", "")
