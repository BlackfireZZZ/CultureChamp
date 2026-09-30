# Creative RAG MVP — master plan and task tracker

Status: **integration in progress** · Integration base: `790564e2fa8aa3c7307c5a8df3c633829c2745aa` ·
Integration owner: **Codex integration agent** · Last updated: 2026-09-30

## Purpose and observable result

Build a text-only MVP in which a **user** starts with a creative task in a familiar
chat interface, receives a useful answer grounded in approved cultural sources,
and can inspect each cited original. A secondary materials tab supports source
exploration. An **administrator** can inspect a structured, tagged document corpus
and control which exact source revisions are eligible for user retrieval. The answer
model is accessed through a server-side API adapter.

The [concept](../../product/CONCEPT.md) defines product intent, the
[use-case guide](../../product/USE_CASES.md) defines scenarios and starter prompts,
and [`DESIGN.md`](../../../DESIGN.md) defines visual rules. This plan is the task
tracker and execution source of truth. The integrated branch has working identity,
PDF intake, review, and materials APIs; retrieval and live chat remain unfinished.

## Scope and boundaries

**MVP:** two roles; chat list/dialogue/composer; task starters and help; persistent
or explicitly temporary conversations per the identity decision; text input and
text output; approved source browser; source citations opening exact locations;
admin document inventory, structure, tags, processing/approval states; common text
and table ingestion; measured retrieval; an external model API; safety, evaluation,
and operations gates.

**Outside MVP:** image, audio, music, video, OCR for scans unless the first corpus
requires it, multimedia generation, autonomous tool actions, a map-first interface,
public document contribution, nationwide source coverage, and a claim that all
model output is verified. Keep extension seams without building these capabilities.

The phrase "arbitrary text and tables" is a design goal, not an acceptance claim.
The first fixtures will define supported formats and failure behavior. Candidate
formats to evaluate are TXT/Markdown, PDF with extractable text, DOCX, CSV, and
XLSX; HTML and scanned PDFs require separate evidence and decisions.

## Architecture sketch and decision gates

1. **Corpus:** immutable source revisions plus metadata (origin, author, rights,
   language, region, period, sensitivity, approval), extracted sections and table
   cells/rows with stable source locators. Keep original bytes separate from search
   representations. No unapproved revision enters user search or generation.
2. **Ingestion:** authorized intake → file validation/storage → isolated parsing →
   structure normalization → review → exact-revision approval → indexing. Revisions,
   failures, retries, deletion and revocation are auditable and idempotent.
3. **Retrieval:** start with a PostgreSQL lexical baseline. Compare dense and hybrid
   retrieval on a labelled corpus before choosing an embedding model, vector index,
   reranker, or external search service. PostGIS is present in the scaffold; pgvector
   availability and operational fit are **unverified**.
4. **Generation:** retrieval returns approved source segments with locators. A
   provider-neutral model adapter applies timeouts, quotas and cost limits. The
   orchestration layer treats retrieved text as untrusted data, builds a bounded
   context, validates citation IDs against retrieved evidence, and states uncertainty
   when evidence is insufficient. The model never decides its own permissions.
5. **Presentation:** chat is the default user page. A citation opens an authorized
   source detail at the recorded page/section or sheet/row/cell. Materials are a
   secondary tab. Admin inventory and review views live behind server-enforced role
   checks. Desktop uses a chat list and main dialogue; mobile uses an accessible
   drawer or equivalent, without losing the composer or citation navigation.

Record irreversible choices in ADRs before implementation. The initial format,
provider, identity, vector storage, and retention decisions remain open until their
tasks produce evidence.

## Milestones and gates

