# Corpus/backend integration handoff — 2026-09-30

## External model configuration checkpoint

The owner accepted the current retrieval study for MVP engineering progress and
requested no further retrieval ablations. This does not turn provisional
page-level labels into expert passage judgments. The existing E5-small text index
and its provisional threshold remain the runtime configuration; user-facing
cultural release still needs eligible reviewed sources. The next integration
slice is the server-side model path and a live synthetic browser journey.

The owner selected an external OpenAI-compatible API but has not supplied its
service, HTTPS Chat Completions URL, model ID or key. The backend now accepts
these as operator settings while defaulting to the deterministic fake provider.
External configuration fails startup unless the policy switch and required
settings are present. An external adapter sets the generation service's
`for_provider` search mode so only current `provider_transfer` revisions can be
ranked and sent. A live PostgreSQL/Qdrant test with a self-authored source lacking
that right returned insufficient evidence and made zero HTTP provider calls.
The exact setup boundary is in [the provider runbook](../../operations/model-provider.md).

Verification: `CORPUS_TEST_DATABASE_URL=postgresql+asyncpg://culturechamp:culturechamp_local@localhost:15436/culturechamp CORPUS_TEST_VECTOR_URL=http://localhost:16333 make check`
with Node 24 passed: 60 backend, 15 frontend and 20 ML tests, architecture,
Ruff, mypy, build, API contract and Compose config. No real source text or key
was used in provider tests. An isolated clean Compose build with its own ports
passed `make compose-check up smoke down`: backend liveness/readiness and frontend
smoke all passed. Actual provider compatibility and terms remain open.

## Latest extraction and source-boundary check

The retrieval extraction audit compared normalized token content and order for
all 32 physical pages of the three locally held PDFs. PDF-03 page 1 had 0.9932
unordered but 0.8549 ordered agreement between `pypdf` and Poppler on the
`pypdf` side. The rendered page confirms parallel Russian/English front matter;
page 7 is author/citation metadata. This parser disagreement and non-evidence
content are gates for passage review, not proof that either parser is correct.
The numeric report is Git-ignored at `.private/reviews/pdf-extraction-agreement.json`.

The three personally downloaded PDFs were found in the initial public Git
commit `f67a058`. Commit `dd6b24e` removed them from the tracked `main` tree;
the integration branch merged that change at `da50603`. Their local paths are
ignored, and the owner's copies remain on disk. Backend tests use self-authored
PDFs. A no-source full check passed: 46 backend tests with 13 service-dependent
skips, 15 frontend and 20 ML tests, plus static, build, contract and Compose
checks. Prior Git history and other remote branches still contain the files.
Repository-wide history remediation requires a separately reviewed coordinated
plan and is not claimed here.

The `da50603` CI run exposed an ML test-collection error: the extraction audit
imported the backend package before its functions were called, while the ML job
installs only ML dependencies. Moving that import into the audit command made
`make sync-ml ml-check` pass in the isolated ML environment (20 tests). The
audit remains run under the backend environment, as documented in the format
matrix. The `dd6b24e` CI Compose job failed because `scripts/smoke.sh` had Git
mode `100644`; the local checkout's executable mode had concealed that. Commit
`68ed9b5` corrected the mode on `main`, and the integration branch merged it
at `1304f65`. The same `make compose-check up smoke down` command had passed
locally on `dd6b24e`; the new remote CI run is the verification gate.

## Latest CSV integration evidence

