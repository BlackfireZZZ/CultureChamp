"""Deterministic text windows that retain the original page locator."""


def chunk_text(text: str, *, max_words: int = 120, overlap_words: int = 30) -> tuple[str, ...]:
    if max_words <= 0 or not 0 <= overlap_words < max_words:
        raise ValueError("Invalid text window")
    words = text.split()
    if not words:
        return ()
    step = max_words - overlap_words
    return tuple(
        " ".join(words[start : start + max_words])
        for start in range(0, len(words), step)
        if start == 0 or start + overlap_words < len(words)
    )
