# CultureChamp delivery — MVP and full-concept task baseline

Status: **integration in progress** · Integration base: `790564e2fa8aa3c7307c5a8df3c633829c2745aa` ·
Integration owner: **Codex integration agent** · Last updated: 2026-09-30

## Purpose and observable result

Build a first text-output slice in which a **user** starts with a creative task in a familiar
chat interface, receives a useful answer grounded in approved cultural sources,
and can inspect each cited original. A secondary materials tab supports source
exploration. An **administrator** can inspect a structured, tagged document corpus
and control which exact source revisions are eligible for user retrieval. The answer
model is accessed through a server-side API adapter. The architecture must also
support the full concept: additional cultural collections, image and audio source
material, more creative domains, and institutional review workflows. A narrow
first release does not remove these product requirements.

The [concept](../../product/CONCEPT.md) defines product intent, the
[use-case guide](../../product/USE_CASES.md) defines scenarios and starter prompts,
and [`DESIGN.md`](../../../DESIGN.md) defines visual rules. This plan is the task
tracker and execution source of truth. The integrated branch has working identity,
PDF intake, review and materials APIs. Vector retrieval and persisted chat have
synthetic backend checks; UI and release evidence remain unfinished.

## Scope and boundaries

**MVP:** two roles; chat list/dialogue/composer; task starters and help; persistent
or explicitly temporary conversations per the identity decision; text input and
text output; approved source browser; source citations opening exact locations;
admin document inventory, structure, tags, processing/approval states; common text
and table ingestion; measured retrieval; an external model API; safety, evaluation,
and operations gates.

**After the first release:** image, audio, music and video source understanding;
OCR for scans; visual and audio output generation; larger cultural and creative
coverage; and institutional participation. These are tracked in the full-concept
backlog below. Autonomous actions, a map-first interface, indiscriminate public
contribution and a claim that all model output is verified are not concept goals.

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
3. **Retrieval:** generate versioned embeddings and search a dedicated vector
   database for the first text slice. PostgreSQL remains authoritative for source
   rights, exact revisions and locators. Compare vector-only and hybrid relevance
   on the same labelled corpus. The lexical SQL path is an offline baseline, not
   the chat retrieval implementation. See [ADR 0006](../../decisions/0006-vector-retrieval-and-media.md).
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

Record irreversible choices in ADRs before implementation. Source formats,
provider, embedding quality, media storage and retention limits require further
evidence; ADR 0006 sets the vector storage direction.

## Milestones and gates