| Milestone | Gate | Status |
|---|---|---|
| M0 — Product slice and decisions | One narrow corpus/task slice, source policy, format matrix, identity/provider constraints and evaluable examples are recorded. | in_progress: policy and examples exist; real-source rights, reviewer and provider terms are external dependencies |
| M1 — Governed corpus | An approved source revision can be ingested, inspected, cited, revoked, and excluded from user retrieval; text and table locations survive extraction. | in_progress: synthetic PDF vertical path verified; table extraction absent |
| M2 — Measured retrieval | Labelled queries exist; lexical baseline and at least one alternative are compared by source format and language; the selected path meets agreed thresholds. | in_progress: two PostgreSQL lexical configurations measured on provisional labels; expert labels, table source and thresholds absent |
| M3 — Grounded chat | A text brief produces a persisted or explicitly temporary text conversation with validated source citations, no-evidence behavior, and bounded model API calls. | todo |
| M4 — Two-role product UI | User chat, starter guide, source browser/citation view and admin document inventory work at canonical widths and keyboard paths. | in_progress: real auth/materials/admin read path; chat remains local preview |
| M5 — MVP evidence and operations | End-to-end, security, quality, recovery, cost/latency and user/expert review evidence supports a narrow release decision. | todo |

## Task rules

Use only `todo`, `ready`, `in_progress`, `blocked`, and `done` as defined in the
[tracking convention](../README.md). `in_progress` can have verified subresults,
but acceptance remains open until every check passes. `blocked` names a specific
external condition that prevents the remaining work; it is not a substitute for
independent technical work. The integration agent owns task state and acceptance
gates in this branch. Prior authorship stays recorded in handoffs. A `—`
handoff means no ownership transfer has occurred; add a link to a handoff record on
transfer. Dependencies are task IDs, not vague milestone names. No task becomes
`done` until the integration owner checks its acceptance evidence and updates the
gate. Each row is intended as one cohesive review.

## Integration audit at base 790564e

- Primary path: `/mnt/BlackfireZZZ/Hackatons/CultureChamp` (`main`,
  `f67a0586f55e4bf3aa5192628d95a0d0cb527096`). Integration path:
  `/mnt/BlackfireZZZ/Hackatons/CultureChamp-integration-backend`
  (`agent/integration-backend`, `790564e2fa8aa3c7307c5a8df3c633829c2745aa`).
  `git status --short --branch` was clean at the integration base. Existing corpus,
  access/UI and architecture worktrees and branches are retained. This branch is
  the isolated checkout for the remaining large task; logical commits will be
  verified here before integration with `main`.
- Hypothesis: a synthetic, explicitly non-cultural document can prove ingestion,
  rights filtering, retrieval, citation navigation, and persisted chat mechanics.
  The hypothesis fails if an unapproved revision reaches search/model context, a
  citation changes revision or location, a retry duplicates a turn, or a user
  reads another user's chat. Passing it cannot establish cultural or legal release.
- S01 and S02 are blocked on an appointed rights/cultural reviewer and exact-source
  permission decisions. Q04 is blocked on recruited target users. These remain
  external dependencies. The three supplied PDFs stay held and are not user or
  provider fixtures. S03 can proceed with the fake provider and retention work;
  external provider activation awaits approved terms, key handling and budget.
- Technical tasks with verified subsets remain `in_progress`; their unmet checks
  are in their acceptance columns and the [prior handoff](../../agentic/handoffs/integration-backend.md).
  `ready` marks independent work with sufficient technical inputs; dependent work
  stays `todo` until its prerequisites are met.

### M0 — Product, policy and evidence

| ID | Status · owner · handoff | Depends | Deliverable and owned area | Acceptance and smallest falsifying check |
|---|---|---|---|---|
| S01 | blocked · integration agent · [handoff](../../agentic/handoffs/integration-backend.md) | — | Choose one region/community, 2–3 creative tasks and a bounded initial corpus; `docs/product/` | A written slice maps at least three real briefs to permitted sources and expected output; review against the concept and UC-01–UC-06. |
| S02 | blocked · integration agent · [handoff](../../agentic/handoffs/integration-backend.md) | — | Define verified/approved, rights, sensitive-source and revocation policy; `docs/product/` | Each fixture source has a reviewer, rights decision and user-visibility rule; challenge with a restricted and a disputed source. |
| S03 | in_progress · integration agent · [handoff](../../agentic/handoffs/integration-backend.md) | — | Decide user identity/guest mode, admin bootstrap, conversation retention, model-provider data handling and budget constraints; `docs/decisions/` | Decision records user/admin access, deletion, provider data flow and who holds keys; threat-review one leaked-token and one cross-role case. |
| S04 | in_progress · integration agent · [handoff](../../agentic/handoffs/integration-backend.md) | S01 | Inventory supplied text/table fixtures and choose supported MVP formats; `docs/product/` | Format matrix records extraction fidelity, locators, unsupported cases and sample rights; inspect at least one prose file and one table. |
| S05 | in_progress · integration agent · [handoff](../../../frontend/HANDOFF.md) | S01, S02, S04 | Build task/query examples and expert review rubric; `ml/evals/` | Cases cover factual support, interpretation, no evidence, conflicting accounts, sensitive content and table lookup; a reviewer can label each without hidden knowledge. |