Objective and status: C06 and C09 gained a synthetic UTF-8 CSV path with exact
record/column evidence, governed visibility, vector search and original access.
Real cultural tables, XLSX merged cells and expert retrieval labels remain open.
Worktree: `/mnt/BlackfireZZZ/Hackatons/CultureChamp-integration-backend`, branch
`agent/integration-backend`, base `f67a0586f55e4bf3aa5192628d95a0d0cb527096`;
the integration agent owns these changes. Before this slice the branch was clean
at `4af785554f4b154d43ec67173f6c79e88c5de074`.
Contracts changed: private original storage, worker extraction, source/original
API, OpenAPI snapshot/client, admin and materials UI, ADR 0003, format matrix and
active tracker. RFC 4180 and Python's CSV parser documentation support the
explicit delimiter/header choice; no delimiter inference is used.
Verification: a clean PostgreSQL upgrade through `b516391e8732` passed; the
live `test_csv_upload_to_vector_and_original_access` passed against PostgreSQL
and Qdrant, including immediate revocation. `PATH=/home/blackfire/.nvm/versions/node/v24.19.0/bin:$PATH
CORPUS_TEST_DATABASE_URL=postgresql+asyncpg://culturechamp:culturechamp_local@localhost:25436/culturechamp
CORPUS_TEST_VECTOR_URL=http://localhost:26336 make check` passed: 60 backend,
15 frontend and 17 ML tests, lint, mypy, build, contracts and Compose config.
`make migration-check` reported no new upgrade operations; `git diff --check`
passed. The previous vector-prefilter commit's [CI run](https://github.com/BlackfireZZZ/CultureChamp/actions/runs/36753793607)
also completed successfully. No real source entered user publication or a model
provider. Next: obtain the user's passage grades, then evaluate release gates;
compare an eligible real table against CSV cells and implement XLSX only with a
merged-cell fixture. The isolated test stack can be removed after verification.

Follow-up vector check: Qdrant's 64–256 point guidance exposed the previous
single-request limit for large CSV revisions. The adapter now embeds/upserts in
128-point batches and deletes in 256-point batches. A live 257-point test forced
a second-batch failure, then verified full replay and removal. A clean-stack
test also found that an empty approved corpus returned 503 when Qdrant had no
collection. Search now returns an empty evidence set in that case; it still
fails closed if any approved revision awaits indexing. The second clean-stack
`make check` passed 61 backend, 15 frontend and 17 ML tests plus static,
contract, build and Compose checks.

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
APIs. The admin UI can upload a PDF or narrow UTF-8 CSV candidate, inspect extracted segments and
errors, retry failed processing, explicitly grant rights on an exact revision,
and revoke it. Original-file and provider-transfer grants default to false.
Material detail preserves table cell locators in its API and UI instead of
coercing them to page 1. The synthetic CSV path has isolated extraction,
Qdrant indexing, exact cell lookup and authorized original download; a real
cultural table remains unverified.
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

S01/S02/S04 and C01/C05/C06/C07/C09 remain partial as recorded in the
tracker. A synthetic CSV has exact cell locators through the user API and table
UI, plus a permitted original download. Real cultural tables and XLSX/merged
cells remain unverified. No real source has reuse, provider-transfer or
community-sensitive clearance; the three PDFs remain admin-only candidates.
Heading extraction and complete multicolumn reading order are unverified. The
PDF and CSV parsers have bounded CPU/memory child processes and request-body
limits, but no hardened syscall/network sandbox. Admin tag-value filters,
passage-level exclusions and audited account role changes are absent. External
generation remains gated on retrieval review. The live Compose test used an
example.invalid rights URL only for self-authored synthetic bytes; it is not a
model for accepting evidence about a third-party source.

## Risks and open questions

Appoint a rights and cultural approval authority; obtain exact-version grants
for user excerpts and provider transmission separately. Verify full PDF-03
reading order and supply an eligible real table fixture before widening the
format gate. Harden parser isolation before untrusted bulk
uploads. The rate limiter is per username and can be abused to lock an account;
evaluate an IP/account policy with operators before broader availability.

## Exact next step

For the next backend slice, compare an eligible real table against CSV cell
locators and add XLSX merged-cell handling with a separate fixture. Harden the
parser sandbox before accepting untrusted bulk uploads.
Keep all three supplied PDFs held until a named reviewer has documented rights,
sensitivity and extraction fidelity for an exact hash. Re-run `make check`, clean
migration and live role/revocation checks for any contract or schema change.

## Cleanup completed or retention reason

The isolated integration worktree and source branches are retained for follow-up
and review. The isolated Compose volumes are retained for repeatable tests; no
production database, source, provider or credential was touched.

## 2026-09-30 live browser verification update

Objective and actual status: Add a reproducible, clean-stack browser check for the
two-role synthetic vertical path. The test passed once after correcting its
ambiguous heading selector. It does not establish cultural answer or external
provider quality.

