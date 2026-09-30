"""Validate the bounded parser child output before storing table cells."""

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
from app.infrastructure.ingestion.storage import MAX_CSV_BYTES

PARSER_PATH = Path(__file__).with_name("csv_parser_child.py")
MAX_RESULT_BYTES = MAX_CSV_BYTES * 6


def extract_csv_isolated(data: bytes, *, timeout_seconds: float = 20) -> tuple[ExtractedCell, ...]:
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
        raise ExtractionError("CSV parser failed or timed out") from exc
    if result.returncode != 0 or len(result.stdout) > MAX_RESULT_BYTES:
        raise ExtractionError("CSV parser failed or exceeded output limit")
    try:
        raw = json.loads(result.stdout)
        if not isinstance(raw, list) or not 1 <= len(raw) <= MAX_CSV_CELLS:
            raise ValueError("invalid cell count")
        cells = []
        for item in raw:
            row, column, content = item
            if (
                not isinstance(row, int)
                or not 2 <= row <= MAX_CSV_ROWS
                or not isinstance(column, int)
                or not 2 <= column <= MAX_CSV_COLUMNS
                or not isinstance(content, str)
                or not content
                or len(content) > MAX_CSV_FIELD_CHARS + MAX_CSV_LABEL_CHARS * 2 + 4
            ):
                raise ValueError("invalid cell")
            cells.append(
                ExtractedCell(
                    content,
                    Locator(
                        table="CSV",
                        row_start=row,
                        row_end=row,
                        column_start=column,
                        column_end=column,
                    ),
                )
            )
        return tuple(cells)
    except (TypeError, ValueError) as exc:
        raise ExtractionError("CSV parser returned invalid output") from exc
