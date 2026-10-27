# Server hybrid retrieval delivery

## Outcome and contracts

The server implements the frozen E5-small dense50 + Russian BM25S50 union and
BGE-reranker-v2-m3 pipeline. Authenticated materials search is additive and does
not call generation; chat shares the retrieval service. Current SQL rights,
provider scope, sensitivity, included segments and metadata filters apply before
candidate limits and again after reranking. Index generations distinguish model,
implementation and dtype. Old collections remain available for rollback.

The owner explicitly deferred EPUB intake. Both EPUB originals remain in private
storage and remain represented in the offline/frozen-segment benchmark. No EPUB
upload path was added. All 19 supplied PDFs were loaded into the main local stack
through official upload, worker extraction, download/hash verification and
approval APIs. A repeat imported zero new sources and reused all 19. The existing
four sources remain; all 23 revisions have the new FP32 index marker. Original
files, source-containing receipts and temporary credentials are excluded from Git.

## Evidence

- `make check` passed on primary: architecture, backend Ruff/mypy and 128 tests
  (23 service opt-in skips), frontend lint/typecheck, 33 tests/build, ML 38 tests,
  OpenAPI/client and Compose configuration. A later cache-completeness regression
  passed with the adapter tests (11 total); focused Ruff and mypy passed.
- Three live hybrid HTTP tests separately passed against real PostgreSQL/Qdrant,
  including final revocation/exclusion rechecks and filtering before pooling.
- `round2/api-parity.json`: all 134 frozen questions plus six diagnostics replayed
  through real authenticated HTTP with real local GPU models and SQL/Qdrant.
  Test Hit@5 47/50, Hit@10 48/50, MRR@10 0.8277, HTTP p95 0.519 s; locator checks
  passed and generation attempts stayed zero. This is published-benchmark parity,
  not an independent test, parser parity or calibrated unsupported-query rejection.
- Clean Docker build and CPU import smoke passed. The main backend and ingestion
  worker were rebuilt/restarted, preserving database, vector and private volumes.
  Repeated preparation verifies the complete local cache without public downloads.
- CPU isolated first-query smoke: 48.3 seconds. The main CPU API smoke returned
  five results with correct no-store headers in 54.6 seconds. Original hashes and
  approvals of the four pre-existing sources were verified; generation count
  stayed at 17 before/after. Temporary intake/smoke accounts were deactivated
  and sessions revoked. See `round2/main-intake.json`. Full redundant CPU replay was stopped;
  GPU timing is not a CPU deployment promise. See `api-cpu-smoke.json`.
- Independent read-only review found no authorization/integration blocker. Its
  incomplete-cache recovery finding was fixed by requiring tokenizer/config,
  encoder modules/pooling and pinned weight hashes before skipping provisioning.

## Integration and retention

Primary path: `/mnt/BlackfireZZZ/Hackatons/CultureChamp`; base
`0a760e5a97f05b0e18f1b48ba5d5aa0856ec611e`. Implementation used isolated branch
`agent/retrieval-corpus-benchmark` in the attached retrieval worktree. Adapter/test
and review ownership were non-overlapping. Verified task files were copied into
primary and committed as a scoped main integration; four pre-existing owner files
were hash-checked and excluded: `.env.example`, `docs/product/CONCEPT.md`,
`frontend/src/index.css`, `docs/product/POST_MVP_ROADMAP.md`.

Models and the CUDA benchmark environment were moved to
`/home/blackfire/.local/share/culturechamp/retrieval/` and linked from primary.
The original corpus remains under primary `.private/corpora/heritage-2026-10-27/`.
The app archive action remained queued, so a recoverable snapshot was committed
on `agent/retrieval-corpus-benchmark` (`c2c59f6`) and the now-clean retrieval
worktree was removed with Git after main integration. Seven other clean
worktrees whose HEADs are ancestors of main were removed without force. The
remove-brief and architecture worktrees contain unfinished changes and are
preserved under the repository prohibition on removing dirty worktrees. The
access-model worktree is not merged; a missing locked checkout registration is
also preserved. No force, reset or clean was used.

## Remaining limits

Slow CPU reranking needs a measured deployment decision. New tuning requires new
held-out questions. Unsupported-query rejection and independent expert cultural
review remain outside this benchmark. EPUB intake is deliberately deferred.
See `docs/operations/retrieval.md` for recovery and official corpus intake.
