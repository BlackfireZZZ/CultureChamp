FROM python:3.15.2-slim-trixie@sha256:65a65fc7b30b06cb6df4930fd4650697cb23f4c2698ab81fc87e4b031bc36928 AS runtime

COPY --from=ghcr.io/astral-sh/uv:0.12.13@sha256:b485bd65cc2cf1c9a93b3554012c9c3778cf7b1b5fd3d3096ce9e1226c97e1e6 /uv /uvx /bin/
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /workspace

COPY pyproject.toml uv.lock ./
COPY backend/pyproject.toml ./backend/pyproject.toml
COPY ml/pyproject.toml ./ml/pyproject.toml
RUN uv sync --frozen --package culturechamp-backend --no-dev --no-install-workspace

COPY backend ./backend
RUN uv sync --locked --package culturechamp-backend --no-dev --no-editable

RUN useradd --create-home --uid 10001 appuser && mkdir -p /workspace/.private && chown appuser:appuser /workspace/.private
USER appuser
WORKDIR /workspace/backend
EXPOSE 8000
CMD ["/workspace/.venv/bin/uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
