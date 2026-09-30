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

## 2026-09-30 chat lifecycle browser verification

Objective and actual status: Confirm the remaining U02 chat UI paths using the
real built stack. The existing six starters and in-app guide already match
`docs/product/USE_CASES.md`: each fills an editable composer without sending,
and the guide opens before any chat exists. U03 is accepted. The live test now
checks chat switching, deletion, and a 503 retry that preserves the draft and
reuses the request ID. U02 is accepted; broader Q01 release scenarios remain.

Worktree / branch / base SHA: The same isolated integration worktree and
`agent/integration-backend` branch, clean at `b5e3914` before this slice. The
integration agent owns the browser test, tracker, runbook and this handoff.
No application code or API contract changed.

Decision and evidence: `USE_CASES.md` requires users to revisit conversations
and recover from interruptions without losing the brief. The browser check
uses a self-authored CSV, local Qdrant and the fake model. It injects one 503
at the chat message route, then observes the draft, retry ID and persisted
conversation before switching and deleting the earlier chat.

Verification: A fresh `culturechamp_chatjourney` Compose project on ports
15440/16337/18040/18085 built and became healthy. The first live run passed
one browser test in 38.5 seconds, including switching and deletion. The second
run passed one test in 5.8 seconds with the added 503 retry assertion. The
stack used only synthetic content and never contacted an external model API.
The full `make check` passed architecture, Ruff, mypy, 48 backend tests with
13 live-service skips, 16 frontend tests/build, 20 ML tests, OpenAPI/client
contract and Compose config. The previous slice ran all 61 backend tests
against isolated PostgreSQL and Qdrant.

Remaining limits: This proves client recovery and mechanical source access,
not answer quality, expert review, provider activation or use cases UC-01 and
UC-06–UC-11. The isolated stack was stopped after the final gate; its named
volumes are retained for repeatable local checks.

## 2026-09-30 withdrawn citation verification

Objective and actual status: A cited source can be withdrawn after an answer.
The live browser journey now reloads the historical conversation after
revocation and verifies that the answer stays visible, the original citation
button is disabled, and a withdrawal explanation appears. The materials list
still excludes the revision. G03 and U05 meet their synthetic acceptance checks;
this does not establish cultural support quality.

Worktree / branch / base SHA: The same isolated integration checkout on
`agent/integration-backend`, clean at `d170257` before this slice. The
integration agent owns the browser test, tracker and this handoff. No API or
database schema changed.

Verification: Reused the retained `culturechamp_chatjourney` volumes and
started all five Compose services healthy. `npm run test:e2e --
e2e/live.e2e.ts` passed one test in 9.6 seconds, including exact CSV row
navigation, original bytes and post-withdrawal citation behavior. The existing
PDF page component check and backend exact-revision checks provide the other
format and authority cases. The fake provider and self-authored CSV were used.

Recovery drill: The same browser journey deleted the isolated Qdrant text
collection while its synthetic CSV revision was approved. The worker recreated
the collection and point from PostgreSQL authority, and the next chat turn
again cited that revision. The first expanded run reached recovery but failed
on a strict Playwright selector because the chat now contained two supported
answers. After selecting both explicitly, the full live journey passed one
test in 6.8 seconds. Q03 is in progress: database/private-original restore,
monitoring and representative cost/latency evidence remain open.

Backup and restore drill: With the synthetic stack idle, `pg_dump -Fc` and a
private-source tar archive were taken. `pg_restore` into an independent
`culturechamp_restore` database completed without errors; original/restored
counts matched at 5 conversations, 7 turns, 5 revisions, 5 segments and
10 decisions. Alembic reported no new operations. Five restored CSV originals
matched both their SHA-256 content-addressed filenames and the restored
revision hashes. The procedure and its
production limits are recorded in `docs/operations/backup-restore.md` using
PostgreSQL and Qdrant primary documentation. This does not establish encrypted
remote backups, scheduling, retention enforcement or a full-stack replacement
RTO/RPO. The restored database and temporary archives are synthetic only.
The restored test database and temporary archives were removed after verification;
the Compose stack was stopped and its original named test volumes retained.
The destructive collection-loss check now requires an explicit
`LIVE_E2E_RESET_VECTOR=true` flag and a loopback Qdrant URL. With the flag,
the live journey passed in 11.6 seconds; without it, the ordinary live path
passed in 4.3 seconds. Frontend lint and TypeScript checks passed after this
guard was added. The final `make check` passed architecture, Ruff, mypy,
48 backend tests with 13 live-service skips, 16 frontend tests/build, 20 ML
tests, OpenAPI/client contract and Compose config. The live service paths were
observed in the browser runs and prior full 61-test database gate.

## 2026-09-30 curator description for approved materials