### M1 — Corpus contracts and administration

| ID | Status · owner · handoff | Depends | Deliverable and owned area | Acceptance and smallest falsifying check |
|---|---|---|---|---|
| C01 | in_progress · integration agent · [handoff](../../agentic/handoffs/integration-backend.md) | S02, S04 | ADR and schema for source identity, immutable revisions, metadata, tags, structure, table locators and approval; `docs/decisions/`, `backend/app/domain/` | A citation uniquely resolves to one source revision and page/section/sheet/row/cell; changing metadata never rewrites cited text. |
| C02 | done · integration agent · [handoff](../../agentic/handoffs/integration-backend.md) | S03 | Server-enforced user/admin identity and authorization boundary; `backend/app/application/`, `backend/app/api/` | User requests cannot read admin/unapproved records even with guessed IDs; role tests cover direct API calls and expired credentials. |
| C03 | done · integration agent · [handoff](../../agentic/handoffs/integration-backend.md) | C01 | Alembic tables and repository ports/adapters for sources, revisions, tags and locators; `backend/app/infrastructure/db/` | Clean PostgreSQL upgrade works and repository round-trip preserves the exact revision and locator; migration check and integration test pass. |
| C04 | done · integration agent · [handoff](../../agentic/handoffs/integration-backend.md) | C02, C03, S04 | Authorized file intake, private storage, type/size validation and immutable content hash; `backend/app/infrastructure/` | Spoofed type, oversized file and duplicate retry are rejected or safely deduplicated; original bytes stay outside public webroot. |
| C05 | in_progress · integration agent · [handoff](../../agentic/handoffs/integration-backend.md) | C04 | Text extraction adapters with structure and location preservation for approved formats; `backend/app/infrastructure/ingestion/` | Fixtures produce non-empty ordered sections with stable page/heading locators; malformed input fails with a recorded error, not partial publication. |
| C06 | ready · integration agent · — | C04 | Table extraction adapters retaining sheet/table, row/column, headers and cell meaning; `backend/app/infrastructure/ingestion/` | A queryable table fact maps back to its original sheet/table and cell range; merged/empty cells and encoding errors have fixture checks. |
| C07 | in_progress · integration agent · [handoff](../../agentic/handoffs/integration-backend.md) | C03, C05, C06, S02 | Background processing, revision lifecycle, review and exact-revision approval/revocation; `backend/app/application/ingestion/` | Retried processing is idempotent; only an approved revision appears in user retrieval, and revocation removes it without destroying provenance. |
| C08 | done · integration agent · [handoff](../../agentic/handoffs/integration-backend.md) | C02, C03, C07 | Admin inventory/detail/filter API and generated OpenAPI client contract; `backend/app/api/`, `contracts/` | Admin sees tags, structure, state and errors; user receives denial for the same unpublished detail; success/error/schema checks pass. |
| C09 | in_progress · integration agent · [handoff](../../agentic/handoffs/integration-backend.md) | C02, C03, C07 | User materials list/detail and authorized original/locator API; `backend/app/api/materials/`, `contracts/` | User sees approved revisions only; section/page/sheet/row links resolve to the same revision, and forbidden originals cannot be fetched. |
| C10 | done · integration agent · [handoff](../../agentic/handoffs/integration-backend.md) | C02, C04, C07 | Admin import/status and approval/revocation command API; `backend/app/api/admin/`, `contracts/` | Authorized import reaches a reviewable state; an admin can approve/revoke exact revisions; user and malformed commands are denied. |

### M2 — Retrieval and evaluation