| Milestone | Gate | Status |
|---|---|---|
| M0 — Product slice and decisions | One narrow corpus/task slice, source policy, format matrix, identity/provider constraints and evaluable examples are recorded. | in_progress: policy and examples exist; real-source rights, reviewer and provider terms are external dependencies |
| M1 — Governed corpus | An approved source revision can be ingested, inspected, cited, revoked, and excluded from user retrieval; text and table locations survive extraction. | in_progress: synthetic PDF and UTF-8 CSV vertical paths verified; real table fidelity and rights remain open |
| M2 — Vector retrieval | Versioned embeddings are indexed in Qdrant; chat uses vector candidates with authoritative rights rechecks; measured retrieval meets agreed thresholds. | in_progress: synthetic vector and revocation checks pass; same-fixture provisional dense recall@5 1.00; expert relevance, replay and release thresholds remain |
| M3 — Grounded chat | A text brief produces a persisted text conversation with validated source citations, no-evidence behavior, and bounded model API calls. | in_progress: a live synthetic browser journey passes with the fake provider; exact external provider activation and reviewed cultural answers remain |
| M4 — Two-role product UI | User chat, starter guide, source browser/citation view and admin document inventory work at canonical widths and keyboard paths. | in_progress: live browser tagged upload, server-filtered materials, review, cited answer, original download and revocation pass; full use-case checks remain |
| M5 — MVP evidence and operations | End-to-end, security, quality, recovery, cost/latency and user/expert review evidence supports a narrow release decision. | in_progress: one clean-stack synthetic journey passes; remaining release gates are open |

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
| C06 | in_progress · integration agent · [handoff](../../agentic/handoffs/integration-backend.md) | C04 | Table extraction adapters retaining sheet/table, row/column, headers and cell meaning; `backend/app/infrastructure/ingestion/` | A queryable table fact maps back to its original sheet/table and cell range; merged/empty cells and encoding errors have fixture checks. Synthetic CSV cells and invalid encoding are covered; real table and XLSX merged cells remain open. |
| C07 | in_progress · integration agent · [handoff](../../agentic/handoffs/integration-backend.md) | C03, C05, C06, S02 | Background processing, revision lifecycle, review and exact-revision approval/revocation; `backend/app/application/ingestion/` | Retried processing is idempotent; only an approved revision appears in user retrieval, and revocation removes it without destroying provenance. |
| C08 | done · integration agent · [handoff](../../agentic/handoffs/integration-backend.md) | C02, C03, C07 | Admin inventory/detail/filter API and generated OpenAPI client contract; `backend/app/api/`, `contracts/` | Admin sees tags, structure, state and errors; user receives denial for the same unpublished detail; success/error/schema checks pass. |
| C09 | in_progress · integration agent · [handoff](../../agentic/handoffs/integration-backend.md) | C02, C03, C07 | User materials list/detail and authorized original/locator API; `backend/app/api/materials/`, `contracts/` | Page and table/row/cell locators survive the API contract without invented pages; user sees approved revisions only. Exact revision tags and server-side title/author/tag, region, people, period and format filters pass synthetic API checks; real table proof remains open. |
| C10 | done · integration agent · [handoff](../../agentic/handoffs/integration-backend.md) | C02, C04, C07 | Admin import/status and approval/revocation command API; `backend/app/api/admin/`, `contracts/` | Authorized import reaches a reviewable state; an admin can approve/revoke exact revisions; user and malformed commands are denied. |

### M2 — Retrieval and evaluation

| ID | Status · owner · handoff | Depends | Deliverable and owned area | Acceptance and smallest falsifying check |
|---|---|---|---|---|
| R01 | in_progress · integration agent · — | S05, C05, C06 | Gold query-to-source/locator judgements and retrieval harness; `ml/evals/` | Evaluation reports recall@k and ranking metrics by language, format and table/prose slice; a missing relevant source fails a labelled case. |
| R02 | done · integration agent · — | C07 | Historical PostgreSQL lexical baseline; `backend/app/infrastructure/db/lexical_search.py` | Reproducible provisional metrics and rights-filter test are retained for comparison only; ADR 0005 is superseded. |
| R03 | in_progress · integration agent · — | C07, S03 | Versioned multilingual text embeddings, dedicated Qdrant collection, ingestion/reindex jobs and index health; `backend/app/infrastructure/vector/` | A paraphrased synthetic query finds its passage; retries are idempotent; clean Compose replay rebuilds the index; no chat request uses SQL lexical ranking. |
| R04 | in_progress · integration agent · — | R03, R01 | ADR 0006 and measured retrieval selection, chunking, fusion/reranking and thresholds; `docs/decisions/`, `ml/evals/` | Same frozen corpus and query set compare vector-only and lexical/hybrid by language, format, latency and cost; expert-reviewed regressions and tradeoffs are explicit. |
| R05 | in_progress · integration agent · — | R03, C07 | Application retrieval port/service with current-authority filters, bounded context and stable evidence IDs; `backend/app/application/retrieval.py` | Same query/approved corpus yields traceable vector candidates; revoked/restricted text never returns even with stale vector points; integration tests cover prose and tables. |

### M3 — Model API and grounded conversation

