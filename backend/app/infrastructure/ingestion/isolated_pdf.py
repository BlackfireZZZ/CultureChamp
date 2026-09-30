"""Parse candidate bytes outside the long-lived database worker process."""

import json
import subprocess
import sys
from pathlib import Path

from app.domain.sources import Locator
from app.infrastructure.ingestion.pdf_text import (
    MAX_PAGE_CHARS,
    MAX_PAGES,
    ExtractedPage,
    ExtractionError,
)

PARSER_PATH = Path(__file__).with_name("pdf_parser_child.py")
MAX_RESULT_BYTES = MAX_PAGES * (MAX_PAGE_CHARS * 4 + 64)


def extract_pdf_isolated(data: bytes, *, timeout_seconds: float = 20) -> tuple[ExtractedPage, ...]:
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
        raise ExtractionError("PDF parser failed or timed out") from exc
    if result.returncode != 0 or len(result.stdout) > MAX_RESULT_BYTES:
        raise ExtractionError("PDF parser failed or exceeded output limit")
    try:
        raw = json.loads(result.stdout)
        if not isinstance(raw, list) or not 1 <= len(raw) <= MAX_PAGES:
            raise ValueError("invalid page count")
        pages = []
        for expected_ordinal, item in enumerate(raw):
            ordinal, page, content = item
            if (
                ordinal != expected_ordinal
                or page != expected_ordinal + 1
                or not isinstance(content, str)
                or not content
                or len(content) > MAX_PAGE_CHARS
            ):
                raise ValueError("invalid page")
            pages.append(ExtractedPage(ordinal, content, Locator(page=page)))
        return tuple(pages)
    except (TypeError, ValueError) as exc:
        raise ExtractionError("PDF parser returned invalid output") from exc
