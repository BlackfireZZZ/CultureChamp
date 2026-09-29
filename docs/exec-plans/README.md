# Execution plans

An ExecPlan is a living document for a large task. Active plans are stored in
`active/`; completed plans are stored in `completed/`.

Required sections are purpose, context, scope/non-goals, acceptance,
progress/decisions, research evidence and validation/recovery.

## Tracking convention

A large initiative is managed as one version-controlled master plan. It contains
milestones and tasks with stable identifiers. GitHub issues or another tracker may
serve as a projection of this plan, but they do not replace architectural decisions
or observable verification results in the repository.

The product concept is recorded in [`docs/product/CONCEPT.md`](../product/CONCEPT.md).
The current master plan and repository task tracker is
[`active/creative-rag-mvp.md`](active/creative-rag-mvp.md). Do not carry forward
completed tasks from the former product as a measure of progress toward the new one.

Every task must have:

- one current owner or `unassigned`;
- a `todo`, `ready`, `in_progress`, `blocked` or `done` status;
- dependencies identified by ID;
- a concrete deliverable and file-ownership boundary;
- acceptance criteria and a falsifying check;
- a handoff reference when ownership changes.

Only the integration owner changes a milestone gate or marks a task `done` after
verifying the result. Writing agents do not take overlapping files. A task must fit
within one cohesive review; if it has more than one independently verifiable result,
it is split before work begins.
