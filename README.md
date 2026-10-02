# Лад

Лад is a service for creating contemporary concepts and content using
verified cultural heritage sources from the peoples of Russia. A user starts with a
practical creative task; the service generates a useful result and, where relevant,
shows the cultural sources and context behind it.

The full product source of truth is [`docs/product/CONCEPT.md`](docs/product/CONCEPT.md).
Its MVP hypothesis and other assumptions still require validation. The integrated
branch contains the governed-source backend and a text chat implementation in
progress; it is not a released cultural product.

The [delivery tracker](docs/exec-plans/active/creative-rag-mvp.md) records the
first text release and full-concept backlog. The [use-case guide](docs/product/USE_CASES.md)
defines starter tasks and the expected source-navigation behavior.

## Stack

- Python 3.13, uv, FastAPI, SQLAlchemy, Alembic, PostgreSQL/PostGIS, Qdrant
  and local multilingual text embeddings.
- React 19, TypeScript, Vite, Tailwind CSS and TanStack Query.
- Docker Compose for local integration and Caddy for the built frontend.
- An isolated `ml/` workspace for future offline experiments.

## Run locally

Use Node 24 and a working Docker daemon:

```bash
make bootstrap
make check
make up
make smoke
```

The frontend is at `http://localhost:8080`; the API is at
`http://localhost:8000/api/v1/health/live`. The local Qdrant endpoint is bound
to `127.0.0.1:6333`. The first published text revision triggers a one-time
download of the configured embedding model into the private Compose volume.
`make down` stops the stack.

## Architecture

- `backend/app/domain`, `application`, `infrastructure`, `api`: the modular monolith.
- `frontend/src/api`, `features`, `components/ui`: transport and UI boundaries.
- `contracts/openapi.json`: version-controlled API contract.
- `AGENTS.md`, `docs/agentic/`, `docs/architecture/` and `docs/decisions/`: working rules and decisions.
- `DESIGN.md`: the supplied visual contract for frontend work.
- `docs/exec-plans/`: planning and technical debt records.

The [model provider runbook](docs/operations/model-provider.md) records the
backend-only settings for a future OpenAI-compatible text API. The default
provider is the deterministic fake until an exact service, model and data policy
are configured.

The [live browser check](docs/operations/live-browser-check.md) runs the full
two-role workflow on an isolated Compose stack with a self-authored CSV. The
bounded XLSX path has a separate self-authored two-sheet integration fixture;
neither fixture is cultural evidence.

Feature modules and MVP boundaries should be derived from `docs/product/CONCEPT.md`.
`DESIGN.md` supplies the visual baseline; its optional map and archive patterns do
not define the primary workflow. Existing ADRs are retained as engineering decisions,
not product requirements.