Worktree / branch / base SHA: `/mnt/BlackfireZZZ/Hackatons/CultureChamp-integration-backend`,
`agent/integration-backend`, based on `d6804b7` for this slice. The initial
`git status --short --branch` was clean.

Owner of changed files: Integration agent owns `frontend/playwright.config.ts`,
`frontend/e2e/live.e2e.ts`, this handoff, the live-check runbook, README and the
task tracker. No concurrent writing agent contributed.

Changed contracts and files: `LIVE_E2E_BASE_URL` selects an existing built
frontend without starting Vite; the new Playwright test is opt-in through four
environment variables and uses only self-authored CSV bytes. The runbook records
an isolated Compose setup and first-admin bootstrap. No public API or schema
contract changed.

Decisions and supporting evidence: The existing `AdminView`, `MaterialsView`,
chat UI and source API contracts supplied selectors and expected states. A failed
rerun on a dirty stack showed that a previously approved synthetic table can
match another table-shaped query; a fresh stack and best-effort test revocation
remove that cross-run interference. This is a test-isolation finding, not a new
retrieval ablation or relevance claim.

Verification commands and observed results: `npm run lint` passed. `make up` on
`culturechamp_livee2e` started healthy db, vector, migrate, backend, ingest-worker
and frontend services from clean volumes. The first browser attempt reached cited
navigation but failed on a strict locator matching both list title and detail
heading; the locator was fixed. The final
`npm run test:e2e -- e2e/live.e2e.ts` with the four live environment variables
passed 1 test in 42.7 seconds, covering candidate isolation, no-evidence,
review, vector indexing, cited answer, exact CSV download and revocation.
`make check` passed architecture, Ruff, mypy, 53 backend tests (7 live-vector
tests skipped without a vector URL), 15 frontend tests/build, 20 ML tests,
contracts and Compose config. The ordinary `npm run test:e2e` passed four mocked
browser tests and skipped the live check. `make smoke` passed backend liveness,
readiness and frontend checks against the isolated stack. A first focused live
backend run had two failures because the running ingest worker claimed its test
indexing jobs. After stopping that worker, creating and migrating a separate
`culturechamp_tests` database and clearing the test Qdrant collection, the same
focused suite passed 11 tests. `make migration-check` on the separate database
reported no new upgrade operations.

What remains unverified and why: Exact external provider/model/terms/key are not
yet supplied. No eligible real cultural source has approved user/provider rights
or expert cultural support labels. Other use cases, canonical widths, failure
drills and recovery remain open in Q01–Q04.

Risks and open questions: The fake answer checks orchestration only. The live
test requires a running isolated stack and a one-time local embedding download;
normal Playwright runs skip it.

Exact next step: Inspect the diff, then commit and push this slice. Continue G05 and remaining
release gates without reopening the owner-accepted retrieval experiments.

Cleanup completed or retention reason: The isolated test stack was stopped after
verification; its named volumes were retained for another local run.

## 2026-09-30 generation output guard update

Objective and actual status: A model answer that cites an allowed segment while
inventing a different fact previously passed validation. A failing synthetic test
reproduced this. The generation service now accepts the `fact` field only when
its normalized text is a contiguous span of at least one cited excerpt. The
fake provider emits that span directly. This narrows the fact claim to text the
user can inspect; it does not validate interpretation or creative prose.

Worktree / branch / base SHA: The same isolated integration worktree and branch,
starting at `85316ab`; the worktree was clean before this slice. The integration
agent owns the changed generation service, fake provider, test, tracker and
handoff files. No schema or API contract changed.

