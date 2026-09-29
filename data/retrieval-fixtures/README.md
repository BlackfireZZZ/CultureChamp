# Retrieval source fixtures

This directory holds the original PDF files supplied on 2026-09-30 for testing
document extraction and retrieval. The files in `raw/` are unchanged source bytes.
They are **candidate test material**, not an approved user-facing corpus. There is
no ingestion or retrieval pipeline connected to this directory yet.

## Inventory

| ID | Original file | Bibliographic details visible in the PDF | Pages | Bytes | SHA-256 |
|---|---|---|---:|---:|---|
| PDF-01 | [51-88-1-SM.pdf](raw/51-88-1-SM.pdf) | А. Л. Казин, “Русская культура как цивилизационный феномен: ценностный аспект”; *Russia & World: Scientific Dialogue*, No. 1(3), March 2022; DOI `10.53658/RW2022-2-1(3)-175-189` | 15 | 161864 | `61b78fe753a6ea347aed7ead60fd3e9d5309d0e1ea4f5150c5c3adc192ad8d85` |
| PDF-02 | [perspektivy-etnoekologicheskih-issledovaniy-kultury-korennyh-narodov-rossiyskogo-dalnego-vostoka.pdf](raw/perspektivy-etnoekologicheskih-issledovaniy-kultury-korennyh-narodov-rossiyskogo-dalnego-vostoka.pdf) | О. Н. Данилова and К. А. Карим, “Перспективы этноэкологических исследований культуры коренных народов российского Дальнего Востока”; DOI `10.24866/VVSU/2073-3984/2020-2/217-226` | 10 | 502017 | `ecadbe5afc98a88ade6715079c89363ee1bbc7b4a7889efd2c89ffb77394cf94` |
| PDF-03 | [problemy-traditsionnoy-kultury-korennyh-malochislennyh-narodov-yuga-dalnego-vostoka-rossii-i-roli-gosudarstva-v-etih-protsessah-xx-nachalo-xxi-veka.pdf](raw/problemy-traditsionnoy-kultury-korennyh-malochislennyh-narodov-yuga-dalnego-vostoka-rossii-i-roli-gosudarstva-v-etih-protsessah-xx-nachalo-xxi-veka.pdf) | Р. В. Гвоздев, “Проблемы традиционной культуры коренных малочисленных народов юга Дальнего Востока России и роли государства в этих процессах (XX–начало XXI века)”; DOI `10.19110/1994-5655-2024-6-103-109` | 7 | 147069 | `5df1eeb1f3a45937b986ade1f41f92a9f56aa4679d0ff9a6371883955f25393b` |

The titles, authors and DOIs above were transcribed from the first pages. They
have not been checked against publisher records. The PDF metadata for PDF-02
names a production file and `marina_p`; those fields are not treated as article
title or authorship.

## Use and review status

- All three PDFs contain extractable text (`pdftotext` returned nonempty output).
  This is a smoke check, not a fidelity or retrieval-quality assessment.
- PDF-03 has parallel Russian and English columns, so extraction order and page
  locators need checking before using it in citation tests.
- No spreadsheet or standalone table fixture is included. Format coverage and
  extraction fidelity remain open in [task S04](../../docs/exec-plans/active/creative-rag-mvp.md).
- Rights, source credibility, cultural sensitivity and approval for user-visible
  retrieval have **not** been reviewed. None of these files should be exposed as
  a verified source or sent to an external model until the source policy and
  per-document review are complete. PDF-01 contains an author's interpretation
  of culture and religion; attribute its claims to the author.

To verify the preserved bytes, run `sha256sum data/retrieval-fixtures/raw/*.pdf`
from the repository root and compare the results with the inventory above.