Objective and actual status: The materials catalogue required a concise
description. An administrator can capture an optional, 500-character,
curator-written description at intake; it is bound to the exact source
revision. Admin detail shows it during review. User list/detail expose it only
after the same revision is approved, and text search includes it. Existing
revisions retain a null description. A retry with the same source ID and byte
hash cannot overwrite the captured description. G04's persisted client and
browser checks now satisfy its stated acceptance; U04 remains in progress for
broader format and discovery coverage.

Worktree / branch / base SHA: The isolated integration worktree
`/mnt/BlackfireZZZ/Hackatons/CultureChamp-integration-backend`, branch
`agent/integration-backend`, was clean at `a56ac1c` before this slice. The
primary checkout and other authors' worktrees were untouched. The integration
agent owns the schema, migration, application/SQL gateway, API contract,
frontend, tests, ADR extension, tracker and this handoff.

Decision and evidence: `docs/product/USE_CASES.md` asks for a concise material
description. ADR 0003 treats captured revision metadata as immutable; the
description follows that rule and is not a model-generated claim. A null field
keeps pre-existing revisions valid. The list still uses metadata-only reads;
full segment bodies are fetched only in detail. RFC 9110 describes PUT as
resource replacement and RFC 5789 PATCH as partial modification, but this
slice adds no metadata edit endpoint. Correcting captured wording after a
duplicate retry would require an audited overlay under ADR 0003; that remains
open rather than silently mutating an approved revision.

Verification and integration: A new nullable-column migration upgraded a
clean PostgreSQL 17/PostGIS database to head; Alembic check found no drift.
The focused source API suite passed 3 tests on isolated PostgreSQL/Qdrant,
including preapproval invisibility, approved description/search and immutable
duplicate retry. Full `make check` with isolated services passed architecture,
Ruff, mypy, 61 backend tests, 16 frontend tests/build, 20 ML tests,
OpenAPI/generated-client checks and Compose config. Four mocked Playwright
tests passed at canonical widths; one live test was skipped. A separate clean
Compose stack ran the synthetic CSV browser journey with description upload
and approved user display; it passed one live test in 35.1 seconds. The model
was the deterministic fake. `make smoke` passed backend liveness/readiness
and frontend. All source files were self-authored fixtures.

Risks and next step: The description is a curator assertion, not a verified
source fact. Admins cannot yet correct tags or description after capture;
implementing that requires an audited overlay and concurrency policy. Large
catalogues still need pagination and measured latency. Both isolated stacks
were stopped after verification; their named volumes remain for repeat checks.
Review the diff, commit and push, then verify CI. Continue
independent admin/error and safety checks; source rights, expert review and
the exact external provider remain outside this technical slice.

Remaining limits: Expert factual review, a real provider, eligible cultural
rights, image/audio locators and broader UC-07–UC-11 adversarial cases remain
outside this synthetic citation check.

## 2026-09-30 private original during administrator review

Objective and actual status: Administrators can now open the stored original
for any exact revision, including a candidate before approval and a withdrawn
revision. The admin detail links to its protected route and displays origin,
creator, format and source identity alongside the extracted segments. The user
original route continues to require the exact current rights decision.

Worktree / branch / base SHA: The isolated integration worktree and
`agent/integration-backend` branch were clean at `793ed0a` before this slice.
The integration agent owns the application protocol, SQL adapter, HTTP route,
OpenAPI/client, admin UI, tests, ADR extension, runbook and tracker. The
primary checkout and other authors' work were untouched.

Falsifiable check and observed evidence: A self-authored CSV candidate returns
identical bytes from the admin original route before approval; a user receives
403 there and 404 from the user material route. After withdrawal, the admin
can still inspect the bytes while the user remains unable to do so. Stored
bytes are verified against the revision SHA-256 before serving; both original
routes use generated filenames, `nosniff` and `no-store`. The focused source
API suite passed 3 tests on isolated PostgreSQL/Qdrant. Full `make check`
passed architecture, 61 backend, 16 frontend and 20 ML tests, static checks,
contract generation and Compose config. A mocked keyboard admin browser path
passed. A fresh Compose stack passed the synthetic live browser journey in
33.2 seconds with candidate review, user denial and withdrawn audit access.

Risk and integration: This route is deliberately admin-only, including when
rights are unconfirmed; admin credentials remain a high-trust boundary. The
hash check detects mismatched private bytes. The broader U06 error, format and
keyboard review and real-source approval are still open. Review the diff,
commit and push, then verify CI. Stop both isolated test stacks after the
smoke check; retain their named volumes for repeat checks.