| ID | Status · owner · handoff | Depends | Deliverable and owned area | Acceptance and smallest falsifying check |
|---|---|---|---|---|
| G01 | in_progress · integration agent · — | S03 | Server-side model API adapter with secret isolation, timeout, retry, rate/cost limits and fake provider; `backend/app/infrastructure/model/` | Fake and failure paths pass; external provider configuration and provider-transfer filtering are wired; exact service/model, live activation, measured cost and secret-handling review remain. |
| G02 | in_progress · integration agent · — | R05, G01, S02 | Text orchestration: task prompt, approved evidence context, uncertainty and fact/interpretation/creation framing; `backend/app/application/generation/` | Synthetic fake-model and live vector-backed cases pass; the fact field now requires a verbatim cited span. Expert support review remains. |
| G03 | in_progress · integration agent · — | G02, C01 | Citation validation and source-location resolution; `backend/app/application/citations/` | Synthetic exact-revision checks pass; mixed format and source withdrawal UI checks remain. |
| G04 | in_progress · integration agent · — | C02, G03, S03 | Conversation/message model and chat API (list, create, send, continue, delete per retention decision); `backend/app/api/`, `backend/app/infrastructure/db/` | PostgreSQL ownership/retry/citation test passes; client and end-to-end checks remain. |
| G05 | in_progress · integration agent · — | G02, G03, S02 | Prompt-injection and sensitive/no-evidence guardrails; `backend/app/application/generation/`, `ml/evals/` | Model-selected IDs are rechecked and an unsupported fact with a valid citation now fails closed. This does not prove that interpretation or creative prose is culturally supported; adversarial provider and UC-07–UC-11 review remain. |

### M4 — User and administrator interfaces

| ID | Status · owner · handoff | Depends | Deliverable and owned area | Acceptance and smallest falsifying check |
|---|---|---|---|---|
| U01 | ready · integration agent · — | S01, S03 | Responsive information architecture and reviewed wireframes for two roles; `docs/product/`, `DESIGN.md` | Default chat, secondary materials, admin inventory and source navigation are demonstrated at 360/768/1280/1440 px with keyboard paths. |
| U02 | in_progress · integration agent · — | U01, G04 | Chat list, dialogue, composer and request states; `frontend/src/features/chat/` | Component checks pass for persisted send and failure draft; live browser, switching, deletion and retry paths remain to be observed. |
| U03 | ready · integration agent · — | U01, S01 | Editable starter prompts and in-app use-case help sourced from `USE_CASES.md`; `frontend/src/features/onboarding/` | Each UC-01–UC-06 starter fills the composer with an editable task; users can reach the guide without starting a chat. |
| U04 | in_progress · integration agent · — | U01, C09 | Approved materials list, filters and document detail; `frontend/src/features/materials/` | A user can filter approved materials by text, region, people, period and format; tags and rights appear on exact details. Synthetic CSV filter and original access pass live browser checks. Prose/table coverage, concise descriptions and broader discovery remain open. |
| U05 | in_progress · integration agent · — | U02, U04, G03 | Citation cards/links and exact-location inspector with return-to-chat navigation; `frontend/src/features/chat/`, `frontend/src/features/materials/` | A component check opens an exact cited text segment and returns to chat; table locators and live withdrawal remain. |
| U06 | in_progress · integration agent · — | U01, C08, C10 | Admin document inventory/detail UI with structure, tags, status and explicit review actions; `frontend/src/features/admin/` | Admin component checks cover filter and exact approval/revocation with explicit rights; live browser upload now records revision tags. Broader format, error and keyboard review remains. |

### M5 — Integration, quality and release evidence