| ID | Status · owner · handoff | Depends | Deliverable and owned area | Acceptance and smallest falsifying check |
|---|---|---|---|---|
| R01 | in_progress · integration agent · — | S05, C05, C06 | Gold query-to-source/locator judgements and retrieval harness; `ml/evals/` | Evaluation reports recall@k and ranking metrics by language, format and table/prose slice; a missing relevant source fails a labelled case. |
| R02 | in_progress · integration agent · — | C07, R01 | PostgreSQL lexical indexing/search baseline with metadata and approval filters; `backend/app/infrastructure/db/lexical_search.py` | Relevant exact names and table values are found; an unapproved revision is absent before ranking; query plan and R01 metrics are recorded. |
| R03 | todo · integration agent · — | R01, R02, S03 | Dense/hybrid retrieval experiment, embedding/provider and index compatibility check; `ml/evals/`, `docs/decisions/` | Compare same gold set with cost/latency and relevant-source recall; test pgvector availability before adopting it. No production index is implied by the experiment. |
| R04 | todo · integration agent · — | R02, R03 | ADR selecting retrieval, chunking, fusion/reranking and thresholds; `docs/decisions/` | Chosen configuration beats or justifies retaining the lexical baseline on agreed slices; regressions and tradeoffs are explicit. |
| R05 | in_progress · integration agent · — | R04, C07 | Application retrieval port/service with filters, bounded context and stable evidence IDs; `backend/app/application/retrieval.py` | Same query/approved corpus yields traceable segments; revoked/restricted text never returns; integration tests cover prose and tables. |

### M3 — Model API and grounded conversation

| ID | Status · owner · handoff | Depends | Deliverable and owned area | Acceptance and smallest falsifying check |
|---|---|---|---|---|
| G01 | ready · integration agent · — | S03 | Server-side model API adapter with secret isolation, timeout, retry, rate/cost limits and fake provider; `backend/app/infrastructure/model/` | A timeout or provider error yields a bounded safe failure; tests show no key or raw prompt in logs and no browser-side provider call. |
| G02 | todo · integration agent · — | R05, G01, S02 | Text-only orchestration: task prompt, approved evidence context, uncertainty and fact/interpretation/creation framing; `backend/app/application/generation/` | A supplied source supports the answer; an empty evidence set cannot become a sourced cultural claim; deterministic fake-model cases pass. |
| G03 | todo · integration agent · — | G02, C01 | Citation validation and source-location resolution; `backend/app/application/citations/` | Every displayed citation maps to a retrieved approved revision/locator; fabricated IDs are removed or cause a safe failure. |
| G04 | todo · integration agent · — | C02, G03, S03 | Conversation/message model and chat API (list, create, send, continue, delete per retention decision); `backend/app/api/`, `backend/app/infrastructure/db/` | One user cannot read another's chat; a retry does not duplicate a turn; API errors and generated schema are tested. |
| G05 | todo · integration agent · — | G02, G03, S02 | Prompt-injection and sensitive/no-evidence guardrails; `backend/app/application/generation/`, `ml/evals/` | Retrieved instructions cannot change role/secret policy; UC-07–UC-11 return safe, accurately labelled behavior in adversarial fixtures. |

### M4 — User and administrator interfaces

| ID | Status · owner · handoff | Depends | Deliverable and owned area | Acceptance and smallest falsifying check |
|---|---|---|---|---|
| U01 | ready · integration agent · — | S01, S03 | Responsive information architecture and reviewed wireframes for two roles; `docs/product/`, `DESIGN.md` | Default chat, secondary materials, admin inventory and source navigation are demonstrated at 360/768/1280/1440 px with keyboard paths. |
| U02 | todo · integration agent · — | U01, G04 | Chat list, dialogue, composer and request states; `frontend/src/features/chat/` | Start/continue/switch chats, send with keyboard, recover from timeout without losing draft; component and e2e checks pass. |
| U03 | ready · integration agent · — | U01, S01 | Editable starter prompts and in-app use-case help sourced from `USE_CASES.md`; `frontend/src/features/onboarding/` | Each UC-01–UC-06 starter fills the composer with an editable task; users can reach the guide without starting a chat. |
| U04 | todo · integration agent · — | U01, C09 | Approved materials list, filters and document detail; `frontend/src/features/materials/` | User can find and inspect an approved prose and table source; unpublished items never appear; empty/error/keyboard paths pass. |
| U05 | todo · integration agent · — | U02, U04, G03 | Citation cards/links and exact-location inspector with return-to-chat navigation; `frontend/src/features/citations/` | Clicking a citation opens the cited revision at its section/page or sheet/row; withdrawn/unavailable locations show an honest state. |
| U06 | todo · integration agent · — | U01, C08, C10 | Admin document inventory/detail UI with structure, tags, status and explicit review actions; `frontend/src/features/admin/` | Admin can filter, inspect errors and approve/revoke an exact revision; user cannot enter the route or fetch its data. |

