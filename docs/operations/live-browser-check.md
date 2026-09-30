# Live browser check with a synthetic source

This check exercises the built frontend, backend, worker, PostgreSQL and Qdrant
on a separate Compose project. It creates a self-authored CSV and test accounts;
it does not use the held cultural PDFs or contact a model provider. The default
fake model proves application wiring and citation navigation, not answer quality.

Use Node 24 and an installed Playwright Chromium. From the repository root:

```bash
COMPOSE_PROJECT_NAME=culturechamp_livee2e POSTGRES_PORT=15438 VECTOR_PORT=16335 \
  BACKEND_PORT=18038 FRONTEND_PORT=18083 \
  BACKEND_CORS_ORIGINS='["http://127.0.0.1:18083"]' make up
COMPOSE_PROJECT_NAME=culturechamp_livee2e docker compose exec -T backend \
  /workspace/.venv/bin/python -m app.infrastructure.db.bootstrap_admin e2e-admin
```

Enter a new local test password at the prompt. Do not use a real credential.
Then run from `frontend/`:

```bash
LIVE_E2E_BASE_URL=http://127.0.0.1:18083 \
  LIVE_E2E_VECTOR_URL=http://127.0.0.1:16335 \
  LIVE_E2E_ADMIN_USER=e2e-admin LIVE_E2E_ADMIN_PASSWORD='<test password>' \
  npm run test:e2e -- e2e/live.e2e.ts
```

To add the destructive Qdrant collection-loss/replay drill, set
`LIVE_E2E_RESET_VECTOR=true` on the test command. It is permitted only with a
loopback vector URL and must point at a separate test Compose project.

The browser test requires all four variables and is skipped in the ordinary
mocked Playwright run. It checks candidate invisibility, a no-evidence response,
worker extraction, admin-only review of the original before approval, explicit
approval, a Qdrant point, a cited chat answer, chat switching/deletion, retry
after a simulated 503 with the same request ID,
source focus, exact original bytes and withdrawal. With the explicit reset flag,
it also checks Qdrant collection loss and worker replay. After withdrawal, the
historical answer stays visible but its citation becomes unavailable. The
administrator can still inspect the withdrawn original for audit, while the
user cannot retrieve it through either original route. A random marker isolates
new test records, but the no-evidence step requires an empty approved corpus;
the test checks this precondition. A clean run downloads the embedding
model into the private test volume once. The external model remains disabled.
The same journey uploads a self-authored malformed PDF after the approved-source
flow. It checks the failed extraction in the administrator view, retry from that
view, the repeated failure and continued user denial. A previously interrupted
run can leave approved synthetic sources in its test database and affect the
no-evidence assertion. For a fresh run, reset only the disposable isolated
Compose project; if offline, seed its private volume with the pinned model cache
before starting the worker.
It then uploads the self-authored two-sheet XLSX fixture, approves its exact
revision, checks physical sheet/row/column locators and a Qdrant point, filters
the user materials list to XLSX, downloads identical original bytes, and opens
a cited workbook cell from a new chat. Revocation makes the historical citation
unavailable. Opening a previously viewed source through a citation also checks
that keyboard focus returns to the cited cell after cached data refreshes.
The journey also uploads a self-authored two-page text-layer PDF. It checks
candidate isolation, both physical page locators, an indexed page-two segment,
a page-two chat citation and original link, byte-identical user access to the
approved PDF, and denial of the original after revocation.
The same run checks the admin review, cited chat and source detail for document
overflow at 360, 768, 1280 and 1440 px; it is a layout check on synthetic
content, not a target-user usability review.

Backend tests that call `ApprovedTextIndexer.index_one()` must use a separate
database and vector index with no ingest worker. The worker claims the same
queue and can otherwise consume the test revision first; the browser journey
intentionally keeps it running.

Stop the isolated stack with
`COMPOSE_PROJECT_NAME=culturechamp_livee2e docker compose down`. Removing its
three named test volumes is appropriate only when discarding this test project's
database, vector index and embedding cache intentionally.
