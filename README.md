# CultureChamp

CultureChamp is a service for creating contemporary concepts and content using
verified cultural heritage sources from the peoples of Russia. A user starts with a
practical creative task; the service generates a useful result and, where relevant,
shows the cultural sources and context behind it.

The full product source of truth is [`docs/product/CONCEPT.md`](docs/product/CONCEPT.md).
Its MVP hypothesis and other assumptions still require validation. The previous
product implementation has not been copied. The engineering scaffold is runnable
and has no product domain tables or feature flows yet.

The [MVP task tracker](docs/exec-plans/active/creative-rag-mvp.md) records the
two-role chat and RAG delivery plan. The [use-case guide](docs/product/USE_CASES.md)
defines starter tasks and the expected source-navigation behavior.

## Stack

- Python 3.13, uv, FastAPI, SQLAlchemy, Alembic and PostgreSQL/PostGIS.
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
`http://localhost:8000/api/v1/health/live`. `make down` stops the stack.

## Architecture

- `backend/app/domain`, `application`, `infrastructure`, `api`: the modular monolith.
- `frontend/src/api`, `features`, `components/ui`: transport and UI boundaries.
- `contracts/openapi.json`: version-controlled API contract.
- `AGENTS.md`, `docs/agentic/`, `docs/architecture/` and `docs/decisions/`: working rules and decisions.
- `DESIGN.md`: the supplied visual contract for frontend work.
- `docs/exec-plans/`: planning and technical debt records.

Feature modules and MVP boundaries should be derived from `docs/product/CONCEPT.md`.
`DESIGN.md` supplies the visual baseline; its optional map and archive patterns do
not define the primary workflow. Existing ADRs are retained as engineering decisions,
not product requirements.