| ID | Status · owner · handoff | Depends | Deliverable and owned area | Acceptance and smallest falsifying check |
|---|---|---|---|---|
| Q01 | in_progress · integration agent · — | U02, U03, U05, U06, G05 | Compose-backed end-to-end journeys for both roles and source revocation; `frontend/e2e/`, `backend/tests/integration/` | A seeded stack passes the self-authored CSV journey through candidate isolation, tagged upload, review, server-filtered materials, Qdrant indexing, cited chat, exact original download and revocation. UC-01, UC-06–UC-11, canonical-width paths and release-specific gates remain. |
| Q02 | todo · integration agent · — | R01, R04, G05, Q01 | Offline retrieval/answer evaluation, expert review and release thresholds; `ml/evals/`, `docs/exec-plans/` | Report slice-level retrieval, groundedness, citation precision, unsupported-claim and refusal results against baseline; expert reviews sampled outputs. |
| Q03 | todo · integration agent · — | G01, C07, Q01 | Operations runbook: secrets, backups, reindex/replay, deletion, cost/latency and failure alerts; `docs/operations/`, `scripts/` | A clean restore/reindex and provider-outage drill preserve approved-state isolation and give observable recovery evidence. |
| Q04 | blocked · integration agent · — | Q02, U03 | Target-user test of starter tasks, chat usefulness and source trust; `docs/product/` | At least one professional and one occasional-user scenario are observed with the same rubric; findings change or confirm the next MVP backlog. |

## Full-concept backlog after the first text release

These items are product commitments to plan and validate, not claims that a
specific model or provider already meets quality requirements. Each keeps the
same source identity, rights and citation rules as the text slice.

| ID | Status | Deliverable | Acceptance evidence |
|---|---|---|---|
| F01 | todo | Expand governed collections across communities, regions and periods with institutional and community review. | Each added slice has provenance, accountable review, rights scopes, conflict handling and expert-labelled tasks. |
| F02 | todo | Ingest images and scanned pages into private media storage with image regions, OCR/layout text and stable visual locators. | Authorized image queries return the correct image/region; a revoked image disappears; captions and OCR are distinguished from source facts. |
| F03 | todo | Ingest recordings and music with transcript, time ranges, performer/recording rights and audio embeddings. | A query opens the cited recording at the correct time span; transcript and audio similarity are evaluated separately; restricted recordings never leak. |
| F04 | todo | Add modality-aware and cross-modal retrieval with separately versioned text, visual and audio encoders. | Text-to-image and text-to-audio tasks pass expert-labelled recall and cultural-context checks; incompatible vector spaces cannot be compared. |
| F05 | todo | Generate and edit visual and audio creative outputs where rights and cultural review permit. | Generated work is marked creative, has inspectable cultural references, respects source and output rights, and passes user and expert review. |
| F06 | todo | Expand professional creative workflows, output formats and collaborative revision. | Target professionals complete recurring briefs with usable deliverables and traceable source context; user research validates priority. |
| F07 | todo | Institutional source submission, review, correction and revocation workflows. | A provider can submit and correct an exact revision; independent reviewers decide visibility and sensitive use; audit and withdrawal propagate to every modality index. |
| F08 | todo | Production object storage, index generation lifecycle, backups and scale tests. | Restore and full reindex reproduce approved search state; latency, cost and failure targets are measured on representative media collections. |

The owner accepted the current retrieval diagnostics for MVP engineering progress
and requested no further retrieval experiments. Server-side external-model
configuration and one live synthetic end-to-end journey are implemented. The
next work is G05 guardrails, C06/U04 and remaining quality and operations gates.
Cultural answer release still needs eligible source rights,
provider terms and support review; provisional page labels do not prove those
gates. F02–F08 are not silently discarded after M5; their product ordering
follows the concept's coverage, creative-domain and institutional-participation
axes.

## Integration order and parallelism

The synthetic mechanical vertical slice already uses vector retrieval, a fake
model adapter and a chat/citation path. The owner stopped further retrieval
ablations after reviewing the diagnostic results. Unreviewed extraction,
passage relevance and no-evidence calibration remain known release risks; the
external adapter can be wired and tested with synthetic content while its real
provider and source permissions are pending. Frontend and backend
owners must agree on OpenAPI before working in parallel; no two writing owners edit
the same contract file. An external model is connected only after the fake-provider
path, evaluation cases, and data-handling constraints exist.

## Research evidence and alternatives

