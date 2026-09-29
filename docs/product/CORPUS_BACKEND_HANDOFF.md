# Corpus and backend handoff — 2026-09-30

## Objective and actual status

The narrow Primorye corpus slice and source admission policy are proposed, not
approved. All three supplied PDFs remain admin-only candidate fixtures. S04 has a
tested PDF page matrix but is open because no table fixture exists and full reading
order/rights have not been reviewed. C01/C03 have a source/revision/locator schema,
domain rules, migration and repository adapter. C04 has bounded private PDF storage
and retry deduplication, but no authorized admin intake API. C05 has a page-text
adapter and tests for all three PDFs and malformed input; it has no background job,
error record or publication workflow. No task is marked done in the master plan.

## Worktree / branch / base SHA

- Primary checkout: `/mnt/BlackfireZZZ/Hackatons/CultureChamp`, `main`.
- Baseline scaffold and fixtures: `f67a0586f55e4bf3aa5192628d95a0d0cb527096`.
  Baseline `make check` passed and the commit was pushed to `origin/main`.
- Isolated checkout: `/mnt/BlackfireZZZ/Hackatons/CultureChamp-corpus-backend`,
  branch `agent/corpus-backend` from the baseline. Initial `git status` was clean.
  The managed worktree tool reported “Git is unavailable”, so `git worktree add`
  was used. The branch is retained for integration.

## Owner of changed files

This owner changed the new corpus documents in `docs/product/`, ADR 0003,
`backend/app/domain/sources.py`, `backend/app/infrastructure/db/`,
`backend/app/infrastructure/ingestion/`, the corresponding Alembic revision and
backend tests. The dependency-only `backend/pyproject.toml` / `uv.lock` commit came
from the “Access and interface” chat and was cherry-picked with its permission.
No frontend, auth, model API, `main.py`, OpenAPI or shared API contract was edited
here.

## Changed contracts and files

- [First slice](FIRST_CORPUS_SLICE.md): Primorye; two scholarly PDF candidates;
  three realistic text briefs. PDF-01 is an extraction control outside the slice.
- [Source policy](SOURCE_POLICY.md): provenance, credibility, separate rights
  scopes, sensitivity, fidelity, named approval, exact-revision revocation.
- [Format matrix](FORMAT_MATRIX.md): page counts and extraction limits for three
  PDFs; explicit absence of table/OCR/DOCX/CSV/XLSX coverage.
- [ADR 0003](../decisions/0003-source-revisions-and-locators.md): source UUID,
  immutable revision identity/hash, append-only decisions, typed page/table
  locators, fail-closed user eligibility.
- Domain and SQL adapter: revisions, tags, segments and decisions; a retry with
  the same source/hash returns the existing revision and captured metadata. A
  visible citation resolves only to the exact approved, sensitivity-cleared
  revision with user-text rights. Revocation removes it on the next lookup.
- Private storage uses a server-generated source/hash key, a 10 MiB cap,
  PDF extension/media claim/signature checks, 0700 directory and 0600 file modes,
  and atomic deduplication. The parser returns all physical PDF pages or an error.

## Decisions and supporting evidence

Publisher pages identify PDF-02 and PDF-03 but do not grant reuse. PDF-02 includes
an author copyright notice. Crossref's license metadata guidance distinguishes
version and text-mining rights. The Library of Congress sensitive-materials policy
is a comparable community-aware access pattern, not authority for these sources.
OWASP's File Upload Cheat Sheet informed type, size, filename and private-storage
checks. SQLAlchemy/Alembic documentation informed explicit constraints and
migration review. The ADR and policy link to these primary references.

## Verification commands and observed results

- Baseline `make check`: success before baseline commit.
- `sha256sum data/retrieval-fixtures/raw/*.pdf`, `pdfinfo`, Poppler
  `pdftotext -layout`, and `pypdf` 6.19.0 sample extraction: 15, 10 and 7
  text-bearing pages. PDF-03 Poppler layout mixes columns; sampled `pypdf`
  content order keeps the checked left-column passage before the right-column one.
- `CORPUS_TEST_DATABASE_URL=postgresql+asyncpg://culturechamp:culturechamp_local@localhost:15434/culturechamp uv run --package culturechamp-backend --extra dev pytest backend/tests/test_source_repository.py -q`:
  one PostgreSQL round-trip/revocation test passed.
- On an isolated fresh PostGIS 17 database, Alembic upgraded from empty to 0001
  and then to the source migration. `downgrade 0001_initial`, `upgrade head`, and
  `make migration-check` succeeded; check reported no new operations.
- `PATH=/home/blackfire/.nvm/versions/node/v24.19.0/bin:$PATH CORPUS_TEST_DATABASE_URL=postgresql+asyncpg://culturechamp:culturechamp_local@localhost:15434/culturechamp make check`:
  success after installing frontend dependencies with Node 24. Backend: 25 tests
  passed, Ruff and mypy passed. Frontend lint, Vitest and build passed. ML checks,
  OpenAPI contract check and Compose config passed. A first attempt with system
  Node 18 failed because an optional native binding was missing; `npm ci` with
  required Node 24 resolved it.
- `git diff --check`: no whitespace errors. The final clean-status and push SHA
  should be read from the branch at integration time.

## What remains unverified and why

- No rights holder permission, appointed cultural reviewer or user-visible source
  approval exists. The three PDFs must not be sent to an external model.
- No table fixture exists, so row/cell extraction and C06 remain unverified.
- Full text reading order, headings, hyphenation, footnotes and multilingual
  segmentation need visual review. Physical page locators work; heading locators
  are not extracted.
- C04 authorization depends on C02 session/admin API. No public upload route or
  storage volume wiring exists. File signature checks alone do not prove that a
  PDF is harmless; parser isolation, malware controls and error persistence are
  future work before untrusted admin uploads can be considered production-ready.
- C05 error recording/background processing depends on C07. The adapter is
  fail-closed in memory but does not persist a failed processing state.
- The schema has no database trigger forbidding privileged updates to immutable
  rows; the repository exposes insert/read paths only. A retention/deletion
  decision is needed before stronger database immutability enforcement.

## Risks and open questions

Appoint source/rights and community reviewers; identify an explicit reuse grant
for each candidate and each use scope; supply a rights-cleared table fixture;
decide admin storage configuration and parser isolation. Coordinate exact
visibility semantics with the “Access and interface” owner. Both chats agreed that
`user_text`, `original_file` and `provider_transfer` are separate scopes, and that
unknown/unapproved/revoked records are hidden from user lookup.

## Exact next step

Integrate C02's server-enforced admin identity with a new authorized intake use
case, then persist private-store output and parser success/error against one
revision. Before enabling any user retrieval, obtain a named review decision and
rights evidence for a specific PDF revision; add a real table fixture and repeat
S04/C06 checks. Run the PostgreSQL and full `make check` gates after integration.

## Cleanup completed or retention reason

The isolated worktree and branch remain for integration; they contain pushed,
reviewable work. The isolated Compose database can be stopped without removing
its named volume. The primary checkout is preserved for the other owner.
