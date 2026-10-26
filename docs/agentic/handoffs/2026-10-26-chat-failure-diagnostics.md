# Chat failure diagnosis and retry repair

## Objective and actual status

Investigate the October 26 provider-success/chat-failure incident. Historical logs
confirm provider completion and recorded usage (1,243 input and 226 output tokens),
followed by a failed chat turn. They do not identify whether answer validation,
citation revalidation, persistence or transport serialization failed. The raw model
answer was not retained. Do not describe any one of those causes as established.
The subsequent provider connectivity failure is a separate observation.

## Worktree / branch / base SHA

- Primary: `/mnt/BlackfireZZZ/Hackatons/CultureChamp`, branch `main`.
- Base: `4602e16063531987e77e5fc9f21126269991ca2d`.
- Isolated worktree: `/home/blackfire/.codex/worktrees/chat-failure-diagnostics/CultureChamp`.
- Branch: `agent/chat-failure-diagnostics`.
- Primary already had unrelated changes in `.env.example`, the product concept,
  the product roadmap and frontend CSS; these were preserved.

## Owner of changed files

The investigating agent owns the backend generation, streaming, chat-store and
quota changes, their focused regression tests, and this handoff. The lead agent
integrates only these files and performs the final runtime build.

## Changed contracts and files

No public API, schema, dependency or source-visibility rule changes. Generation
validation now classifies controlled failure reasons, including malformed JSON,
field types, citation types, fabricated IDs and revoked citations. Stream failures
log only the stage, exception type and controlled reason; they never log exception
messages, tracebacks, model responses, source excerpts or credentials.

The quota guard permits a previously successful provider reservation to retry only
when an owned chat turn has a currently leased, pending claim for a later attempt.
Previous attempt usage remains in the attempt ledger; all attempts count against
the existing daily limits. Completed and standalone IDs remain protected.

The chat store cannot change an already committed completed turn to failed when
later stream serialization fails. This avoids discarding its answer and attempting
to insert its citation ordinals again on retry.

## Decisions and supporting evidence

The gateway records provider success before application validation and database
completion. Previously its `done` reservation blocked the same request ID even
when the chat turn had failed. The UI retries that same ID. The new PostgreSQL
regression reproduces that state and verifies a bounded recovery without removing
usage history. A separate store regression verifies completed answers survive a
late failure. These are demonstrated defects; neither proves the historical first
failure's exact trigger.

## Verification commands and observed results

Commands used the primary checkout's installed Python binaries with `PYTHONPATH=backend`
from the isolated worktree, because fresh `uv` environment setup stalled. No primary
source files or environment packages were changed.

- `python -m pytest backend/tests/test_generation.py backend/tests/test_chat_stream.py`:
  33 passed.
- `ruff check backend`: passed.
- `mypy backend/app`: passed, 78 source files.
- `python scripts/architecture_check.py`: passed.
- `alembic -c backend/alembic.ini upgrade head` against a newly created isolated
  PostgreSQL test database: all migrations completed.
- `python -m pytest backend/tests/test_model_quota.py backend/tests/test_chat_store.py`
  against that database: 4 passed.
- `python -m pytest backend/tests` with the isolated PostgreSQL database configured:
  128 passed, 10 skipped. Skips require vector integration configuration or explicit
  embedding execution; one existing Starlette deprecation warning remains.
- `git diff --check`: passed.

## What remains unverified and why

The exact historical invalid response or postprocessing exception is unrecoverable
from retained logs. No additional paid model calls were made. A live retry after
connectivity returns is needed to identify any recurring failure through the new
safe diagnostics. Deterministic tests do not establish live provider availability.

## Risks and open questions

A retried generation can incur another provider charge, bounded by the existing
attempt limits; the original raw completion is not cached. Do not weaken citation
or evidence validation to make a live response pass.

## Exact next step

The lead agent should review and integrate the isolated commit, rebuild the backend,
run the repository quality gate, and retry the affected conversation after provider
connectivity is restored. Inspect `chat_stream outcome=failed stage=... reason=...`
if it fails again.

## Cleanup completed or retention reason

The isolated worktree and branch are retained for integration. Only a temporary
self-authored test database was used for integration checks; application data and
private original sources were not changed.