Review follow-up: The new origin link exposed a legacy-data risk because
intake had accepted arbitrary URL schemes. The application now accepts only
credential-free HTTP(S) origin URLs, and the admin view renders any existing
non-HTTP(S) origin as plain text. A forged intake URL returns 422; a legacy
`javascript:` value has no clickable link in the component check. This fix
is part of the same U06 integration work. The focused PostgreSQL source API
suite passed 3 tests, 17 frontend component tests passed, all four mocked
browser paths passed, and full `make check` passed again with 61 backend and
20 ML tests plus static, contract and Compose checks. The previous
admin-original commit passed GitHub CI before this follow-up.

## 2026-09-30 administrator inventory discovery

Objective and actual status: The administrator inventory can now filter
candidate and decided revisions by source title, description, creator or
origin URL, media type, exact revision tag kind/value, processing status and
latest decision. Filtering happens in PostgreSQL before ordering and the
100-row cap; the frontend sends a bounded search request and can reset it.
This is catalogue discovery, not the accepted Qdrant chat retrieval path.

Worktree / ownership: The same isolated worktree and
`agent/integration-backend` branch were clean at `58cf628` before this slice.
The integration agent owns the application filter contract, SQL, API,
OpenAPI/client, admin UI, tests, tracker and this handoff. Other authors'
checkouts were untouched.

Falsifiable check and observed evidence: An unapproved, self-authored PDF
fixture appears when source, PDF format and exact region tag match. The same
revision is absent with CSV format, another region or a literal percent query.
The focused PostgreSQL source API suite passed 3 tests. The frontend component
suite passed 17 tests, and four mocked Playwright paths passed, including
keyboard submission of the admin filters. The built Compose browser journey
found an unapproved synthetic CSV through source/format/region filters, then
completed approval, chat, citation, original access and withdrawal in 10.2
seconds using the fake model. Full `make check` passed architecture, 61
backend, 17 frontend, 20 ML, static, contract and Compose checks. `make smoke`
passed liveness, readiness and frontend checks. Diff review and CI remain to
be recorded for this slice.

Risk and next step: The API returns at most 100 newest matches; cursor
pagination and realistic-corpus query latency remain open. The inventory
filter is metadata-only and does not publish unpublished text to users.
Stop the test stacks, review the diff, commit/push and verify CI. U06 remains
in progress for PDF and error-state browser coverage.

## 2026-09-30 audited candidate metadata review

Objective and actual status: A reviewer can correct a review-pending revision's
description and tags after comparing its original and extracted segments.
Every captured or corrected snapshot appears in admin-only metadata history.
The user cannot see a candidate or its history. Approval locks further edits;
a stale metadata version returns 409. The source bytes, hash, segment IDs and
locators remain unchanged.

Worktree / branch / base SHA: The isolated integration worktree on
`agent/integration-backend` was clean at `dc8c715` before this slice. The
integration agent owns the migration, application/SQL gateway, API and
generated client, admin UI, tests, ADR and tracker. Other worktrees were not
changed. The falsifiable check was a successful preapproval amendment followed
by an identical citation and a rejected stale or postapproval amendment.

Evidence and verification: A new Alembic migration upgraded a clean PostgreSQL
database and passed `alembic check`. On an existing synthetic test database it
backfilled version 0 for all 38 revisions; a SQL comparison found zero
description/tag mismatches and retained 56 existing decision events. The
PostgreSQL source API suite passed 3 tests covering role denial, duplicate tags,
version conflict, audit history, duplicate upload and postapproval lock. The
frontend component suite passed 18 tests and the four mocked browser paths
passed. The built Compose browser journey amended a synthetic CSV before
approval, inspected version 1 history, and completed cited chat and revocation
in 9.3 seconds using the fake model. Full `make check` passed architecture,
61 backend, 18 frontend and 20 ML tests, static checks, generated contract
comparison and Compose config. `make smoke` passed liveness, readiness and
frontend checks. Diff review and CI remain to be recorded before integration.

Decision and risk: ADR 0003 now defines captured version 0 and an append-only
event for each correction. PostgreSQL locks processing and revision rows in the
same order as approval; a transaction updates the current catalogue projection
and event atomically. Only description and tags are editable in this pilot.
Postapproval corrections, expert validation of cultural context, and real-source
rights remain open. Review the diff, stop isolated stacks, commit/push and
verify CI.

## 2026-09-30 bounded XLSX table path

Objective and actual status: A self-authored XLSX workbook with two sheets,
an interior empty cell and a vertical merged row key retains exact sheet/row/
column locators from private intake through parser, PostgreSQL, Qdrant,
materials API and original-file download. Formula and ambiguous merged-cell
workbooks fail processing without publishing partial segments. Eligible real
workbooks, embedded PDF tables and cultural table semantics remain unverified.

