"""Validate bounded worksheet extraction from a separate parser process."""

import json
import subprocess
import sys
from pathlib import Path

from app.domain.sources import Locator
from app.infrastructure.ingestion.csv_table import (
    MAX_CSV_CELLS,
    MAX_CSV_COLUMNS,
    MAX_CSV_FIELD_CHARS,
    MAX_CSV_LABEL_CHARS,
    MAX_CSV_ROWS,
    ExtractedCell,
)
from app.infrastructure.ingestion.pdf_text import ExtractionError
from app.infrastructure.ingestion.storage import MAX_XLSX_BYTES

PARSER_PATH = Path(__file__).with_name("xlsx_parser_child.py")
MAX_RESULT_BYTES = MAX_XLSX_BYTES * 6


def extract_xlsx_isolated(data: bytes, *, timeout_seconds: float = 20) -> tuple[ExtractedCell, ...]:
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
        raise ExtractionError("XLSX parser failed or timed out") from exc
    if result.returncode != 0 or len(result.stdout) > MAX_RESULT_BYTES:
        raise ExtractionError("XLSX parser failed or exceeded output limit")
    try:
        raw = json.loads(result.stdout)
        if not isinstance(raw, list) or not 1 <= len(raw) <= MAX_CSV_CELLS:
            raise ValueError("invalid XLSX cell count")
        cells = []
        for item in raw:
            sheet, row, column, content = item
            if (
                not isinstance(sheet, str)
                or not 1 <= len(sheet) <= 31
                or not isinstance(row, int)
                or not 2 <= row <= MAX_CSV_ROWS
                or not isinstance(column, int)
                or not 2 <= column <= MAX_CSV_COLUMNS
                or not isinstance(content, str)
                or not content
                or len(content) > MAX_CSV_FIELD_CHARS + MAX_CSV_LABEL_CHARS * 2 + 4
            ):
                raise ValueError("invalid XLSX cell")
            cells.append(ExtractedCell(
                content,
                Locator(sheet=sheet, row_start=row, row_end=row,
                        column_start=column, column_end=column),
            ))
        return tuple(cells)
    except (TypeError, ValueError) as exc:
        raise ExtractionError("XLSX parser returned invalid output") from exc
