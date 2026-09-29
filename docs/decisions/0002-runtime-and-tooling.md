# ADR 0002: Runtime and tooling baseline

## Status

Accepted for the runnable application scaffold. Revisit individual components when
the product workflow gives a concrete reason to change them.

## Decision

Use Python 3.13 with uv, FastAPI, SQLAlchemy/Alembic and PostgreSQL for backend;
Node 24, React, TypeScript and Vite for frontend; Docker Compose for reproducible
local integration. Pin lock files and run lint, types, tests, contracts and clean
migrations in CI.

## Consequences

When implemented, local environments must match `.python-version` and
`.node-version`. Generated OpenAPI types are checked for drift. A change to the
confirmed runtime baseline requires a new ADR.
