"""Resource-limited entry point for one candidate XLSX workbook."""

import json
import resource
import sys

from app.infrastructure.ingestion.pdf_text import ExtractionError
from app.infrastructure.ingestion.xlsx_table import extract_xlsx_cells


def main() -> int:
    resource.setrlimit(resource.RLIMIT_CPU, (10, 10))
    resource.setrlimit(resource.RLIMIT_AS, (512 * 1024 * 1024, 512 * 1024 * 1024))
    resource.setrlimit(resource.RLIMIT_FSIZE, (0, 0))
    try:
        cells = extract_xlsx_cells(sys.stdin.buffer.read())
    except (ExtractionError, MemoryError):
        return 2
    json.dump(
        [[cell.locator.sheet, cell.locator.row_start, cell.locator.column_start, cell.text]
         for cell in cells],
        sys.stdout,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
