"""Extract bounded, page-located text from candidate text-layer PDFs."""

from dataclasses import dataclass
from io import BytesIO

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from app.domain.sources import Locator
from app.infrastructure.ingestion.storage import MAX_PDF_BYTES

MAX_PAGES = 200
MAX_PAGE_CHARS = 100_000


class ExtractionError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class ExtractedPage:
    ordinal: int
    text: str
    locator: Locator


def extract_pdf_pages(data: bytes) -> tuple[ExtractedPage, ...]:
    """Return all pages or raise, so callers never publish a partial extraction."""
    if not data or len(data) > MAX_PDF_BYTES:
        raise ExtractionError("invalid PDF size")
    try:
        reader = PdfReader(BytesIO(data), strict=True)
        if reader.is_encrypted:
            raise ExtractionError("encrypted PDF is unsupported")
        page_count = len(reader.pages)
        if not 1 <= page_count <= MAX_PAGES:
            raise ExtractionError("PDF page count is unsupported")
        pages: list[ExtractedPage] = []
        for index, page in enumerate(reader.pages):
            # Content stream order preserves this fixture's columns better than layout mode.
            text = page.extract_text() or ""
            text = text.strip()
            if not text or len(text) > MAX_PAGE_CHARS:
                raise ExtractionError("PDF page has no usable text or exceeds limit")
            pages.append(ExtractedPage(index, text, Locator(page=index + 1)))
        return tuple(pages)
    except (PdfReadError, UnicodeError, KeyError, TypeError, ValueError) as exc:
        if isinstance(exc, ExtractionError):
            raise
        raise ExtractionError("PDF parsing failed") from exc
