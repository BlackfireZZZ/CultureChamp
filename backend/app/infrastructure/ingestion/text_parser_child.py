"""Resource-limited entry point for one candidate UTF-8 text file."""

import json
import resource
import sys

from app.infrastructure.ingestion.pdf_text import ExtractionError
from app.infrastructure.ingestion.text_plain import extract_text_sections


def main() -> int:
    resource.setrlimit(resource.RLIMIT_CPU, (10, 10))
    resource.setrlimit(resource.RLIMIT_AS, (512 * 1024 * 1024, 512 * 1024 * 1024))
    resource.setrlimit(resource.RLIMIT_FSIZE, (0, 0))
    try:
        sections = extract_text_sections(sys.stdin.buffer.read())
    except (ExtractionError, MemoryError):
        return 2
    json.dump(
        [
            [section.ordinal, section.locator.section, section.text]
            for section in sections
        ],
        sys.stdout,
        ensure_ascii=False,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
