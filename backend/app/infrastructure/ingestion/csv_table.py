"""Bounded UTF-8 RFC 4180 table extraction with record and cell locators."""

import csv
from dataclasses import dataclass
from io import StringIO

from app.domain.sources import Locator
from app.infrastructure.ingestion.pdf_text import ExtractionError
from app.infrastructure.ingestion.storage import MAX_CSV_BYTES

MAX_CSV_ROWS = 2000
MAX_CSV_COLUMNS = 50
MAX_CSV_FIELD_CHARS = 4000
MAX_CSV_LABEL_CHARS = 200
MAX_CSV_CELLS = 10000


@dataclass(frozen=True, slots=True)
class ExtractedCell:
    text: str
    locator: Locator


def extract_csv_cells(data: bytes) -> tuple[ExtractedCell, ...]:
    if not data or len(data) > MAX_CSV_BYTES or b"\x00" in data:
        raise ExtractionError("invalid CSV size or bytes")
    try:
        decoded = data.decode("utf-8-sig")
        if "\ufeff" in decoded:
            raise ExtractionError("unexpected CSV byte-order mark")
        reader = csv.reader(StringIO(decoded, newline=""), dialect="excel", strict=True)
        header = next(reader)
        if not 2 <= len(header) <= MAX_CSV_COLUMNS:
            raise ExtractionError("CSV needs two to fifty columns")
        if any(not value.strip() or len(value) > MAX_CSV_LABEL_CHARS for value in header):
            raise ExtractionError("CSV has an empty or oversized header")
        if len(set(header)) != len(header):
            raise ExtractionError("CSV has duplicate headers")
        cells: list[ExtractedCell] = []
        for row_number, row in enumerate(reader, start=2):
            if row_number > MAX_CSV_ROWS:
                raise ExtractionError("CSV exceeds row limit")
            if len(row) != len(header) or any(len(value) > MAX_CSV_FIELD_CHARS for value in row):
                raise ExtractionError("CSV has an irregular or oversized row")
            if not any(value.strip() for value in row):
                continue
            if not row[0].strip() or len(row[0]) > MAX_CSV_LABEL_CHARS:
                raise ExtractionError("CSV row key is empty")
            for column, value in enumerate(row[1:], start=2):
                if not value.strip():
                    continue
                cells.append(
                    ExtractedCell(
                        f"{header[0]}: {row[0]}; {header[column - 1]}: {value}",
                        Locator(
                            table="CSV",
                            row_start=row_number,
                            row_end=row_number,
                            column_start=column,
                            column_end=column,
                        ),
                    )
                )
                if len(cells) > MAX_CSV_CELLS:
                    raise ExtractionError("CSV exceeds cell limit")
        if not cells:
            raise ExtractionError("CSV has no queryable data cells")
        return tuple(cells)
    except (UnicodeError, csv.Error, StopIteration) as exc:
        raise ExtractionError("CSV decoding or parsing failed") from exc
