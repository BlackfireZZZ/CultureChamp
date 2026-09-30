# Access, model, and interface handoff — 2026-09-30

## Objective and actual status

S03 is recorded in ADR 0004 and reviewed against token leakage and cross-role
access scenarios. C02 has application authorization rules, an API session
dependency, and negative tests, but is **partial**: account/bootstrap/session
storage and production route wiring are absent. G01 has a deterministic fake,
bounded gateway and a disabled-by-default HTTP adapter with safe failures, but
is **partial** until shared quotas, provider policy approval and a real provider
contract exist. U01 has responsive wireframes; U03 has six editable starter
tasks and a help dialog. The frontend chat/materials/admin shell is explicitly
a deterministic preview. U02, U04 and U06 are not integrated or complete.

## Worktree / branch / base SHA

- Primary checkout: `/mnt/BlackfireZZZ/Hackatons/CultureChamp`, `main`.
- Base SHA: `f67a0586f55e4bf3aa5192628d95a0d0cb527096` (clean scaffold commit,
  confirmed with the corpus owner before worktree creation).
- Isolated checkout: `/mnt/BlackfireZZZ/Hackatons/CultureChamp-access-model-ui`,
  branch `agent/access-model-ui`. Initial status was clean. Managed worktree
  creation failed with “Git is unavailable”; `git worktree add` created this
  checkout from the agreed SHA. Retain for integration.

## Owner of changed files

This owner changed ADR 0004 for access/model data, UX_CHAT_MVP.md, new
`backend/app/application/access.py`, `backend/app/api/auth.py`, the new
`backend/app/infrastructure/model/` package and dedicated tests, frontend files,
and a dependency-only `backend/pyproject.toml` / `uv.lock` commit. The corpus
owner approved the dependency edit and cherry-picked it as `6127ba0`.

## Changed contracts and files

- [ADR 0004](../../decisions/0004-access-model-data.md): invite-only users, no
  guest chat, offline first-admin bootstrap, server session, role/owner/revision
  checks, 30-day active chat retention, separate source rights for provider
  transfer, backend-held key and pilot limits.
- [UX plan](../../product/UX_CHAT_MVP.md): default chat, secondary materials,
  admin inventory and citation navigation at 360/768/1280/1440 px, with
  keyboard and state paths. It uses the final S01 proposal and states that the
  candidate PDFs are not approved.
- Auth primitives and dependency: 401 for missing/expired/overlong sessions, 403
  for wrong role/CSRF, hidden foreign chat and unpublished revision decisions.
  These are not wired to a production store or source routes yet.
- Model package: fake response; input/output bounds; injected quota port;
  one retry within a deadline; HTTPS-only, disabled-by-default provider adapter;
  explicit per-request provider-transfer flag; streamed 1 MB response cap;
  sanitized error codes. No real model request was made.
- Frontend: deterministic data only from `src/api/demo.ts`; six editable
  use-case starters, help dialog, preview chat composer, empty approved materials
  and admin placeholder. No browser-side provider call or unpublished PDF data.

## Decisions and supporting evidence

The S03 ADR records OWASP authorization, session/CSRF, secrets, rate-limiting and
prompt-injection guidance. [HTTPX timeouts](https://www.python-httpx.org/advanced/timeouts/)
and [mock transports](https://www.python-httpx.org/advanced/transports/) informed
the adapter and deterministic tests. The [pypdf PyPI release](https://pypi.org/project/pypdf/6.19.0/)
supports the corpus owner's pinned runtime dependency. The corpus owner confirmed
that `user_text`, `original_file`, and `provider_transfer` are separate rights
scopes and that the user lookup filters exact approved revisions before ranking.

## Verification commands and observed results

- `uv run --package culturechamp-backend --extra dev pytest backend/tests/test_access.py backend/tests/test_model_adapter.py -q`: 7 focused tests passed after final model and access changes.
- `make backend-check`: Ruff and mypy passed; 8 backend tests passed, one
  Starlette/httpx deprecation warning.
- Node 24 `npm run lint`, `npm run test -- --run`, `npm run build`: passed; 4
  frontend component tests passed. System Node 18 is incompatible with the
  project. In this worktree, optional native bindings were installed locally
  after npm 9 omitted them; ignored `node_modules` was not committed.
- Node 24 `npm run test:e2e`: one Playwright test passed, checking 360/768/1280/1440
  widths, keyboard starter/send, mobile drawer Escape/focus, materials empty
  state and theme persistence.
- Node 24 `make check`: passed after the final review fixes. Architecture,
  backend (8 tests), frontend (4 tests and build), ML (1 test), OpenAPI and
  Compose gates were green. `git diff --check` passed.
- Read-only independent review found four issues. Streamed response size and
  mobile Escape/focus were fixed. Missing production session wiring and shared
  quotas remain explicit integration blockers.

## What remains unverified and why

- C02 cannot be called server-enforced in the running app: no account/session
  tables or store, login/logout/bootstrap, role management, protected source API,
  or production 401/403/404 tests exist. The current direct API tests use an
  isolated FastAPI app with a fake session store.
- G01 has a `Quota` protocol, not a shared durable limiter. Concurrency,
  per-user/global daily spend and exact input token accounting are unimplemented.
  Keep `policy_approved=False` until these and provider data terms are verified.
- No chat persistence, deletion purge, backup expiry, rights-approved source,
  external provider, citation API, or admin inventory API exists. U02/U04/U06
  remain open. The preview send is local-only and cannot substantiate an answer.
- Visual screenshots at 1280 and 360 px were inspected; tablet/wide widths were
  checked for overflow by Playwright, not manually reviewed for full visual
  polish. Full end-to-end user/admin flows need integrated APIs.

## Risks and open questions

The pilot's 30-day retention and numeric limits are unvalidated assumptions.
Appoint the first admin and source/rights reviewers before enabling ingestion or
provider transfer. Do not use PDF candidates for external generation. The HTTP
wire shape is OpenAI-compatible as a seam, not a selected provider contract.

## Exact next step

Integrate the corpus branch's revision/rights contract with a durable account and
session store plus login/logout/bootstrap, wire protected user/admin source routes,
and add direct API tests for guessed unpublished IDs and expired sessions in the
real app. Implement a shared quota reservation before changing the HTTP adapter's
policy gate. Then replace `src/api/demo.ts` with generated API clients and hooks,
keeping no-evidence behavior until a specific revision is approved.

## Cleanup completed or retention reason

The branch and worktree are retained for integration. No production service or
model call was started. The temporary Vite development server was stopped.
