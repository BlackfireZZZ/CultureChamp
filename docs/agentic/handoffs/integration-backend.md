# Corpus/backend integration handoff — 2026-09-30

## Current integration checkpoint (supersedes older status statements below)

The integration branch now has a Qdrant text vector index with locally generated,
snapshot-checked multilingual embeddings. PostgreSQL remains authoritative for
source revisions, current rights and citations; original bytes remain in private
file storage. ADR 0006 supersedes the PostgreSQL lexical retrieval decision in
ADR 0005. Chat retrieval no longer calls the lexical adapter. The ingestion
worker indexes approved text revisions and removes revoked points; every candidate
is rechecked against current PostgreSQL decisions before model context. This is
the text implementation of a modality-aware architecture, with image and audio
work retained in F02–F05 of the active tracker.

The same branch now has persisted, owned chat turns with retry IDs, citation
withdrawal checks, bounded fake model calls and a frontend connected to those
APIs. The admin UI can upload a PDF candidate, inspect extracted segments and
errors, retry failed processing, explicitly grant rights on an exact revision,
and revoke it. Original-file and provider-transfer grants default to false.
Material detail now preserves table cell locators in its API and UI instead of
coercing them to page 1; extraction and authorized serving of a real table
original remain open.
The three supplied PDFs have been used only in local retrieval diagnostics; no
provided cultural source has been approved for user answers or sent to a model
provider. User authorization covers this internal validation, not public use.

The new [retrieval quality plan](../../exec-plans/active/retrieval-quality.md)
and `ml/evals/run_retrieval_study.py` compare local extraction, chunking and
embedding candidates in disposable Qdrant collections. On eight provisional
page labels, E5-large FP16 with the existing 120-word windows reached
Recall@5/MRR@5/nDCG@5 of 1.00 and used about 1.14 GiB peak CUDA allocation;
larger token windows and layout-block candidates did not reliably improve the
page metric. This is not passage-level or held-out evidence. Every raw dense
configuration returned neighbors for unsupported queries. E5-large top scores
overlap between a supported and unsupported case, so no single cosine cutoff
works even on the provisional set. A map in PDF-02
showed why figure OCR must stay in a distinct, region-located representation;
local OCR had recognition errors. Runtime model and chunking remain provisional.

The worker now audits exact segment IDs and revision payloads for one approved
revision per idle cycle. A missing point invalidates its SQL completion marker,
causing chat search to return 503 until the worker replays that revision. A live
PostgreSQL/Qdrant deletion-and-replay test passed. This is eventual detection;
the [index runbook](../../operations/vector-index.md) records audit latency.
Search also obtains the exact approved, scoped revision IDs from PostgreSQL
before vector ranking and passes them through Qdrant's indexed UUID filter.
A live 120-held-point crowding test proves the allowed passage survives the
bounded candidate set; PostgreSQL still rechecks each returned segment.
The locally held 40-row passage packet at `.private/reviews/e5-large-review.csv`
awaits the user's 0–2 relevance and cultural-context judgments. It is excluded
from Git and user-facing source flows. The packet's non-review fields are locked
by SHA-256 digests in `ml/evals/review_packet_e5_large_fixed120.json`; the
offline evaluator rejects altered or incomplete packets and reports only
top-five judged-pool diagnostics. It cannot establish held-out recall.

A clean PostgreSQL database upgrade and Alembic check passed. With live
PostgreSQL and Qdrant, 51 backend tests passed. The complete `make check` passed
with Node 24: architecture, Ruff, mypy, 51 live-service backend tests,
15 frontend tests/lint/build, 17 ML tests, OpenAPI contract and
Compose config. Four mocked Playwright scenarios passed. The rebuilt Compose
stack reached healthy state and `BASE_URL=http://localhost:18036
FRONTEND_URL=http://localhost:18081 make smoke` passed. These verify synthetic
mechanics; an expert-labelled relevance set, rights-cleared real corpus, table
extractor, live browser journey and provider contract
remain open. The full acceptance state and implementation order live in
`docs/exec-plans/active/creative-rag-mvp.md`.

The sections below preserve the earlier corpus/access checkpoint and its
historical test results. Statements there that say chat or admin writes are
absent no longer describe the current branch.

## Objective and actual status

The corpus and access/UI branches are integrated in a separate worktree. The
server now has durable invite-only accounts and sessions, admin-only PDF intake,
private originals, a separate processing worker, admin revision review, exact
approval/revocation, and user materials list/detail filtered by the current
decision. The three supplied PDFs remain held candidate fixtures. A self-authored
synthetic PDF proved the complete server path in both a PostgreSQL-backed real-app
test and live Compose HTTP requests. No cultural PDF has been approved, served to
a user, or sent to a provider. The frontend now uses real auth, materials, and
read-only admin inventory APIs; chat remains an explicitly local preview.