Decision and evidence: [OWASP RAG Security](https://cheatsheetseries.owasp.org/cheatsheets/RAG_Security_Cheat_Sheet.html)
recommends treating retrieved content as untrusted and validating output. The
current JSON data boundary, bounded excerpts, separate system message and
current-authority citation lookup were already present. The new exact-span rule
addresses the observed case where a real citation ID alone gave an invented fact
an appearance of support. It can reject useful paraphrases; that is a deliberate
MVP restriction until an expert-reviewed support checker exists. A quoted source
span can still contain false or malicious source content, so source review remains
necessary.

Verification: `uv run --package culturechamp-backend --extra dev pytest
backend/tests/test_generation.py -q` first failed the new unsupported-fact case
(3 passed, 1 failed); after the fix, the generation and chat test selection
reported 4 passed and 1 integration test skipped without a live vector URL.
The full `make check` passed architecture, Ruff, mypy, 48 backend tests with
13 live-service skips, 15 frontend tests/build, 20 ML tests, OpenAPI contract
and Compose config. The isolated Compose stack rebuilt with the new fake
provider; `npm run test:e2e -- e2e/live.e2e.ts` passed 1 live test in 9.5
seconds using the existing test admin and cached embedding model.

Exact next step: Stop the isolated stack, inspect diff, then commit and push.
G05 stays
in progress pending adversarial provider and cultural support review.

## 2026-09-30 approved-material discovery update

Objective and actual status: The user materials schema exposed region, people
and period fields but always returned `null`, while the administrator could
store revision tags. Approved materials now expose their exact-revision tags,
populate those fields, and support server-side search and filters. The admin
upload form accepts newline-separated tags. One synthetic live browser path
proved a tagged CSV can be found by its region and excluded by another region.

Worktree / branch / base SHA: The same isolated integration worktree,
`agent/integration-backend`, clean at `42216a5` before this slice. The
integration agent owns the application source contract, SQL gateway, transport
contract, generated client, materials/admin UI, tests, tracker and handoff.

Changed contracts and files: `GET /api/v1/materials` adds optional `q`,
`region`, `people`, `period` and `media_type` query parameters. Existing calls
without filters retain their selection rule; returned materials add a `tags`
array and populated context fields. PostgreSQL
applies visibility before filtering. Text search escapes SQL wildcard characters,
and tag filters match exact values case-insensitively. The new fields were
regenerated in `contracts/openapi.json` and the TypeScript schema. No migration
or vector-index contract changed. The list loads revision metadata and tags in
two queries without fetching extracted segment bodies; exact detail still loads
the segments and current original-file permission.

Decision and evidence: `docs/product/USE_CASES.md` calls for materials filters,
context tags and original/locator detail. The existing `SourceTag` rows and
approval query are the authority. A candidate or revoked revision fails the
visibility predicate regardless of a matching filter. The first tag of each
context kind populates the legacy singular fields; the full array preserves
multiple values for future collections. Discovery still lacks a concise
description and pagination at corpus scale.

Verification commands and observed results: The focused source API suite with
`CORPUS_TEST_DATABASE_URL` on clean PostGIS port 15439 and
`CORPUS_TEST_VECTOR_URL` on Qdrant port 16336 passed 3 tests, including the new
tag, filter, literal wildcard and revocation assertions. `make check` against
those services passed all 61 backend tests, 16 frontend tests, 20 ML tests,
architecture, Ruff, mypy, OpenAPI/client contract, build and Compose config.
Ordinary `npm run test:e2e` passed four browser tests with the live test skipped.
The isolated built Compose stack passed `npm run test:e2e --
e2e/live.e2e.ts` (1 test, 8.3 seconds) with tagged admin upload and user
filtering. `make smoke` passed backend liveness/readiness and frontend; clean
PostGIS `make migration-check` reported no schema drift.
After changing the list to metadata-only reads, Ruff, mypy and the focused
three-test source API suite passed again against the isolated services. A second
full `make check` with the live PostgreSQL and Qdrant endpoints also passed
61 backend, 16 frontend and 20 ML tests plus all static and contract gates.

What remains unverified and why: The live source was self-authored CSV. No
eligible real source, rights review, expert cultural judgement or external model
API was involved. Large-corpus pagination and ranked materials discovery are
not implemented. The broader U04/U06/Q01 gates remain open.

Risks and open questions: The unfiltered material list is unbounded; the first
release needs a corpus-size and latency limit, then a paginated contract before
large institutional collections. Search uses title, creator and tag values, not
the extracted body. That preserves the current chat/vector retrieval boundary.

Exact next step: Stop the two isolated test stacks, inspect the diff, commit
and push the slice, then verify CI. Continue the remaining independent UI and
operations gates without reopening retrieval experiments.

Cleanup completed or retention reason: The isolated test stacks are stopped
after verification; their named volumes are retained for a repeat run.