Worktree / branch / base SHA: The isolated integration worktree on
`agent/integration-backend` was clean at `9f30327` before this slice. The
integration agent owns backend extraction and dependencies, frontend material
controls, OpenAPI contract, tests and format/ADR/tracker documentation. Other
worktrees remain untouched. The falsifying check was a data cell whose original
sheet/row/column or merged row label changed after approval, or a formula
appearing in user material.

Decision and comparable evidence: ADR 0003 records the strict workbook profile.
The official openpyxl guide explains formula load modes and merged anchor
behavior; Python ZIP documentation identifies decompression resource risk.
The parser preflights ZIP size and parts, then uses the existing resource-limited
child process. Unsupported rich workbook constructs fail closed. A first full
gate on a shared test database failed in an existing queue-order assertion
because earlier revoked fixtures were still present. A separate clean
PostgreSQL/Qdrant project upgraded to head and passed the 66-backend,
19-frontend and 20-ML full gate, static checks and generated API contract.
The focused XLSX API test also passed with preserved locators and exact bytes;
the formula fixture records failure with zero published segments. Four mocked
browser paths passed. A separate fresh built Compose stack passed liveness,
readiness and frontend smoke, then the full synthetic CSV browser journey in
33.4 seconds. The browser run checks the deployed runtime and prior path;
the XLSX-specific path is covered by the PostgreSQL/Qdrant API test. A direct
HTTP upload to the built worker also reached `review_pending`, retained the
three exact sheet/row/column coordinates and returned matching original bytes.
CI remains to be checked after the commit.

What remained at this handoff: Diff review, isolated-stack cleanup, commit,
push and CI verification. Commit `7c65921` passed GitHub CI.

## 2026-09-30 generation evidence boundary

Objective and actual status: Explicit assistant-control text in a retrieved
passage or catalogue metadata is withheld from model context. If screening
leaves no usable evidence, generation returns an insufficient-evidence answer
without a model call. A model fact matching only a numeric prefix of a cited
passage is rejected. Table evidence carries its complete locator into the
model payload. This is a narrow, reversible guard, not a proof that cultural
interpretations or creative output are safe or correct.

Worktree / branch / base SHA: The isolated integration worktree on
`agent/integration-backend` was clean at `7c65921` before this slice. The
integration agent owns the application service, screening helper, focused tests,
ADR 0007, tracker and handoff. Other worktrees remain untouched. The falsifying
checks were a model call containing a known explicit source instruction or an
accepted `Count: 7` fact from `Count: 70`/`Count: 7.0`.

Decision and comparable evidence: OWASP LLM01 and the BIPIA study support
separating external text from instructions, output validation and adversarial
tests while warning that these controls are incomplete. The first focused
generation run failed both newly added challenge cases (4 passed, 2 failed).
After the change the focused suite passed 11 tests, Ruff passed and mypy
passed 62 application modules. A clean PostgreSQL/Qdrant stack upgraded to
head and `make check` passed architecture, 73 backend, 19 frontend and 20 ML
tests, static checks, generated contract and Compose configuration. Four
mocked browser paths passed. A separate built Compose stack passed liveness,
readiness and frontend smoke; its synthetic CSV browser journey completed
chat, citation, original and revocation checks in 37.4 seconds. The screen
does not change stored source text or user materials and can reject legitimate
writing that quotes prompt-control phrases; an obfuscated attack can evade its
small pattern set. Provider-specific adversarial testing and qualified cultural
review remain open under G05/Q02.

Exact next step: Review the diff, stop the isolated test stacks, commit, push
and verify CI.

## 2026-09-30 model quota rejection fix

Commit `a8dc560` contains the evidence boundary above and was pushed. The
gateway then exposed a separate quota accounting error: an over-limit provider
response raised `provider_unavailable` but passed that result to `finish`, which
marked the reservation `done`. A focused regression test failed with the
observed `ModelResult` instead of `None`; after the fix all six adapter tests
passed. The gateway now passes only an accepted result to quota completion, so
the existing failed-reservation retry contract applies. This does not yet
measure provider charges for rejected responses.

`PATH=/home/blackfire/.nvm/versions/node/v24.19.0/bin:$PATH make check` passed
architecture, Ruff, mypy, 60 backend unit tests (14 service-dependent skips),
19 frontend tests, 20 ML tests, build, OpenAPI contract and Compose config. The
first invocation used system Node 18 and stopped at Vitest startup; the project
requires Node 24. Prior clean PostgreSQL/Qdrant, browser and built Compose gates
for `a8dc560` are recorded above. External model parameters and permissions
remain the release blockers; measured provider cost and latency remain open.
For this fix, a fresh isolated PostgreSQL container migrated from zero to head;
the real `SqlModelQuota` retry/limit test passed (1 test). That project's
container, network and volume were removed after the check.
