# Fixture extraction and format matrix (S04 assessment)

## Check and limits

This is a direct check of the three unchanged PDFs listed in the
[fixture inventory](../../data/retrieval-fixtures/README.md), not a claim of
production ingestion support. `pdfinfo` and Poppler `pdftotext -layout` were run
on 2026-09-30. The smallest falsifying check was to compare page text and reading
order with the visible first page and a body page; page splits were also counted.
All pages return text. This does not establish complete transcription fidelity.

| Fixture | Observed extraction | Locator fidelity and risk | Format decision |
|---|---|---|---|
| PDF-01 (15 pages; 161,864 bytes) | All 15 pages have text; first page exposes title/author/DOI and print page 175. Prose and headings are legible. | Physical PDF page is available and the article starts at print page 175. Headers, footers, line breaks and hyphenation remain in text. Heading recognition is heuristic; verify sampled citations against render. | Text-layer PDF is a candidate for page-level ingestion; outside first cultural slice. |
| PDF-02 (10 pages; 502,017 bytes) | All 10 pages have text; first page exposes title, authors and DOI. Body prose is legible; references occupy later pages. | Physical page is stable; article starts at print page 217. Footnotes, line wrapping and bibliography can be confused with body text. Heading locators need manual comparison before approval. | Text-layer PDF is a candidate for page-level ingestion and human review. |
| PDF-03 (7 pages; 147,069 bytes) | All 7 pages have text; first page has parallel Russian/English title and abstract. Body pages are in two columns. | Physical page is stable; article starts at print page 103. Poppler `-layout` places left and right column text on the same lines. In the sampled page 2, `pypdf` 6.19.0 content-stream extraction yields left-column passages before a right-column passage. Full-document reading order and language segmentation remain unverified. | Page-level candidate extraction is possible; **do not** claim heading or user citation fidelity yet. |

The raw files remain candidate test material. Rights for processing, display and
model transmission are unresolved in the [source policy](SOURCE_POLICY.md).

| Format | Supplied fixture | Tested fidelity/locator | MVP stance |
|---|---|---|---|
| Text-layer PDF, single-column prose | PDF-01 and PDF-02 | Nonempty page text; page index survives; heading and footnote semantics incomplete | Implement only with explicit page locator and review flag. |
| Text-layer PDF, parallel/multicolumn | PDF-03 | Text exists; Poppler layout fails page 2 reading order, while sampled `pypdf` content order is better | Hold from user publication until full reading-order review. |
| Scanned/image-only PDF | None | No OCR or page-text test | Unsupported; reject or hold for separate OCR decision. |
| TXT/Markdown/DOCX/HTML | None | No fixture or fidelity test | Unsupported in this slice. |
| CSV/XLSX or embedded PDF table | None verified | No row/column, header or cell-locator test | **Table coverage unverified.** S04 acceptance remains open until a rights-cleared table fixture is supplied and inspected. |

## Reproduction

```bash
sha256sum data/retrieval-fixtures/raw/*.pdf
pdfinfo data/retrieval-fixtures/raw/51-88-1-SM.pdf
pdftotext -f 1 -l 2 -layout data/retrieval-fixtures/raw/51-88-1-SM.pdf -
```

Repeat `pdfinfo` and `pdftotext` for the other two inventory paths. For PDF-03,
compare page 2's left and right columns with extracted lines before designing a
paragraph locator. The next falsifying check is a real table fixture with merged
and empty cells and a row/cell-to-original comparison; no such file is supplied.
