from io import BytesIO
from pathlib import Path
from subprocess import TimeoutExpired
from uuid import uuid4
from zipfile import ZIP_DEFLATED, ZipFile

import pytest
from fastapi.testclient import TestClient
from openpyxl import Workbook
from pdf_fixture import self_authored_pdf
from xlsx_fixture import self_authored_xlsx

from app.infrastructure.ingestion.chunking import chunk_text
from app.infrastructure.ingestion.csv_table import extract_csv_cells
from app.infrastructure.ingestion.isolated_csv import extract_csv_isolated
from app.infrastructure.ingestion.isolated_pdf import extract_pdf_isolated
from app.infrastructure.ingestion.isolated_text import extract_text_isolated
from app.infrastructure.ingestion.isolated_xlsx import extract_xlsx_isolated
from app.infrastructure.ingestion.pdf_text import ExtractionError, extract_pdf_pages
from app.infrastructure.ingestion.storage import (
    MAX_PDF_BYTES,
    MAX_TEXT_BYTES,
    IntakeError,
    PrivateOriginalStore,
)
from app.infrastructure.ingestion.text_plain import extract_text_sections
from app.infrastructure.ingestion.xlsx_table import extract_xlsx_cells
from app.main import MAX_REQUEST_BYTES, create_app


def test_long_page_keeps_searchable_tail_with_context_overlap() -> None:
    text = " ".join([*(f"context{i}" for i in range(250)), "unique-tail-evidence"])
    chunks = chunk_text(text)
    assert len(chunks) > 1
    assert "unique-tail-evidence" in chunks[-1]
    assert set(chunks[0].split()) & set(chunks[1].split())
    assert all(len(chunk.split()) <= 120 for chunk in chunks)


def test_private_store_retains_exact_fixture_and_deduplicates_retry(tmp_path: Path) -> None:
    store = PrivateOriginalStore(tmp_path / "private", public_root=tmp_path / "public")
    source_id = uuid4()
    fixture = self_authored_pdf("Self authored test document")
    with BytesIO(fixture) as stream:
        first = store.store(
            source_id, stream, filename="article.pdf", claimed_media_type="application/pdf"
        )
    with BytesIO(fixture) as stream:
        second = store.store(
            source_id, stream, filename="article.pdf", claimed_media_type="application/pdf"
        )
    assert not first.duplicate and second.duplicate
    assert first.storage_key == second.storage_key
    assert first.sha256 == second.sha256
    with store.open_original(first.storage_key) as stored:
        assert stored.read() == fixture
    assert (tmp_path / "private").stat().st_mode & 0o777 == 0o700


def test_utf8_text_keeps_original_bytes_and_exact_line_sections(tmp_path: Path) -> None:
    fixture = b"Synthetic first line\r\nsecond line\r\n\r\nAnother paragraph\r\n"
    store = PrivateOriginalStore(tmp_path / "private")
    stored = store.store(
        uuid4(), BytesIO(fixture), filename="self-authored.txt", claimed_media_type="text/plain"
    )
    with store.open_original(stored.storage_key) as original:
        assert original.read() == fixture
    sections = extract_text_sections(fixture)
    assert [(item.text, item.locator.section) for item in sections] == [
        ("Synthetic first line\nsecond line", "Lines 1–2"),
        ("Another paragraph", "Line 4"),
    ]
    assert extract_text_isolated(fixture) == sections


@pytest.mark.parametrize(
    "bad", [b"", b"\xff", b"one\x00two", b" \n\n ", b"x" * 4001, b"a\n" * 10001]
)
def test_invalid_utf8_text_fails_before_review(bad: bytes) -> None:
    with pytest.raises(ExtractionError):
        extract_text_sections(bad)
    with pytest.raises(ExtractionError):
        extract_text_isolated(bad)


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
    store = PrivateOriginalStore(tmp_path / "private")
    with pytest.raises(IntakeError):
        store.store(uuid4(), BytesIO(data), filename=filename, claimed_media_type=media_type)
    assert not list((tmp_path / "private").rglob("*.pdf"))


def test_store_rejects_oversized_stream(tmp_path: Path) -> None:
    store = PrivateOriginalStore(tmp_path / "private")
    payload = b"%PDF-1.4\n" + b"x" * MAX_PDF_BYTES + b"%%EOF"
    with pytest.raises(IntakeError, match="size"):
        store.store(
            uuid4(), BytesIO(payload), filename="large.pdf", claimed_media_type="application/pdf"
        )


