# Access, model, UI, and evaluation handoff

## Objective and actual status

The pilot UI now uses the server's session API, approved-materials list and exact
revision detail API, plus a read-only, filterable admin revision inventory. An
original PDF link is offered only when the exact approved revision has the
separate original-file right. The chat remains
an explicitly labelled local preview because no chat or generation API is in the
agreed OpenAPI snapshot. U02, U04, U05, U06 and R01 are not complete.

S05 has eight provisional, page-located cases and a reviewer rubric in
[`ml/evals/README.md`](../ml/evals/README.md). No case has expert-confirmed
ground truth; the candidate PDFs have unknown user-corpus rights.

## Worktree, ownership, and changed contracts

- Primary repository: `/mnt/BlackfireZZZ/Hackatons/CultureChamp`.
- Worktree: `/mnt/BlackfireZZZ/Hackatons/CultureChamp-access-model-ui`.
- Branch: `agent/access-model-ui`; base: `f67a0586` (the shared scaffold).
- Owner of writes: this agent, limited to `frontend/` and `ml/evals/`.
- Integration contract snapshot: `agent/integration-backend` at
  `eb65525462ee6ff5ea78ee9f507e8828e0fa4574`.
- Frontend schema was generated from that exact OpenAPI snapshot. HTTP remains
  in `frontend/src/api`, server state in query hooks. The fixed frontend commits
  include `521a680`, `f02e812`, `238ce41`, `1142cc5`, `6030715`,
  `c9138db`, `7c31ce6`, `8b18907`, `25a3ebd`, and `ceb8bb7` in order.
- The integration agent owns backend and the canonical `contracts/openapi.json`.
  It has been sent the fixed frontend SHAs for cherry-pick and combined checks.

## Decisions and evidence

- Guest access is blocked by `GET /api/v1/auth/me`; users and admins receive
  different navigation. Login uses same-origin credentials, and logout sends the
  server CSRF token. Successful logout clears local draft/chat and admin/material
  query caches. The server remains the authorization authority.
- Materials are read from `/api/v1/materials` and exact revision pages from
  `/api/v1/materials/{revision_id}`. A page link targets that same revision's
  `/original#page=N` endpoint only when `original_available` is true; otherwise
  the page locator and text remain visible without an external-origin link.
  Candidate, revoked, and missing revisions are unavailable, with no fallback
  fixture.
- Admin inventory/detail uses `/api/v1/admin/sources` and
  `/api/v1/admin/revisions/{revision_id}`. Status/decision filters are server
  queries, the 100-result limit is stated, and reviewed tags are shown. It is
  labelled read-only. Approval remains a governed action outside this UI slice.
- R01's oracle run verifies the harness only. Its missing-relevant-source test
  fails as intended; it does not measure retrieval quality.

## Verification and observed results

From `frontend/`, with Node 24 at
`/home/blackfire/.nvm/versions/node/v24.19.0/bin` on `PATH`:

```text
npm run lint               -> passed (ESLint and TypeScript)
npm test -- --run          -> 12 tests passed
npm run test:e2e           -> 4 Playwright tests passed
npm run build              -> Vite production build passed after original-link slice
```

Playwright exercised keyboard login, starter selection, exact-page selection and
focus, admin filters, and overflow at 360, 768, 1280 and 1440 px. From the
repository root:

```text
uv run --package culturechamp-ml --extra dev pytest ml/evals/test_retrieval_eval.py -q
                            -> 5 tests passed
```

On the combined integration branch at `c73762188c6e5567e13b0d34201651c0bd9d108b`
(which includes frontend through `25a3ebd`), with Node 24 on `PATH`:

```text
make check                 -> passed: architecture; backend Ruff/mypy;
                              backend pytest 31 passed, 4 skipped (PostgreSQL
                              dependent); frontend lint, 12 tests, build;
                              ML Ruff/mypy, 6 tests; OpenAPI snapshot and
                              generated schema checks; Compose config
cd frontend && npm run test:e2e
                           -> 4 Playwright tests passed
```

The integration agent separately observed the real PostgreSQL candidate to
approval to user-visibility to revocation path, a user-to-admin 403 response,
exact original PDF bytes only with the extra right, 404 before approval and
after revocation, and clean-database migrations. This agent did not repeat
those live checks.
This worktree retains the old backend contract, while its generated frontend
schema reflects the integration snapshot. A contract check here would compare
different commits rather than validate a combined tree.

## Unverified risks and exact next step

The frontend browser tests mock HTTP responses; a browser-to-live-backend UI run
remains to be observed. The admin intake and approval
actions, persisted chat, source-cited generation, and expert review of qrels
remain open. The tabular evaluation item is explicitly synthetic because a
rights-cleared table fixture is unavailable.

Cherry-pick the cap-label and this handoff commit, run the combined gate once
more, and record a final fixed integration SHA. For product progress,
implement the backend chat and citation API before replacing the labelled local
preview; obtain expert qrels, a rights-cleared table fixture and a measured
retrieval run before claiming R01. Keep this worktree and branch until the
integration handoff is acknowledged.