### M5 — Integration, quality and release evidence

| ID | Status · owner · handoff | Depends | Deliverable and owned area | Acceptance and smallest falsifying check |
|---|---|---|---|---|
| Q01 | todo · integration agent · — | U02, U03, U05, U06, G05 | Compose-backed end-to-end journeys for both roles and source revocation; `frontend/e2e/`, `backend/tests/integration/` | UC-01, UC-06–UC-11 and admin approval/revocation work against a clean seeded stack; `make check`, migration and smoke pass. |
| Q02 | todo · integration agent · — | R01, R04, G05, Q01 | Offline retrieval/answer evaluation, expert review and release thresholds; `ml/evals/`, `docs/exec-plans/` | Report slice-level retrieval, groundedness, citation precision, unsupported-claim and refusal results against baseline; expert reviews sampled outputs. |
| Q03 | todo · integration agent · — | G01, C07, Q01 | Operations runbook: secrets, backups, reindex/replay, deletion, cost/latency and failure alerts; `docs/operations/`, `scripts/` | A clean restore/reindex and provider-outage drill preserve approved-state isolation and give observable recovery evidence. |
| Q04 | blocked · integration agent · — | Q02, U03 | Target-user test of starter tasks, chat usefulness and source trust; `docs/product/` | At least one professional and one occasional-user scenario are observed with the same rubric; findings change or confirm the next MVP backlog. |

## Integration order and parallelism

The first vertical slice should use a small approved fixture, lexical retrieval, a
fake model adapter, and one chat/citation path. It should prove source permissions
and exact citation navigation before optimizing relevance. UI contracts may be
developed against deterministic fixtures while ingestion runs. Frontend and backend
owners must agree on OpenAPI before working in parallel; no two writing owners edit
the same contract file. An external model is connected only after the fake-provider
path, evaluation cases, and data-handling constraints exist.

## Research evidence and alternatives

