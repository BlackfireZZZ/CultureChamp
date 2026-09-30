"""Bounded UTF-8 text extraction with stable line ranges in an immutable revision."""

from dataclasses import dataclass

from app.domain.sources import Locator
from app.infrastructure.ingestion.pdf_text import ExtractionError
from app.infrastructure.ingestion.storage import MAX_TEXT_BYTES

MAX_TEXT_LINES = 10_000
MAX_TEXT_LINE_CHARS = 4_000
MAX_TEXT_SECTION_CHARS = 10_000
MAX_TEXT_SECTIONS = 1_000


@dataclass(frozen=True, slots=True)
class ExtractedTextSection:
    ordinal: int
    text: str
    locator: Locator


def line_section(start: int, end: int) -> str:
    return f"Line {start}" if start == end else f"Lines {start}–{end}"


def extract_text_sections(data: bytes) -> tuple[ExtractedTextSection, ...]:
    if not data or len(data) > MAX_TEXT_BYTES or b"\x00" in data:
        raise ExtractionError("invalid text size or bytes")
    try:
        decoded = data.decode("utf-8-sig")
    except UnicodeError as exc:
        raise ExtractionError("text is not UTF-8") from exc
    if "\ufeff" in decoded:
        raise ExtractionError("unexpected text byte-order mark")
    lines = decoded.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    if len(lines) > MAX_TEXT_LINES or any(len(line) > MAX_TEXT_LINE_CHARS for line in lines):
        raise ExtractionError("text line limit exceeded")
    sections: list[ExtractedTextSection] = []
    group: list[str] = []
    start = 0
    chars = 0

    def flush(end: int) -> None:
        nonlocal chars, start
        if not group:
            return
        sections.append(
            ExtractedTextSection(
                len(sections), "\n".join(group), Locator(section=line_section(start, end))
            )
        )
        if len(sections) > MAX_TEXT_SECTIONS:
            raise ExtractionError("text section limit exceeded")
        group.clear()
        chars = 0
        start = 0

    for number, line in enumerate(lines, start=1):
        content = line.strip()
        if not content:
            flush(number - 1)
            continue
        if group and chars + 1 + len(content) > MAX_TEXT_SECTION_CHARS:
            flush(number - 1)
        if not group:
            start = number
        group.append(content)
        chars += len(content) + (1 if len(group) > 1 else 0)
    flush(len(lines))
    if not sections:
        raise ExtractionError("text has no usable content")
    return tuple(sections)