## Worktree / branch / base SHA

- Primary checkout: `/mnt/BlackfireZZZ/Hackatons/CultureChamp`, `main` at
  `f67a0586f55e4bf3aa5192628d95a0d0cb527096` when integration started.
- Isolated checkout: `/mnt/BlackfireZZZ/Hackatons/CultureChamp-integration-backend`,
  branch `agent/integration-backend`, based on corpus
  `57756799530a4740df08b8822ffc2813cee9d44a`.
- Fixed access/UI parent: `6f6d87a7e3404515cf45ba93e4119b86dd1a5503`.
  Both parent commits are retained by merge commit
  `fc6e3f1abe77e86e810f2ca539f196bbbf0d00e9`. Later frontend/evaluation
  commits were cherry-picked with their originals retained on
  `agent/access-model-ui`. The last backend/OpenAPI contract commit before this
  handoff is `eb65525462ee6ff5ea78ee9f507e8828e0fa4574`; its generated
  frontend schema and original-link UI were cherry-picked from the access/UI
  branch. The integration branch retains both merge parents and the content of
  later cherry-picked commits; their original SHAs remain on the access/UI branch.
- Managed worktree creation returned “Git is unavailable”; a manual unique
  worktree was created instead. It must be retained for follow-up work. Initial
  primary and both source branch statuses were clean. Final status is recorded
  with the completion message and should be checked before more edits.

## Owner of changed files

The corpus/backend owner integrated the fixed commits, resolved the duplicate
`backend/pyproject.toml`/`uv.lock` dependency patch, assigned distinct ADR
numbers 0003 and 0004, and owns backend, migrations, OpenAPI, integration docs,
Compose wiring and this branch. The access/UI owner retained ownership of
`frontend/` and `ml/evals/`; their fixed frontend schema and feature commits
were cherry-picked without editing those files locally. The integration owner
added the evaluation test to the root `make check` target.

## Changed contracts and files

- `POST /api/v1/auth/login`, `GET /auth/me`, `POST /auth/logout`, and admin account
  creation use PostgreSQL accounts and hashed server sessions, Argon2id passwords,
  12-hour expiry, cookie rotation, Origin plus CSRF checks and role guards.
  The first admin is created by an offline CLI; public signup is absent.
- Admin `POST /api/v1/admin/sources` accepts one bounded PDF, immutable source
  metadata and optional `kind:value` tags. Retrying with the same source ID and
  bytes returns the same revision without rewriting metadata/tags. A separate
  worker records page segments or a safe failure code. Admin inventory/detail,
  approve, revoke and failed-processing retry are protected routes.
- User `GET /api/v1/materials` and `GET /materials/{revision_id}` expose only the
  currently approved, sensitivity-cleared exact revision with `user_text` rights.
  Candidate, revoked and unknown IDs all return 404. A later additive route,
  `GET /materials/{revision_id}/original`, returns exact hash-checked PDF bytes
  only when the latest decision also grants `original_file`; the detail's
  `original_available` flag guides page links. Revocation denies the original on
  the next request. `provider_transfer` remains a separate right.
- Admin inventory has optional processing-state and latest-decision filters plus
  a bounded limit. Omitted filters preserve the initial inventory response.
- `contracts/openapi.json` and the frontend generated schema match the above
  transport shapes. ADR 0003 documents durable queue and decision semantics;
  ADR 0004 records the pilot account/session implementation. The task tracker
  marks C02/C03/C04/C08/C10 done by their focused acceptance checks; incomplete
  format, rights and remaining API gates stay partial.

## Decisions and supporting evidence

