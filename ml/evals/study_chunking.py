"""Offline passage candidates for controlled retrieval comparisons.

This is not a PDF parser. It operates within one already located page and must
not be used to assert reading order or paragraph boundaries of a source PDF.
"""

import json
import re
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


class Encoded(Protocol):
    ids: list[int]


class Tokenizer(Protocol):
    def encode(self, text: str) -> Encoded | list[int]: ...


@dataclass(frozen=True)
class PictureRegion:
    page: int
    bbox: tuple[float, float, float, float]
    texts: tuple[str, ...]


_SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?…])\s+(?=[A-ZА-ЯЁ])")


def token_count(tokenizer: Tokenizer, text: str) -> int:
    encoded = tokenizer.encode(text)
    return len(encoded if isinstance(encoded, list) else encoded.ids)


def sentence_token_windows(text: str, tokenizer: Tokenizer, max_tokens: int) -> tuple[str, ...]:
    """Group visible sentences within a model-token budget for an offline ablation."""
    if max_tokens < 16:
        raise ValueError("max_tokens must be at least 16")
    normalized = " ".join(text.split())
    if not normalized:
        return ()
    sentences = _SENTENCE_BOUNDARY.split(normalized)
    units: list[str] = []
    for sentence in sentences:
        if token_count(tokenizer, sentence) <= max_tokens:
            units.append(sentence)
            continue
        words = sentence.split()
        current: list[str] = []
        for word in words:
            candidate = " ".join([*current, word])
            if token_count(tokenizer, candidate) > max_tokens:
                if not current:
                    raise ValueError("one word exceeds token budget")
                units.append(" ".join(current))
                current = [word]
                if token_count(tokenizer, word) > max_tokens:
                    raise ValueError("one word exceeds token budget")
            else:
                current.append(word)
        if current:
            units.append(" ".join(current))
    chunks: list[str] = []
    current = []
    for unit in units:
        candidate = " ".join([*current, unit])
        if current and token_count(tokenizer, candidate) > max_tokens:
            chunks.append(" ".join(current))
            current = [unit]
        else:
            current.append(unit)
    if current:
        chunks.append(" ".join(current))
    if any(token_count(tokenizer, chunk) > max_tokens for chunk in chunks):
        raise AssertionError("token budget exceeded")
    return tuple(chunks)


def block_token_windows(
    blocks: Sequence[str], tokenizer: Tokenizer, max_tokens: int
) -> tuple[str, ...]:
    """Merge adjacent layout blocks, splitting only blocks over budget."""
    if max_tokens < 16:
        raise ValueError("max_tokens must be at least 16")
    chunks: list[str] = []
    current: list[str] = []
    for block in blocks:
        normalized = " ".join(block.split())
        if not normalized:
            continue
        units = (
            (normalized,)
            if token_count(tokenizer, normalized) <= max_tokens
            else sentence_token_windows(normalized, tokenizer, max_tokens)
        )
        for unit in units:
            candidate = " ".join([*current, unit])
            if current and token_count(tokenizer, candidate) > max_tokens:
                chunks.append(" ".join(current))
                current = [unit]
            else:
                current.append(unit)
    if current:
        chunks.append(" ".join(current))
    return tuple(chunks)


def docling_pages(path: Path) -> dict[int, list[str]]:
    """Read located body blocks in Docling order; ignore headers and footers."""
    document = json.loads(path.read_text(encoding="utf-8"))
    pages: dict[int, list[str]] = {int(number): [] for number in document["pages"]}

    def walk(node: dict[str, str]) -> None:
        kind, index = node["$ref"].strip("#/").split("/")
        item = document[kind][int(index)]
        if kind == "groups":
            for child in item.get("children", []):
                walk(child)
        elif kind == "texts" and item["label"] not in {"page_header", "page_footer"}:
            provenance = item.get("prov", [])
            page_numbers = {entry["page_no"] for entry in provenance}
            if len(page_numbers) != 1:
                raise ValueError("text item needs one source page for this study")
            pages[page_numbers.pop()].append(item["text"])

    for child in document["body"]["children"]:
        walk(child)
    if not all(pages.values()):
        raise ValueError("Docling produced an empty body page")
    return pages


def docling_picture_regions(path: Path) -> tuple[PictureRegion, ...]:
    """Keep OCR text attached to a figure and its PDF-space region for review."""
    document = json.loads(path.read_text(encoding="utf-8"))
    regions: list[PictureRegion] = []
    for picture in document.get("pictures", []):
        provenance = picture.get("prov", [])
        page_numbers = {entry["page_no"] for entry in provenance}
        if len(page_numbers) != 1 or len(provenance) != 1:
            raise ValueError("picture needs one source region for this study")
        bbox = provenance[0]["bbox"]
        if bbox["coord_origin"] != "BOTTOMLEFT":
            raise ValueError("unexpected picture coordinate system")
        children = picture.get("children", [])
        texts = tuple(
            document["texts"][int(child["$ref"].removeprefix("#/texts/"))]["text"]
            for child in children
            if child["$ref"].startswith("#/texts/")
        )
        regions.append(
            PictureRegion(
                page=page_numbers.pop(),
                bbox=(bbox["l"], bbox["b"], bbox["r"], bbox["t"]),
                texts=texts,
            )
        )
    return tuple(regions)
