"""Self-authored PDF bytes for parser and storage tests."""

from io import BytesIO

from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject


def self_authored_pdf(*pages: str) -> bytes:
    writer = PdfWriter()
    for text in pages:
        if not text.isascii() or any(char in text for char in "()\\"):
            raise ValueError("synthetic PDF text must be simple ASCII")
        page = writer.add_blank_page(width=300, height=300)
        stream = DecodedStreamObject()
        stream.set_data(f"BT /F1 12 Tf 30 200 Td ({text}) Tj ET".encode("ascii"))
        page[NameObject("/Contents")] = writer._add_object(stream)
        font = DictionaryObject({
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        })
        page[NameObject("/Resources")] = DictionaryObject({
            NameObject("/Font"): DictionaryObject({NameObject("/F1"): writer._add_object(font)})
        })
    result = BytesIO()
    writer.write(result)
    return result.getvalue()
