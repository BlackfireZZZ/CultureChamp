# Access, model, UI, and evaluation handoff

## Objective and actual status

The pilot UI now uses the server's session API, approved-materials list and exact
revision detail API, plus a read-only admin revision inventory. The chat remains
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
  `4a9440f36be904747fdc563ae668dbdfc12684ef`.
- Frontend schema was generated from that exact OpenAPI snapshot. HTTP remains
  in `frontend/src/api`, server state in query hooks. The fixed frontend commits
  are `521a680`, `f02e812`, `238ce41`, and `1142cc5` in order.
- The integration agent owns backend and the canonical `contracts/openapi.json`.
  It has been sent the fixed frontend SHAs for cherry-pick and combined checks.

## Decisions and evidence

- Guest access is blocked by `GET /api/v1/auth/me`; users and admins receive
  different navigation. Login uses same-origin credentials, and logout sends the
  server CSRF token. Successful logout clears local draft/chat and admin/material
  query caches. The server remains the authorization authority.
- Materials are read from `/api/v1/materials` and exact revision pages from
  `/api/v1/materials/{revision_id}`. Candidate, revoked, and missing revisions
  are represented as an unavailable source in UI, with no fallback fixture.
- Admin inventory/detail uses `/api/v1/admin/sources` and
  `/api/v1/admin/revisions/{revision_id}`. It is labelled read-only. Approval
  remains a governed action outside this UI slice.
- R01's oracle run verifies the harness only. Its missing-relevant-source test
  fails as intended; it does not measure retrieval quality.

## Verification and observed results

From `frontend/`, with Node 24 at
`/home/blackfire/.nvm/versions/node/v24.19.0/bin` on `PATH`:

```text
npm run lint               -> passed (ESLint and TypeScript)
npm test -- --run          -> 11 tests passed
npm run test:e2e           -> 3 Playwright tests passed
npm run build              -> Vite production build passed after materials slice
```

Playwright exercised keyboard login, starter selection, exact-page selection and
focus, and overflow at 360, 768, 1280 and 1440 px. From the repository root:

```text
uv run --package culturechamp-ml --extra dev pytest ml/evals/test_retrieval_eval.py -q
                            -> 5 tests passed
```

The combined `make check` must run on the integration branch after cherry-pick.
This worktree retains the old backend contract, while its generated frontend
schema reflects the new integration snapshot. A contract check here would compare
different commits and therefore cannot validate the combined tree.

## Unverified risks and exact next step

The frontend tests mock HTTP responses; a browser-to-live-backend run and the
combined `make check` remain to be observed. The admin intake and approval
actions, persisted chat, source-cited generation, and expert review of qrels
remain open. The tabular evaluation item is explicitly synthetic because a
rights-cleared table fixture is unavailable.

Cherry-pick the four frontend commits on the integration branch after the four
`ml/evals/` commits, regenerate or check the OpenAPI client, run `make check` and
Playwright against the combined tree, then record the resulting fixed SHA. Keep
this worktree and branch until that integration is confirmed.
