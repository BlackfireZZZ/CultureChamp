"""Resource-limited entry point for parsing one candidate PDF."""

import json
import resource
import sys

from app.infrastructure.ingestion.pdf_text import ExtractionError, extract_pdf_pages


def main() -> int:
    resource.setrlimit(resource.RLIMIT_CPU, (10, 10))
    resource.setrlimit(resource.RLIMIT_AS, (512 * 1024 * 1024, 512 * 1024 * 1024))
    resource.setrlimit(resource.RLIMIT_FSIZE, (0, 0))
    try:
        pages = extract_pdf_pages(sys.stdin.buffer.read())
    except (ExtractionError, MemoryError):
        return 2
    json.dump([[page.ordinal, page.locator.page, page.text] for page in pages], sys.stdout)
    return 0


if __name__ == "__main__":
    sys.exit(main())