def test_store_rejects_oversized_text_stream(tmp_path: Path) -> None:
    store = PrivateOriginalStore(tmp_path / "private")
    with pytest.raises(IntakeError, match="size"):
        store.store(
            uuid4(), BytesIO(b"x" * (MAX_TEXT_BYTES + 1)),
            filename="large.txt", claimed_media_type="text/plain",
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
        PrivateOriginalStore(tmp_path / "public" / "uploads", public_root=tmp_path / "public")


@pytest.mark.parametrize("pages", [1, 3])
def test_pdf_extraction_preserves_nonempty_physical_pages(pages: int) -> None:
    fixture = self_authored_pdf(*(f"Synthetic page {number}" for number in range(1, pages + 1)))
    extracted = extract_pdf_pages(fixture)
    assert len(extracted) == pages
    assert [page.ordinal for page in extracted] == list(range(pages))
    assert [page.locator.page for page in extracted] == list(range(1, pages + 1))
    assert all(page.text for page in extracted)


@pytest.mark.parametrize("data", [b"not a PDF", b"%PDF-1.4\n%%EOF", b""])
def test_malformed_pdf_fails_without_partial_pages(data: bytes) -> None:
    with pytest.raises(ExtractionError):
        extract_pdf_pages(data)


def test_isolated_parser_returns_physical_pages_and_safe_failure() -> None:
    pages = extract_pdf_isolated(self_authored_pdf("Self authored page"))
    assert len(pages) == 1
    assert pages[0].locator.page == 1
    with pytest.raises(ExtractionError):
        extract_pdf_isolated(b"%PDF-1.4\n%%EOF")


def test_isolated_parser_timeout_is_bounded(monkeypatch: pytest.MonkeyPatch) -> None:
    def timed_out(*args: object, **kwargs: object) -> None:
        raise TimeoutExpired("parser", 0.01)

    monkeypatch.setattr("app.infrastructure.ingestion.isolated_pdf.subprocess.run", timed_out)
    with pytest.raises(ExtractionError, match="timed out"):
        extract_pdf_isolated(b"%PDF-1.4\n%%EOF", timeout_seconds=0.01)


def test_csv_cells_keep_header_key_and_physical_column_after_empty_cell() -> None:
    cells = extract_csv_cells("Название,Регион,Число\r\nТест,,7\r\n".encode())
    assert len(cells) == 1
    assert cells[0].text == "Название: Тест; Число: 7"
    assert cells[0].locator.page is None
    assert (cells[0].locator.table, cells[0].locator.row_start) == ("CSV", 2)
    assert (cells[0].locator.column_start, cells[0].locator.column_end) == (3, 3)


def test_csv_quoted_newline_is_one_record_and_preserves_next_row_number() -> None:
    cells = extract_csv_cells(b'key,note\r\nalpha,"first\r\nsecond"\r\nbeta,seven\r\n')
    assert [(cell.locator.row_start, cell.locator.column_start) for cell in cells] == [
        (2, 2), (3, 2)
    ]
    assert "first\r\nsecond" in cells[0].text


@pytest.mark.parametrize(
    "data",
    [b"key,value\n\xff,7", b"key,value\na", b"key,key\na,7", b"key,value\n,7"],
)
def test_csv_rejects_ambiguous_or_invalid_rows(data: bytes) -> None:
    with pytest.raises(ExtractionError):
        extract_csv_cells(data)


def test_csv_isolated_parser_and_private_original(tmp_path: Path) -> None:
    payload = b"key,count\r\nself-authored,7\r\n"
    store = PrivateOriginalStore(tmp_path / "private")
    saved = store.store(
        uuid4(), BytesIO(payload), filename="sample.csv", claimed_media_type="text/csv"
    )
    with store.open_original(saved.storage_key) as stream:
        assert stream.read() == payload
    cells = extract_csv_isolated(payload)
    assert len(cells) == 1
    assert cells[0].locator.row_start == 2
    assert cells[0].locator.column_start == 2


def test_csv_private_store_rejects_wrong_claimed_type(tmp_path: Path) -> None:
    store = PrivateOriginalStore(tmp_path / "private")
    with pytest.raises(IntakeError):
        store.store(
            uuid4(), BytesIO(b"key,value\na,7"),
            filename="a.csv", claimed_media_type="application/pdf"
        )


def test_xlsx_preserves_sheet_cell_and_merged_row_key(tmp_path: Path) -> None:
    payload = self_authored_xlsx()
    cells = extract_xlsx_cells(payload)
    assert [(cell.locator.sheet, cell.locator.row_start, cell.locator.column_start)
            for cell in cells] == [("North", 2, 3), ("North", 3, 2), ("South", 2, 2)]
    assert cells[1].text == "Item: Example A; Count: 7"
    assert all(cell.locator.page is None for cell in cells)
    assert extract_xlsx_isolated(payload) == cells
    store = PrivateOriginalStore(tmp_path / "private")
    saved = store.store(
        uuid4(), BytesIO(payload), filename="table.xlsx",
        claimed_media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    with store.open_original(saved.storage_key) as stream:
        assert stream.read() == payload


def test_xlsx_rejects_formula_and_ambiguous_merge() -> None:
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["Item", "Count"])
    sheet.append(["Example", "=2+2"])
    output = BytesIO()
    workbook.save(output)
    with pytest.raises(ExtractionError, match="formula"):
        extract_xlsx_cells(output.getvalue())
    sheet["B2"] = 4
    sheet.merge_cells("A1:B1")
    output = BytesIO()
    workbook.save(output)
    with pytest.raises(ExtractionError, match="merged"):
        extract_xlsx_cells(output.getvalue())


def test_xlsx_rejects_spoofed_zip_at_intake(tmp_path: Path) -> None:
    store = PrivateOriginalStore(tmp_path / "private")
    with pytest.raises(IntakeError, match="signature"):
        store.store(
            uuid4(), BytesIO(b"not an XLSX"), filename="table.xlsx",
            claimed_media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    with pytest.raises(ExtractionError):
        extract_xlsx_cells(b"PK\x03\x04broken")


def test_xlsx_rejects_archive_expansion_before_workbook_load() -> None:
    output = BytesIO()
    with ZipFile(output, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("xl/worksheets/sheet1.xml", b" " * (21 * 1024 * 1024))
    assert len(output.getvalue()) < 2 * 1024 * 1024
    with pytest.raises(ExtractionError, match="archive exceeds limits"):
        extract_xlsx_cells(output.getvalue())