- [PostgreSQL row-lock guidance](https://www.postgresql.org/docs/17/sql-select.html#SQL-FOR-UPDATE-SHARE)
  supports `SKIP LOCKED` for queue consumers but warns that it is unsuitable for
  consistent general reads. Processing uses a claim lease and attempt counter;
  user visibility reads the latest decision instead of a queue snapshot.
- [SQLAlchemy async guidance](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)
  informed separate sessions per request/worker transaction. API handlers now
  invoke application use cases through a protocol; SQL stays in the adapter.
- [OWASP upload guidance](https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html),
  [password storage](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html),
  [sessions](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html),
  and [CSRF](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html)
  informed private storage, Argon2id, cookie and CSRF boundaries. These checks
  do not establish a production upload sandbox or rights approval.
- The exact first corpus, rights holds, three-PDF extraction matrix and source
  hashes are in `docs/product/` and `data/retrieval-fixtures/`. No rights holder
  or qualified cultural reviewer has approved the supplied PDFs.

## Verification commands and observed results

- Fresh PostgreSQL database `culturechamp_verify_20260930` on the isolated
  PostGIS 17 Compose service: `DATABASE_URL=postgresql+asyncpg://culturechamp:culturechamp_local@localhost:15435/culturechamp_verify_20260930 uv run --package culturechamp-backend --extra dev alembic -c backend/alembic.ini upgrade head` ran `0001`, source, accounts and processing migrations from empty; `make migration-check` reported “No new upgrade operations detected.” A first offline admin was created there; a second bootstrap was rejected.
- `CORPUS_TEST_DATABASE_URL=postgresql+asyncpg://culturechamp:culturechamp_local@localhost:15435/culturechamp uv run --package culturechamp-backend --extra dev pytest backend/tests/test_identity_api.py backend/tests/test_source_api.py -q`: three tests passed. They cover real app/DB credentials, Argon2id and hashed cookie storage, rotation, throttle, CSRF, roles, expiry, spoofed input, duplicate upload/tags, failed extraction/retry, unpublished 404, exact approval and immediate revocation.
- The next focused `test_source_api.py` run passed after adding admin filters and
  an original-file rights test. It covered unpublished/original-denied 404,
  allowed exact bytes with `nosniff`/`no-store`, and revoked-original 404.
- `PATH=/home/blackfire/.nvm/versions/node/v24.19.0/bin:$PATH CORPUS_TEST_DATABASE_URL=postgresql+asyncpg://culturechamp:culturechamp_local@localhost:15435/culturechamp make check`: passed after the original-file contract sync. Architecture, Ruff, mypy, 35 backend tests, frontend lint/build and 12 tests, ML Ruff/mypy and 6 tests, OpenAPI snapshot/client check, Compose config all passed. One Starlette/httpx deprecation warning remains.
- `PATH=/home/blackfire/.nvm/versions/node/v24.19.0/bin:$PATH npm run test:e2e` in `frontend/`: four Playwright tests passed, including the keyboard admin filter and narrow-width path.
- Isolated live Compose stack (`BACKEND_PORT=18035`, `FRONTEND_PORT=18080`, `POSTGRES_PORT=15435`) built and reached healthy backend, worker and frontend. Direct HTTP checks with an offline admin and a self-authored PDF observed: candidate invisible → worker `review_pending` with page 1 → admin approval → user list/detail visible → user/admin cross-role 403 → revoke → user list empty and detail 404. No supplied PDF was used in this approval.
- After rebuilding the stack with the additive original-file route, direct HTTP
  checks observed candidate original 404, worker extraction and reviewed tag,
  exact approval with `original_file=true`, original bytes matching the upload,
  `no-store`/`nosniff`, admin filters, then revoked-original 404. The test PDF
  was again self-authored; supplied fixtures remained held.
- `git diff --check` and inspection of the final staged diff are required again
  immediately before the handoff commit; report the observed result there.

## What remains unverified and why

S01/S02/S04 and C01/C05/C07/C09 remain partial as recorded in the
tracker. No table file exists, so table extraction, cell locators in user APIs and
table UI cannot be claimed. No real source has reuse, provider-transfer or
community-sensitive clearance; the three PDFs remain admin-only candidates.
Heading extraction and complete multicolumn reading order are unverified. The
  ingress/proxy has no explicit request-body limit before multipart spooling, and
the PDF parser has no hardened process sandbox or CPU/memory ceiling. Admin
  tag-value filters, passage-level exclusions and audited account role changes
  are absent. Provider policy remains disabled; real
generation and chat persistence are absent. The live Compose test used an
example.invalid rights URL only for self-authored synthetic bytes; it is not a
model for accepting evidence about a third-party source.

## Risks and open questions

Appoint a rights and cultural approval authority; obtain exact-version grants
for user excerpts and provider transmission separately. Verify full PDF-03
reading order and supply a rights-cleared table fixture before widening the
format gate. Set proxy body limits and parser isolation before untrusted bulk
uploads. The rate limiter is per username and can be abused to lock an account;
evaluate an IP/account policy with operators before broader availability.

## Exact next step

For the next backend slice, add a rights-cleared real table fixture and prove a
cell-to-original locator through C06 before widening C07/C09. Add a constrained
parser process and request-body ingress limit before accepting untrusted bulk
uploads; then test process termination, retry and candidate isolation.
Keep all three supplied PDFs held until a named reviewer has documented rights,
sensitivity and extraction fidelity for an exact hash. Re-run `make check`, clean
migration and live role/revocation checks for any contract or schema change.

## Cleanup completed or retention reason

The isolated integration worktree and source branches are retained for follow-up
and review. The isolated Compose volumes are retained for repeatable tests; no
production database, source, provider or credential was touched.
