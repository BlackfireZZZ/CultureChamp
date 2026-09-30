# Corpus/backend integration handoff — 2026-09-30

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
  handoff is `9266ee6038bcd1c7fe2e977ae247753aa5d7081d`; its generated
  frontend schema sync was cherry-picked as `5bddcf7`.
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
  Candidate, revoked and unknown IDs all return 404. There is no original-file
  download route; `original_file` and `provider_transfer` remain distinct rights.
- `contracts/openapi.json` and the frontend generated schema match the above
  transport shapes. ADR 0003 documents durable queue and decision semantics;
  ADR 0004 records the pilot account/session implementation. The task tracker
  marks only C02/C03 done; incomplete format, rights and API gates remain partial.

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
- `PATH=/home/blackfire/.nvm/versions/node/v24.19.0/bin:$PATH CORPUS_TEST_DATABASE_URL=postgresql+asyncpg://culturechamp:culturechamp_local@localhost:15435/culturechamp make check`: passed after the final contract sync. Architecture, Ruff, mypy, 35 backend tests, frontend lint/build and 11 tests, ML Ruff/mypy and 6 tests, OpenAPI snapshot/client check, Compose config all passed. One Starlette/httpx deprecation warning remains.
- `PATH=/home/blackfire/.nvm/versions/node/v24.19.0/bin:$PATH npm run test:e2e` in `frontend/`: three Playwright tests passed at the specified responsive/keyboard paths.
- Isolated live Compose stack (`BACKEND_PORT=18035`, `FRONTEND_PORT=18080`, `POSTGRES_PORT=15435`) built and reached healthy backend, worker and frontend. Direct HTTP checks with an offline admin and a self-authored PDF observed: candidate invisible → worker `review_pending` with page 1 → admin approval → user list/detail visible → user/admin cross-role 403 → revoke → user list empty and detail 404. No supplied PDF was used in this approval.
- `git diff --check` and inspection of the final staged diff are required again
  immediately before the handoff commit; report the observed result there.

## What remains unverified and why

S01/S02/S04 and C01/C04/C05/C07/C08/C09/C10 remain partial as recorded in the
tracker. No table file exists, so table extraction, cell locators in user APIs and
table UI cannot be claimed. No real source has reuse, provider-transfer or
community-sensitive clearance; the three PDFs remain admin-only candidates.
Heading extraction and complete multicolumn reading order are unverified. The
ingress/proxy has no explicit request-body limit before multipart spooling, and
the PDF parser has no hardened process sandbox or CPU/memory ceiling. Admin
filters, passage-level exclusions, original-file authorization/download and
audited account role changes are absent. Provider policy remains disabled; real
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
cell-to-original locator through C06 before widening C07/C09. In parallel, add
admin inventory filters and an original-file endpoint that checks the current
exact-revision `original_file` scope, then test restricted/guessed/revoked IDs.
Keep all three supplied PDFs held until a named reviewer has documented rights,
sensitivity and extraction fidelity for an exact hash. Re-run `make check`, clean
migration and live role/revocation checks for any contract or schema change.

## Cleanup completed or retention reason

The isolated integration worktree and source branches are retained for follow-up
and review. The isolated Compose volumes are retained for repeatable tests; no
production database, source, provider or credential was touched.
