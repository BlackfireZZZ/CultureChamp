# ADR 0001: Modular monolith

## Status

Retained as the engineering baseline for the new concept; bounded contexts remain
open until product boundaries are agreed.

## Decision

When these components are needed, use one deployable FastAPI backend with explicit
`domain`, `application`, `api` and `infrastructure` boundaries. Keep the web frontend
and offline ML workspace separate. Split services only when observed scaling,
ownership or reliability requirements justify the operational cost.

## Consequences

Contracts stay explicit without premature distributed systems. Boundary checks
and dependency direction are mandatory because process boundaries do not enforce them.
