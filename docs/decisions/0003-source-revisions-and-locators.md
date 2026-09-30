# ADR 0003: Source revisions, decisions and locators

Status: Implemented for PDF page text in the pilot; table extraction and approval authority remain open.
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
  parse; parser isolation and resource ceilings remain release work.

## Decision

1. `source_id` identifies a bibliographic/source record. `revision_id` identifies
   one immutable original byte sequence and its review snapshot. A retry with the
   same `source_id` and SHA-256 resolves to that revision without replacing its
   captured metadata; different bytes create a new revision. Store originals
   privately under a server-generated key.
2. Revision records include source attribution and contextual metadata as captured
   for that revision. Corrections require a new revision or an audited overlay; no
   routine update path rewrites the revision bytes, hash or extracted segment text.
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
