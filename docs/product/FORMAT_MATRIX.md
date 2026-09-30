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

A normalized token-order audit of all 32 physical pages found that PDF-03 page 1
has 0.9932 unordered but only 0.8549 ordered agreement between `pypdf` and
Poppler default text on the `pypdf` side. This isolates a reading-order dispute,
not a loss of most words. Visual inspection confirms parallel Russian/English
front matter and shows that `pypdf` places page furniture before the title;
Poppler interleaves some parallel text. PDF-03 page 7 contains author and
citation metadata, which should be excluded from cultural evidence after review.
The audit reports parser agreement only; it cannot decide which parser is right
without a rendered-page comparison. Numeric per-page output is local and
contains no excerpts.

The raw files remain candidate test material. Rights for processing, display and
model transmission are unresolved in the [source policy](SOURCE_POLICY.md).

| Format | Supplied fixture | Tested fidelity/locator | MVP stance |
|---|---|---|---|
| Text-layer PDF, single-column prose | PDF-01 and PDF-02 | Nonempty page text; page index survives; heading and footnote semantics incomplete | Implement only with explicit page locator and review flag. |
| Text-layer PDF, parallel/multicolumn | PDF-03 | Text exists; Poppler layout fails page 2 reading order, while sampled `pypdf` content order is better | Hold from user publication until full reading-order review. |
| Scanned/image-only PDF | None | No OCR or page-text test | Unsupported; reject or hold for separate OCR decision. |
| TXT/Markdown/DOCX/HTML | None | No fixture or fidelity test | Unsupported in this slice. |
| UTF-8 comma CSV with a header row and first-column row keys | Self-authored synthetic table only | Empty interior cells retain their original one-based column; each nonempty data cell carries its column header and row key; clean-database API, original-file and Qdrant checks pass | Technical CSV path is implemented. Cultural table fidelity and retrieval quality remain unverified until an eligible real fixture is inspected. |
| XLSX or embedded PDF table | None verified | No merged-cell, formula, sheet or embedded-table locator test | Unsupported in this slice; C06 remains open. |

## Reproduction

The three PDFs are local-only personal copies at the inventory paths; a clean
checkout does not contain them. The commands below require those exact files
and the inventory SHA-256 checks. CI instead uses self-authored synthetic PDFs.

```bash
sha256sum data/retrieval-fixtures/raw/*.pdf
pdfinfo data/retrieval-fixtures/raw/51-88-1-SM.pdf
pdftotext -f 1 -l 2 -layout data/retrieval-fixtures/raw/51-88-1-SM.pdf -
uv run --package culturechamp-backend --extra dev python ml/evals/audit_pdf_extraction.py --output .private/reviews/pdf-extraction-agreement.json
```

Repeat `pdfinfo` and `pdftotext` for the other two inventory paths. For PDF-03,
compare page 2's left and right columns with extracted lines before designing a
paragraph locator. For CSV, compare the exact record/column in an eligible real
table with its extracted segment, including quoted newlines, empty cells and
headers. XLSX needs a separate merged-cell and sheet-locator fixture; none is
supplied. The CSV adapter follows [RFC 4180](https://datatracker.ietf.org/doc/html/rfc4180)
for commas, quotes and records and Python's [CSV parser](https://docs.python.org/3/library/csv.html)
in strict mode. It deliberately requires UTF-8 and a nonempty unique header row
with a first-column key; delimiter or header inference would make cell meaning
ambiguous. The isolated child process has the same bounded runtime pattern as PDF.
