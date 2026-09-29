# AGENTS.md

## Repository mission

CultureChamp helps people create contemporary, culturally specific concepts and
content using verified heritage sources from the peoples of Russia. The canonical
product concept is `docs/product/CONCEPT.md`. The primary workflow starts from a
creative task and produces a usable result with traceable cultural references where
relevant. Do not carry requirements from the previous Living Map of Russia product
into this repository. Treat the concept's MVP hypothesis and listed assumptions as
questions to validate, not proven facts.

Architecture decisions retained in `docs/decisions/` are the engineering baseline;
revisit them if product needs require different capabilities.

These rules apply throughout the repository. Future nested `AGENTS.md` files may
refine them for their subtrees.

## Agent contract map

- Task specification: `docs/agentic/TASK_SPEC.md`.
- Verification matrix: `docs/agentic/VERIFICATION_MATRIX.md`.
- Permission boundaries: `docs/agentic/PERMISSIONS.md`.
- Handoff contract: `docs/agentic/HANDOFF.md`.
- Long-running plans: `docs/exec-plans/README.md`.

## Documentation language

All project documentation authored or updated by agents must be written in English,
including ADRs, plans, runbooks, handoffs and code comments that function as project
documentation. Immutable primary sources and supplied evidence may remain in their
original language. Proper nouns and verbatim source excerpts may retain their
original form when required, with an English explanation where useful.

## Evidence before changes

Before changing files, state a falsifiable expected result, locate the current
contract or source of truth, select the smallest falsifying check, and find
consumers of the changed contract with `rg`.

If a required check cannot be run, record the blocker and request a human decision.

## Research for complex solutions

Before introducing a complex technology, data model, security mechanism, AI/ML
approach or non-trivial UX pattern, find comparable implementations. Prefer official
documentation, standards, primary papers and engineering reports with measurements.
Record similarities, differences and risks. A decision that is expensive to reverse
requires an ADR in `docs/decisions/`.

## Required workflow

1. Read `README.md`, `docs/product/CONCEPT.md`, this file and the nearest architecture documentation.
2. Run `git status` and preserve unfinished work owned by others.
3. Record the hypothesis and acceptance criteria.
4. For a new complex solution, study official documentation or primary sources.
5. Start with a test or contract, or explain why an existing check is sufficient.
6. Make the smallest coherent change in the correct layer.
7. Run focused checks, then the repository's full check when it exists.
8. Inspect the diff for secrets, generated files and boundary or contract violations.
9. Report observed results, assumptions and unverified risks.

## Large tasks and worktrees

A task is large if it affects at least eight files, three or more areas, a public API,
database, authentication, deployment or production dependency; contains at least
three milestones; takes more than 90 minutes; or uses concurrent writing agents.

For a large task, use an isolated worktree before the first implementation change.
Never remove a dirty worktree or use force, reset or clean against work owned by
others. Record the primary path, base SHA, branch and `git status`; use a unique
`agent/<slug>` branch; give every writing agent a non-overlapping ownership area;
report verification and integration method. Preserve unfinished branches and work.

## Parallel agent work

When parallel agent work is explicitly requested, divide independent research,
reviews, tests and non-overlapping changes. One file or contract has one owner. The
lead agent integrates results and runs the final quality gate. Use the handoff
format in `docs/agentic/HANDOFF.md`.

## Architecture boundaries

- `domain` does not import FastAPI, SQLAlchemy, Pydantic or infrastructure.
- `application` coordinates use cases through protocols; HTTP and SQL are forbidden.
- `infrastructure` implements external adapters and repositories.
- `api` validates transport contracts and invokes application services.
- Frontend feature code accesses HTTP only through `src/api` and hooks.
- `components/ui` contains local primitives without product logic.
- Online web workers do not import training or batch code.

These boundaries apply when the corresponding components are introduced. The product
concept determines which components are needed.

## Cultural evidence and generation

- Distinguish a source-supported cultural fact, an interpretation based on sources,
  and a newly generated creative result.
- Preserve attribution, regional and historical context, and usage rights for
  cultural source material when the corresponding data and workflows are designed.
- Do not present invented traditions, symbols or unsupported model claims as verified.
- Treat sacred, ritual, restricted and community-sensitive material as requiring
  explicit review or exclusion rules before generation from it.

## Database and API

- Change the schema only through a new migration tested on a clean database.
- APIs are backward compatible by default; field removal requires versioning or
  deprecation.
- Logs contain no personal data or secrets.

## Frontend and design

- `DESIGN.md` is the source of truth for frontend visual work.
- Interactive states cover loading, empty, error and keyboard paths.
- Color is not the only carrier of meaning.

## Definition of done

Acceptance criteria are met, relevant tests and static checks pass, migrations and
contracts are synchronized when applicable, documentation is updated, and the report
includes commands and observed results.
