from io import BytesIO
from pathlib import Path
from subprocess import TimeoutExpired
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.infrastructure.ingestion.isolated_pdf import extract_pdf_isolated
from app.infrastructure.ingestion.pdf_text import ExtractionError, extract_pdf_pages
from app.infrastructure.ingestion.storage import MAX_PDF_BYTES, IntakeError, PrivatePdfStore
from app.main import MAX_REQUEST_BYTES, create_app

FIXTURES = Path(__file__).parents[2] / "data" / "retrieval-fixtures" / "raw"


def test_private_store_retains_exact_fixture_and_deduplicates_retry(tmp_path: Path) -> None:
    store = PrivatePdfStore(tmp_path / "private", public_root=tmp_path / "public")
    source_id = uuid4()
    fixture = next(FIXTURES.glob("51-88-1-SM.pdf"))
    with fixture.open("rb") as stream:
        first = store.store(
            source_id, stream, filename="article.pdf", claimed_media_type="application/pdf"
        )
    with fixture.open("rb") as stream:
        second = store.store(
            source_id, stream, filename="article.pdf", claimed_media_type="application/pdf"
        )
    assert not first.duplicate and second.duplicate
    assert first.storage_key == second.storage_key
    assert first.sha256 == second.sha256
    with store.open_original(first.storage_key) as stored:
        assert stored.read() == fixture.read_bytes()
    assert (tmp_path / "private").stat().st_mode & 0o777 == 0o700


@pytest.mark.parametrize(
    ("data", "filename", "media_type"),
    [
        (b"not a PDF", "fake.pdf", "application/pdf"),
        (b"%PDF-1.4\nno trailer", "broken.pdf", "application/pdf"),
        (b"%PDF-1.4\n%%EOF", "document.txt", "application/pdf"),
        (b"%PDF-1.4\n%%EOF", "document.pdf", "text/plain"),
        (b"%PDF-1.4\n%%EOF", "../document.pdf", "application/pdf"),
    ],
)
def test_store_rejects_spoofed_or_malformed_intake(
    tmp_path: Path, data: bytes, filename: str, media_type: str
) -> None:
    store = PrivatePdfStore(tmp_path / "private")
    with pytest.raises(IntakeError):
        store.store(uuid4(), BytesIO(data), filename=filename, claimed_media_type=media_type)
    assert not list((tmp_path / "private").rglob("*.pdf"))


def test_store_rejects_oversized_stream(tmp_path: Path) -> None:
    store = PrivatePdfStore(tmp_path / "private")
    payload = b"%PDF-1.4\n" + b"x" * MAX_PDF_BYTES + b"%%EOF"
    with pytest.raises(IntakeError, match="size"):
        store.store(
            uuid4(), BytesIO(payload), filename="large.pdf", claimed_media_type="application/pdf"
        )


def test_request_body_is_rejected_before_multipart_spooling() -> None:
    with TestClient(create_app()) as client:
        response = client.post(
            "/api/v1/admin/sources",
            content=b"x" * (MAX_REQUEST_BYTES + 1),
            headers={"content-type": "multipart/form-data; boundary=none"},
        )
    assert response.status_code == 413


def test_store_rejects_public_root(tmp_path: Path) -> None:
    with pytest.raises(IntakeError):
        PrivatePdfStore(tmp_path / "public" / "uploads", public_root=tmp_path / "public")


@pytest.mark.parametrize("name,pages", [("51-88-1-SM", 15), ("perspektivy", 10), ("problemy", 7)])
def test_pdf_extraction_preserves_nonempty_physical_pages(name: str, pages: int) -> None:
    fixture = next(FIXTURES.glob(f"{name}*.pdf"))
    extracted = extract_pdf_pages(fixture.read_bytes())
    assert len(extracted) == pages
    assert [page.ordinal for page in extracted] == list(range(pages))
    assert [page.locator.page for page in extracted] == list(range(1, pages + 1))
    assert all(page.text for page in extracted)


def test_two_column_fixture_stays_in_column_order_on_sampled_page() -> None:
    fixture = next(FIXTURES.glob("problemy*.pdf"))
    page_two = extract_pdf_pages(fixture.read_bytes())[1].text
    assert page_two.index("Для примера") < page_two.index("Неоднократно")
    assert page_two.index("Неоднократно") < page_two.index("хозяйства, т. е.")


@pytest.mark.parametrize("data", [b"not a PDF", b"%PDF-1.4\n%%EOF", b""])
def test_malformed_pdf_fails_without_partial_pages(data: bytes) -> None:
    with pytest.raises(ExtractionError):
        extract_pdf_pages(data)


def test_isolated_parser_returns_physical_pages_and_safe_failure() -> None:
    fixture = next(FIXTURES.glob("51-88-1-SM.pdf"))
    pages = extract_pdf_isolated(fixture.read_bytes())
    assert len(pages) == 15
    assert pages[0].locator.page == 1
    with pytest.raises(ExtractionError):
        extract_pdf_isolated(b"%PDF-1.4\n%%EOF")


def test_isolated_parser_timeout_is_bounded(monkeypatch: pytest.MonkeyPatch) -> None:
    def timed_out(*args: object, **kwargs: object) -> None:
        raise TimeoutExpired("parser", 0.01)

    monkeypatch.setattr("app.infrastructure.ingestion.isolated_pdf.subprocess.run", timed_out)
    with pytest.raises(ExtractionError, match="timed out"):
        extract_pdf_isolated(b"%PDF-1.4\n%%EOF", timeout_seconds=0.01)
