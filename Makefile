SHELL := /bin/sh

.PHONY: bootstrap sync-backend sync-ml frontend-install check backend-check frontend-check ml-check architecture-check contract-generate contract-check compose-check up down logs smoke migration migration-check

bootstrap: sync-backend sync-ml frontend-install contract-generate

sync-backend:
	uv sync --package culturechamp-backend --extra dev --locked

sync-ml:
	uv sync --package culturechamp-ml --extra dev --locked

frontend-install:
	cd frontend && npm ci

architecture-check:
	python3 scripts/architecture_check.py

backend-check:
	uv run --package culturechamp-backend --extra dev ruff check backend
	uv run --package culturechamp-backend --extra dev mypy backend/app
	uv run --package culturechamp-backend --extra dev pytest backend/tests

frontend-check:
	cd frontend && npm run lint && npm run test -- --run && npm run build

ml-check:
	uv run --package culturechamp-ml --extra dev ruff check ml
	uv run --package culturechamp-ml --extra dev mypy ml/src
	uv run --package culturechamp-ml --extra dev pytest ml/tests

contract-generate:
	uv run --package culturechamp-backend --extra dev python scripts/export_openapi.py
	cd frontend && npm run api:generate

contract-check:
	cd frontend && npm run contract:check

compose-check:
	docker compose config --quiet

check: architecture-check backend-check frontend-check ml-check contract-check compose-check

up:
	docker compose up --build -d --wait

down:
	docker compose down

logs:
	docker compose logs -f --tail=100

smoke:
	BASE_URL=$${BASE_URL:-http://localhost:8000} FRONTEND_URL=$${FRONTEND_URL:-http://localhost:8080} ./scripts/smoke.sh

migration:
	DATABASE_URL=$${DATABASE_URL:-postgresql+asyncpg://culturechamp:culturechamp_local@localhost:5432/culturechamp} uv run --package culturechamp-backend --extra dev alembic -c backend/alembic.ini revision --autogenerate -m "$(NAME)"

migration-check:
	DATABASE_URL=$${DATABASE_URL:-postgresql+asyncpg://culturechamp:culturechamp_local@localhost:5432/culturechamp} uv run --package culturechamp-backend --extra dev alembic -c backend/alembic.ini check
