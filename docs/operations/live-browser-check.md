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
worker extraction, explicit approval, a Qdrant point, a cited chat answer,
chat switching/deletion, retry after a simulated 503 with the same request ID,
source focus, exact original bytes and withdrawal. With the explicit reset flag,
it also checks Qdrant collection loss and worker replay.
After withdrawal, the
historical answer stays visible but its citation becomes unavailable. A random
marker and cleanup make repeat runs independent. A clean run downloads the embedding model into the
private test volume once. The external model remains disabled.

Backend tests that call `ApprovedTextIndexer.index_one()` must use a separate
database and vector index with no ingest worker. The worker claims the same
queue and can otherwise consume the test revision first; the browser journey
intentionally keeps it running.

Stop the isolated stack with
`COMPOSE_PROJECT_NAME=culturechamp_livee2e docker compose down`. Removing its
three named test volumes is appropriate only when discarding this test project's
database, vector index and embedding cache intentionally.