- The original [RAG paper](https://arxiv.org/abs/2005.11401) motivates coupling
  retrieval with generation; it does not decide this product's chunking or store.
- [PostgreSQL full-text search](https://www.postgresql.org/docs/17/textsearch.html)
  supplies a local lexical baseline and ranking. Its Russian/multilingual and table
  performance must be measured on the actual corpus.
- [Qdrant named vectors](https://qdrant.tech/documentation/manage-data/vectors/)
  support modality-specific spaces, while its
  [filtering](https://qdrant.tech/documentation/search/filtering/) supports
  candidate selection. Current rights remain authoritative in PostgreSQL.
- [FastEmbed](https://github.com/qdrant/fastembed) provides local embedding
  inference; the chosen multilingual model remains a quality hypothesis.
- [pgvector](https://github.com/pgvector/pgvector#hybrid-search) is a considered
  vector alternative. This branch uses a dedicated Qdrant service.
- [BEIR](https://arxiv.org/abs/2104.08663) shows why retrieval needs heterogeneous
  evaluation; a project-specific labelled set remains necessary.
- [OWASP RAG Security](https://cheatsheetseries.owasp.org/cheatsheets/RAG_Security_Cheat_Sheet.html)
  treats retrieved documents as an untrusted input, and
  [OWASP File Upload](https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html)
  informs bounded, validated admin intake. These are design inputs, not evidence
  that the implementation is safe.

## Progress and decisions

- **2026-09-30, evidence-led retrieval study:**
  [The retrieval plan](retrieval-quality.md) records primary research, PDF-specific
  parser risks, held-out passage/locator gates and local GPU limits. An offline
  hash-checked Qdrant ablation compared E5-small, E5-large, BGE-M3 and quantized
  Qwen3-0.6B with fixed and token-bounded candidate passages. E5-large with the
  current 120-word baseline ranked all provisional relevant pages within five
  and had peak CUDA allocation of 1,137.6 MiB; every raw dense run returned
  candidates for all three no-evidence questions. Eight previously seen,
  agent-labelled page judgments cannot select an embedder, chunker or refusal
  threshold for release. In the E5-large run, a no-evidence question had top
  cosine 0.8262 while a supported question's relevant result scored 0.8165;
  one cutoff cannot separate even these cases. Local Docling inspection showed
  better reading order
  on a two-column article but figure OCR remained partial and erroneous; figure
  children retain a separate region contract in the offline study. Runtime
  chunking/model remain unchanged pending expert passage labels and parser
  coverage review. The three held PDFs stayed local and out of user/model flows.
- **2026-09-30, concept correction:** ADR 0006 superseded the SQL lexical
  retrieval default. Chat now requests locally generated multilingual embeddings,
  obtains Qdrant candidates and rechecks current exact-revision rights in
  PostgreSQL. A worker indexes approved revisions and cleans revoked points.
  A clean database upgrade and Alembic check passed. The live PostgreSQL/Qdrant
  suite passed 49 backend tests, including a paraphrased Russian query, stale
  held/revoked points, chat ownership and citation withdrawal. `make check`
  passed with Node 24: 40 backend tests without optional services, 14 frontend
  and six ML tests; Compose build, packaged model inference and smoke passed.
  This proves mechanics only. A frozen expert-labelled relevance comparison,
  representative corpus, robust index recovery drill, production security and
  media encoders remain open. The [index runbook](../../operations/vector-index.md)
  records replay and failure behavior.
- **2026-09-30, dense comparison:** the same three locally held PDFs and one
  explicitly synthetic table cell were run through Qdrant with local embeddings.
  Full-page embeddings recalled 0.70 of provisional relevant pages at k=5.
  Overlapping 120-word windows with page aggregation recalled 1.00, MRR@5 0.84
  and nDCG@5 0.848, compared with the earlier Russian SQL baseline recall 0.80.
  Raw dense no-evidence false-positive rate was 1.00. A cosine gate of 0.84
  selected on these same eight cases yielded observed 0.00 false positives and
  recall 1.00; this is training-set calibration, not expert or held-out quality.
  The gate is provisional and claim support remains a separate release check.
- **2026-09-30, missing-index recovery:** a missing Qdrant collection now fails
  chat search closed with HTTP 503. The worker clears stale completion markers,
  recreates that collection and replays approved revisions. A live missing-
  collection check passes; recovery of missing individual points still needs a
  separate drill. The complete live-service `make check` passed 49 backend,
  14 frontend and six ML tests.
- **2026-09-30, individual-point recovery:** an idle worker now audits one
  approved revision's exact segment IDs and revision payloads at a time. A
  missing point invalidates its completion marker; governed search fails with
  HTTP 503 until replay. A live PostgreSQL/Qdrant test deletes an individual
  point, observes the pending-index failure, and verifies replay. This is
  eventual detection, so audit cycle latency still needs monitoring at scale.
- **2026-09-30, candidate prefilter:** SQL now selects currently approved,
  scoped revision IDs before Qdrant ranking; Qdrant filters on an indexed UUID
  payload and SQL rechecks returned segments after ranking. A live test with
  120 closer held points proves the allowed passage survives the top-100
  candidate limit. Allowlist query size and latency still need corpus-scale
  measurement; it is not silently truncated.
- **2026-09-30, locator contract:** material details now carry the complete
  page/section/sheet/table/row/column locator. The previous adapter fabricated
  page 1 for a table-only segment; the API and frontend now preserve a missing
  page and display the sheet/cell location. Synthetic contract checks cover this
  path. C06 remains open because no table extractor or source format has been
  accepted yet. The live-service `make check` passes 50 backend, 15 frontend
  and six ML tests with synced OpenAPI.
- **2026-09-30, UI continuation:** removed the local demo chat adapter. User
  chats now use the persisted API for list, detail, send and delete; a failed
  send keeps the draft and request ID for retry. Citation buttons open the exact
  approved revision and segment with keyboard focus, and return to the chat.
  Frontend lint, build and 14 component tests pass. A live browser run against
  the rebuilt backend remains open.
- **2026-09-30, admin continuation:** admin upload, error/retry, exact revision
  review, explicit rights-scope approval and revocation controls now use the
  server API. A component check covers approval and withdrawal payloads with
  original-file and provider-transfer rights false by default. Live Compose
  review and upload remain open.
- **2026-09-30, retrieval baseline:** a clean PostgreSQL migration added the
  `russian` GIN expression index. The application retrieval service and SQL
  adapter apply current exact-revision, rights and sensitivity filters before
  ranking; tests prove held/revoked exclusion and immediate revocation on a
  synthetic corpus. A temporary local PostgreSQL evaluation compared `simple`
  and `russian` against the same eight provisional qrels. Recall@5 was 0.40 and
  0.80; no-evidence false-positive rates were 0.667 and 1.000. The Russian
  configuration was an interim engineering default, now superseded by ADR 0006.
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
- **Remaining M1 limits (earlier PDF checkpoint):** no rights-cleared real corpus, appointed review authority,
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
- **2026-09-30, synthetic CSV extension:** A narrow UTF-8 comma CSV with unique
  headers and a first-column row key now passes private intake, isolated parsing,
  exact cell storage, admin review, Qdrant indexing, material detail, permitted
  original download and immediate rights revocation. Empty interior cells preserve
  their original column number. A clean PostgreSQL migration and live API/vector
  test passed. This is a technical fixture only. C06 and S04 remain open for real
  cultural table comparison and XLSX/merged-cell semantics; no table quality
  threshold is claimed. See ADR 0003 and the format matrix.
- **2026-09-30, vector batch recovery:** The Qdrant adapter now writes 128
  points per batch and removes 256 IDs per batch. A 257-point live test forced
  a second-batch interruption and then verified idempotent replay and complete
  deletion. On a clean stack with no approved revisions, chat now receives an
  empty evidence set even before the Qdrant collection exists; approved but
  unindexed revisions still fail closed. Full checks passed with PostgreSQL
  and Qdrant (61 backend, 15 frontend, 17 ML tests). See ADR 0006.
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
