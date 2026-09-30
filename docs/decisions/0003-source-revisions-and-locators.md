# ADR 0003: Source revisions, decisions and locators

Status: Implemented for PDF page text and synthetic CSV/XLSX cells in the pilot; real table fidelity and approval authority remain open.
Date: 2026-09-30

## Context and evidence

The [product concept](../product/CONCEPT.md) requires traceable cultural claims and
separation of facts, interpretation and creative output. The
[source policy](../product/SOURCE_POLICY.md) holds all supplied PDFs pending rights
and cultural review. The [format check](../product/FORMAT_MATRIX.md) found stable
physical PDF pages but unreliable column reading order in PDF-03, and no table
fixture. A citation cannot silently point to replacement bytes or an inferred
printed page number.

Comparable design inputs:

- [Crossref license metadata](https://www.crossref.org/documentation/schema-library/markup-guide-metadata-segments/license-information/)
  distinguishes licenses for the version of record, accepted manuscript and text
  mining. We likewise separate rights by allowed action instead of treating a DOI
  or access link as permission.
- [Library of Congress sensitive-materials policy](https://www.loc.gov/acq/devpol/materialsindigenouspeoplesaccess.pdf)
  distinguishes access, reproduction and community permission. It is a comparison
  for review process, not legal authority for this corpus.
- [SQLAlchemy constraints](https://docs.sqlalchemy.org/en/20/core/constraints.html)
  support explicit foreign keys, unique keys and checks; they can enforce locator
  shape and duplicate retry identity. [Alembic guidance](https://alembic.sqlalchemy.org/en/latest/autogenerate.html)
  requires migration review, so the migration is written and tested explicitly.
- [PostgreSQL 17 locking clauses](https://www.postgresql.org/docs/17/sql-select.html#SQL-FOR-UPDATE-SHARE)
  explicitly allow `SKIP LOCKED` for a queue-like table while warning that it is
  unsuitable for a general consistent read. Candidate processing uses that queue
  pattern, whereas user visibility reads the current decision normally.
- [OWASP file-upload guidance](https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html)
  recommends size/type checks and private storage outside the webroot. Those
  controls reduce exposure but do not establish that an arbitrary PDF is safe to
  parse. [Starlette's request-body limit](https://www.starlette.io/middleware/#requestbodylimitmiddleware)
  and [Caddy's request-body limit](https://caddyserver.com/docs/caddyfile/directives/request_body)
  bound multipart ingress; [Python resource limits](https://docs.python.org/3/library/resource.html)
  provide CPU, address-space and file-size ceilings to a separate parser process.

## Decision

1. `source_id` identifies a bibliographic/source record. `revision_id` identifies
   one immutable original byte sequence and its review snapshot. A retry with the
   same `source_id` and SHA-256 resolves to that revision without replacing its
   captured metadata; different bytes create a new revision. Store originals
   privately under a server-generated key.
2. Revision records include source attribution and contextual metadata as captured
   for that revision. Corrections require a new revision or an audited overlay; no
   routine update path rewrites the revision bytes, hash or extracted segment text.
   An optional curator-written description is captured with the revision and
   shown to users only after that exact revision is approved. It is catalogue
   context, not a verified source fact or an automatically generated summary.
   A duplicate upload with the same source ID and byte hash retains the first
   captured description. The preapproval audited overlay below records editorial
   corrections while preserving that captured snapshot as event version 0.
3. Tags are attached to a revision. A later revision can have different people,
   region, period or sensitivity tags without retroactively changing citations.
4. A segment has an ID, immutable `revision_id`, ordinal and source locator. A PDF
   locator uses **one-based physical page index**, optionally a heading/path and
   bounds. Printed page labels are display metadata only. A table locator reserves
   sheet/table and one-based row/column range, but no table extraction is claimed
   until a real fixture passes S04/C06.
5. Approval/revocation decisions are append-only events keyed to `revision_id`.
   Decisions for one revision serialize on its revision row, and the latest event
   is authoritative. Its rights scopes distinguish user text
   visibility, original-file access and external-provider transfer. Unknown rights
   default to false. A revocation event immediately fails closed at user retrieval
   and display, regardless of stale indexes. Reviewer ID, time, reason and evidence
   are mandatory for approval; the project owner still needs to appoint authority.
6. User-facing queries must apply current approval, revocation, sensitivity and
   rights before ranking or serialization. Unknown, held and revoked IDs have the
   same external lookup result. Admin queries are separately authorized.
7. PDF intake records a candidate processing row before extraction. A separate
   worker claims rows with a lease and `SKIP LOCKED`, writes all page segments in
   one transaction, then moves the exact revision to `review_pending`. A failed
   parse records a bounded error code and no visible segments. A retry reuses the
   same revision and original bytes; an attempt counter fences an expired worker
   from overwriting a newer attempt. The append-only decision stream remains the
   source of truth for visibility; processing state alone never publishes text.
8. An original-file response checks the latest exact decision for `user_text`,
   `original_file` and sensitivity clearance and verifies the stored bytes against
   the captured hash. A denied original has the same 404 as a missing revision.
   The response uses a server-generated UUID filename, the declared PDF type,
   `nosniff` and `no-store`; the user detail exposes `original_available` so a
   page link is offered only when the exact original is authorized. The
   [HTTP Content-Disposition standard](https://datatracker.ietf.org/doc/html/rfc6266)
   treats filenames as advisory, and the [Fetch specification's nosniff rule](https://fetch.spec.whatwg.org/#x-content-type-options-header)
   and [HTTP caching guidance](https://httpwg.org/specs/rfc9111.html#field.cache-control)
   inform the response headers. These headers are defense in depth; authorization
   remains the current database decision.
   Administrators can retrieve the hash-verified private original of a candidate
   or withdrawn revision through a separate admin-only route to compare it with
   extracted segments before making a decision. This review route never changes
   the user-facing rights check and uses the same generated filename, `nosniff`
   and `no-store` response rules.
9. The API rejects request bodies above the PDF limit plus bounded multipart
   overhead before parsing the multipart form. The proxy also caps bodies.
   The worker invokes the parser in a separate isolated Python process with a
   wall timeout and CPU/address-space/file-size limits, no inherited environment
   secrets, and no stderr returned to callers. Failure records a safe error code;
   the worker and candidate remain available for retry. This is process and
   resource isolation, not a hardened syscall or network sandbox. Untrusted bulk
   intake remains a separate deployment gate.

## CSV table extension (2026-09-30)

This extends decisions 4 and 7–9 above. The private original store accepts
`text/csv` with a `.csv` filename and a 2 MiB limit. The worker parses UTF-8 CSV
in a resource-limited child, stores each nonempty data cell as a `table` segment,
and records the one-based CSV record and column without inventing a PDF page or
XLSX sheet. Search text includes the original column header and first-column row
key. The API serves a permitted original as an attachment with its recorded media
type; page links continue to apply only to PDFs. Extraction failure remains held
and uses `source_extraction_failed` for both supported formats.

The accepted subset requires a comma delimiter, a unique nonempty header row,
two or more columns, a first-column key for nonempty data rows, regular row width,
and strict UTF-8 decoding. Quoted newlines count as one CSV record. Empty cells
retain their column positions and are not indexed. This avoids a heuristic header
or delimiter decision that could assign a cultural value to the wrong label.
The design follows [RFC 4180](https://datatracker.ietf.org/doc/html/rfc4180) and
Python's [CSV parser documentation](https://docs.python.org/3/library/csv.html).
The syntax is general, but cultural table semantics and retrieval effectiveness
still require a real eligible fixture and expert judgements. XLSX merged cells,
formulas and sheet locators remain unimplemented. The existing parser process
limits are resource isolation, not a syscall or network sandbox.

## Preapproval metadata amendment (2026-09-30)

Reviewers must be able to correct a candidate's description and contextual
tags after inspecting the extracted text and original. A duplicate upload with
the same bytes remains an idempotent retry; using it to change metadata would
silently replace the capture snapshot. Creating a second byte-identical source
revision for every editorial correction would also split one original across
multiple citation identities. We therefore use an audited projection:

- Intake and the migration from earlier revisions record version 0 in
  `source_metadata_events`. Each event stores a complete description/tag snapshot,
  reviewer identity, reason and time. Events are append-only.
- `source_revisions.description` and `source_tags` hold the current projection for
  catalogue search and governed vector filters. Their captured values remain
  recoverable from version 0; original bytes, content hash and extracted segments
  are never edited. A correction increments `metadata_version` and writes the
  new projection and event in one PostgreSQL transaction.
- Corrections are allowed only for `review_pending` revisions with no decision.
  The caller supplies the expected metadata version. The transaction locks the
  processing row and then the revision row, matching approval's lock order. A
  stale version or a concurrent approval fails with 409. Once approved or
  revoked, a new review process must be designed before metadata can change.
  The user never sees an unapproved correction.

[PostgreSQL 17 row locking](https://www.postgresql.org/docs/17/explicit-locking.html)
provides the serialization boundary for concurrent review and approval;
[SQLAlchemy's transaction guidance](https://docs.sqlalchemy.org/en/20/orm/session_transaction.html)
supports committing the projection and event atomically. This audit records
who changed catalogue context, but it does not by itself validate the cultural
accuracy of a tag or description. Source rights and sensitivity decisions still
require the appointed reviewer under S02.

## XLSX table extension (2026-09-30)

An exact workbook needs a sheet name as well as row and column to resolve a
table citation. We accept a bounded `.xlsx` OOXML ZIP and retain the original
bytes privately. Each visible worksheet has a unique nonempty header in row 1
and a first-column row key. Each nonempty data cell becomes one segment at its
one-based physical sheet, row and column. Empty cells keep their positions.
A vertical merge in column A starting below the header propagates its anchor
row key to the covered rows; other merged ranges are held as ambiguous. Formulas,
error cells, hidden sheets/rows/columns and chart sheets are held for review
rather than silently converting cached or invisible values into cultural facts.

The intake cap is 2 MiB. Before loading, the parser checks at most 200 ZIP
members and 20 MiB declared uncompressed bytes, and rejects encrypted,
external-link, macro, chart, drawing, media and pivot parts, along with duplicate
ZIP member names. Parsing runs in a separate CPU/memory/time-limited
process; the parent validates its bounded JSON output. The supported profile has
at most eight sheets, 2,000 rows, 50 columns and 10,000 nonempty data cells.
The same exact-revision approval, rights, original-file and revocation rules
apply as to CSV. No schema migration is needed because the locator already has a
sheet field. This is a technical format profile, not a claim that arbitrary
spreadsheets or real cultural tables are semantically correct.

The [openpyxl workbook guide](https://openpyxl.readthedocs.io/en/stable/tutorial.html)
documents sheet and cell access and notes that cached formula values and chart
features differ by load mode. Its [merged-cell behavior](https://openpyxl.readthedocs.io/en/stable/_modules/openpyxl/worksheet/worksheet.html)
keeps the value at the top-left anchor. Python's
[ZIP documentation](https://docs.python.org/3/library/zipfile.html#decompression-pitfalls)
warns that archives can exhaust resources. Those are the reasons for explicit
formula/merge decisions and a preflight ZIP expansion cap. A representative
eligible workbook and domain review are still needed to broaden this profile.

## Alternatives and tradeoffs

- A mutable `source.current_text` would be simpler, but would silently retarget
  old citations after replacement. Reject.
- A mutable `approved` boolean on the revision is cheap to query but loses the
  decision trail and risks reapproval on retry. Append-only decisions cost a
  latest-event lookup; index `revision_id, event_id` and measure when the corpus
  grows.
- Storing arbitrary locators only as JSON would allow new formats cheaply but
  cannot enforce page/range shape. Use typed fields for supported locators and
  extend through a migration after a tested fixture.
- Printed page numbers are familiar to readers but may be absent or inconsistent.
  Keep them as labels; physical page index is the machine anchor.

## Consequences and verification

The schema adds sources, immutable revisions, revision tags, segments and decision
events. Domain tests must show exact-revision locator identity and fail-closed
eligibility. A clean PostgreSQL migration, repository round trip and `alembic
check` are required before C03 can be marked complete. S04 remains open without a
table fixture and column-order validation; C04/C05 remain contingent on the access
and intake boundaries.
