# Response feedback and administrator analytics

## Purpose

Let a signed-in user rate each completed answer with a like or dislike and an optional comment. Let an administrator inspect current ratings and comments over a selectable period without opening private conversations.

## Context

Chats and turns live in PostgreSQL and expire or are deleted with their owning conversation. The existing administrator statistics endpoint counts request metadata without exposing conversation text. `DESIGN.md` supplies the chat and administrator visual baseline.

## Scope and non-goals

Add one mutable rating and optional comment per completed turn, an owned feedback endpoint, chat controls, and rating counts and recent comments in administrator statistics. Feedback follows existing chat deletion and 30-day retention. Do not export prompts or generated answers to the administrator view. Do not use ratings to train a model.

## Acceptance

- The owner can rate, change, comment on, or clear a completed answer; the value survives reload.
- Another user cannot rate the answer, and a failed or pending turn cannot be rated.
- The administrator can select 7, 30, or 90 days and see rating counts, positive share, and up to 100 recent comments with source status and starter metadata.
- Clearing a rating and deleting or expiring a chat removes it from the report.
- API, migration, frontend and runtime checks pass.

## Progress and decisions

- Worktree: `/home/blackfire/.codex/worktrees/6402/CultureChamp`; branch: `agent/response-feedback-analytics`; base: `4e8dc2cb6bd0cd7dbb0b00e905134605599208db`. The primary checkout has unrelated changes and will be preserved.
- Store current feedback on the chat turn so ownership, cascade deletion and retention follow existing rules. A rating change replaces the old value; the report counts the current state.
- Keep administrator reporting free of prompt and answer text. A user-entered feedback comment is visible to administrators.

## Research evidence

The existing `ChatTurn`, `SqlChatStore`, request-statistics query and chat UI provide the closest implementation patterns. This change uses the current modular monolith and its established API, ORM, retention and query boundaries; it introduces no new technology or external data transfer.

## Validation and recovery

Run focused API and component tests, Ruff, mypy, full backend/frontend/ML/architecture/contract checks, a clean PostgreSQL migration with `alembic check`, Compose smoke and the browser flow if available. Review the diff for private data exposure and generated files. The migration adds nullable fields, so recovery is to revert the application while preserving columns, then remove them only after a separate data decision.

Observed before integration:

- Clean PostgreSQL upgrade to `f6c0e1a2b3d4` and `alembic check`: no new operations.
- Final `make check` after rebasing onto `main`, with isolated PostgreSQL and Qdrant: 119 backend tests, 26 frontend tests and 20 ML tests passed; architecture, Ruff, mypy, build, contract and Compose checks passed.
- `npm run test:e2e -- e2e/shell.e2e.ts`: 5 passed, including rating and administrator filters.
- `npm run test:e2e -- e2e/shell.e2e.ts e2e/visual.e2e.ts` after rebasing: 6 passed; no tracked screenshot changed because the rating controls are below the initial viewport and the statistics error screen is unchanged.
- Isolated Compose build and `scripts/smoke.sh`: backend live/ready and frontend passed.
- `npm run test:e2e -- e2e/live.e2e.ts` on a separate fresh Compose project: 1 passed with a self-authored source and fake model.
- Independent read-only review found a stale comment draft after switching ratings and a 100-row query limit that could hide older comments. The controls now reset their draft when saved feedback changes, and the query limits comment-bearing rows. Both cases have regression assertions.
- The live browser test now submits a dislike and comment through the built frontend and confirms it in the administrator API. Repeated live runs exposed a citation focus race in the PDF detail view; focusing the cited DOM node on mount resolves that transition while preserving the existing exact-locator check. Two consecutive live runs passed after the fix.
