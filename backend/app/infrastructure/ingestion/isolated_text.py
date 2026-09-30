"""Validate bounded text-parser output before storing source segments."""

import json
import re
import subprocess
import sys
from pathlib import Path

from app.domain.sources import Locator
from app.infrastructure.ingestion.pdf_text import ExtractionError
from app.infrastructure.ingestion.storage import MAX_TEXT_BYTES
from app.infrastructure.ingestion.text_plain import (
    MAX_TEXT_SECTION_CHARS,
    MAX_TEXT_SECTIONS,
    ExtractedTextSection,
)

PARSER_PATH = Path(__file__).with_name("text_parser_child.py")
MAX_RESULT_BYTES = MAX_TEXT_BYTES * 6
SECTION_PATTERN = re.compile(r"(?:Line [1-9]\d*|Lines [1-9]\d*–[1-9]\d*)\Z")


def extract_text_isolated(
    data: bytes, *, timeout_seconds: float = 20
) -> tuple[ExtractedTextSection, ...]:
    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be positive")
    try:
        result = subprocess.run(
            [sys.executable, "-I", str(PARSER_PATH)],
            input=data,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=timeout_seconds,
            cwd="/",
            env={"PYTHONIOENCODING": "utf-8"},
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ExtractionError("text parser failed or timed out") from exc
    if result.returncode != 0 or len(result.stdout) > MAX_RESULT_BYTES:
        raise ExtractionError("text parser failed or exceeded output limit")
    try:
        raw = json.loads(result.stdout)
        if not isinstance(raw, list) or not 1 <= len(raw) <= MAX_TEXT_SECTIONS:
            raise ValueError("invalid section count")
        sections = []
        for expected, item in enumerate(raw):
            ordinal, location, content = item
            if (
                ordinal != expected
                or not isinstance(location, str)
                or not SECTION_PATTERN.fullmatch(location)
                or not isinstance(content, str)
                or not content
                or len(content) > MAX_TEXT_SECTION_CHARS
            ):
                raise ValueError("invalid text section")
            sections.append(ExtractedTextSection(ordinal, content, Locator(section=location)))
        return tuple(sections)
    except (TypeError, ValueError) as exc:
        raise ExtractionError("text parser returned invalid output") from exc