- The original [RAG paper](https://arxiv.org/abs/2005.11401) motivates coupling
  retrieval with generation; it does not decide this product's chunking or store.
- [PostgreSQL full-text search](https://www.postgresql.org/docs/17/textsearch.html)
  supplies a local lexical baseline and ranking. Its Russian/multilingual and table
  performance must be measured on the actual corpus.
- [pgvector](https://github.com/pgvector/pgvector#hybrid-search) documents exact,
  approximate and hybrid options. Approximate indexes trade recall for speed; use
  only after an evaluation and runtime compatibility check.
- [BEIR](https://arxiv.org/abs/2104.08663) shows why retrieval needs heterogeneous
  evaluation; a project-specific labelled set remains necessary.
- [OWASP RAG Security](https://cheatsheetseries.owasp.org/cheatsheets/RAG_Security_Cheat_Sheet.html)
  treats retrieved documents as an untrusted input, and
  [OWASP File Upload](https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html)
  informs bounded, validated admin intake. These are design inputs, not evidence
  that the implementation is safe.

## Progress and decisions

- **2026-09-30, retrieval baseline:** a clean PostgreSQL migration added the
  `russian` GIN expression index. The application retrieval service and SQL
  adapter apply current exact-revision, rights and sensitivity filters before
  ranking; tests prove held/revoked exclusion and immediate revocation on a
  synthetic corpus. A temporary local PostgreSQL evaluation compared `simple`
  and `russian` against the same eight provisional qrels. Recall@5 was 0.40 and
  0.80; no-evidence false-positive rates were 0.667 and 1.000. The Russian
  configuration is a provisional engineering default, not a release threshold.
  Clean migration and Alembic check passed; a forced-index plan used the GIN
  index and applied current-decision filtering before sort. A fresh migrated
  PostgreSQL database and `make check` passed all 40 backend, 12 frontend and
  six ML tests with no database skips; static, OpenAPI and Compose checks passed.
  See [ADR 0005](../../decisions/0005-postgres-lexical-baseline.md).
- **2026-09-30, integration continuation:** reconciled task states to the five
  accepted values and assigned one integration owner. The clean branch at
  `790564e` was retained as the work base. An API request-body ceiling and Caddy
  ceiling now reject oversized multipart input before spooling. Candidate PDF
  extraction runs in a separate resource-limited process with a wall timeout;
  failure remains retryable. The focused ingestion suite passed 18 tests and
  `make check` passed 34 backend tests (four PostgreSQL tests skipped), 12
  frontend tests, six ML tests, static checks, contract and Compose config.
  A fresh Compose build reached healthy backend, worker, database and frontend;
  clean-database migration, four PostgreSQL integration tests, Alembic check,
  smoke, and live API/proxy 413 checks passed. A synthetic text PDF parsed in
  the packaged worker. Process limits do not prove a hardened parser sandbox.
  See ADR 0003.
- **2026-09-30, integration:** `agent/integration-backend` merged the fixed corpus
  and access/UI parents, then incorporated the second owner's reviewed frontend and
  evaluation commits by cherry-pick. The synthetic, self-authored PDF path now
  supports admin intake, worker extraction with physical page locators, exact
  approval, user list/detail, and immediate revocation. Three supplied PDFs remain
  held candidates and were never approved for user answers or provider transfer.
  Clean PostgreSQL migration and `alembic check` passed. Final `make check` passed:
  35 backend, 12 frontend and 6 ML tests; OpenAPI and Compose config matched.
  Four Playwright tests and live Compose HTTP worker/approval/revocation paths
  also passed. See the [integration handoff](../../agentic/handoffs/integration-backend.md).
- **Remaining M1 limits:** no rights-cleared real corpus, appointed review authority,
  table fixture/extractor, hardened parser sandbox, tag-value
  admin filtering, or passage-level sensitivity exclusion. Exact original-file
  access and admin state/decision filters are implemented for the PDF slice.
  PDF-03 reading order still needs full review. The live test's synthetic approval
  demonstrates access behavior, not cultural or legal approval of any PDF fixture.
- **2026-09-30:** Three supplied PDF originals were moved into the
  [retrieval fixture inventory](../../../data/retrieval-fixtures/README.md).
  Their page counts and hashes are recorded, and text extraction produced
  nonempty output. S04 remains open: extraction fidelity, exact locators,
  rights and a table fixture still need assessment.
- **2026-09-30:** Product shape accepted from the user: two roles; chat as the user
  home; starter tasks and in-app guide; secondary materials view; source-linked
  answers; admin structured document inventory; text-only MVP; external model API.
- **2026-09-30:** Created the use-case guide and tracker. No ingestion, retrieval,
  model API, role system or product UI task was complete at that initial checkpoint.
- **Open:** approval authority and rights for a real source, a table fixture,
  model and embedding providers, chat retention implementation, broader format
  support, and quality thresholds. Do not infer permission or product validation
  from the synthetic integration fixture.

## Validation and recovery

For documentation edits, verify links and paths, run `git diff --check`, and inspect
that every task has ID/status/owner/dependencies/deliverable/acceptance/check/handoff.
For implementation, use the nearest `AGENTS.md` and
[`VERIFICATION_MATRIX.md`](../../agentic/VERIFICATION_MATRIX.md). Test migrations
on a clean database and full user/admin flows in Compose. Preserve raw source
revisions and audit events so a failed extraction or index rebuild can be retried;
revocation must fail closed. Record command output, corpus version, model/version,
cost, latency and evaluator identity in milestone evidence. If a gate fails, retain
the last approved corpus/index and do not promote a new revision or model path.
