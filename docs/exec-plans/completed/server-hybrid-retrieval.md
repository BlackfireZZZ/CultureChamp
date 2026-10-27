# Server hybrid retrieval and API replay

Status: complete. Lead owns integration, SQL search, API, dependencies, replay
and docs. Explicitly authorized subagent owns only new local model/BM25 adapters
and their focused tests. Existing benchmark worktree is reused:
`/home/blackfire/.codex/worktrees/retrieval-corpus-benchmark/CultureChamp`, branch
`agent/retrieval-corpus-benchmark`, base
`0a760e5a97f05b0e18f1b48ba5d5aa0856ec611e`. It contains retained prior-task
uncommitted benchmark changes. Primary checkout has those same changes plus the
owner's `.env.example`, product concept, frontend CSS and untracked roadmap;
preserve all. No force/reset/clean or production corpus test writes.

## Purpose, contract and falsifiable hypothesis

The user authorized implementing the selected pipeline and testing it via API,
without calling any LLM. New server default: pinned E5-small dense50 + Russian
BM25S50, deduplicated union≤100, pinned BGE cross-encoder reranking. The source of
truth is `ml/evals/heritage/round2/selection.json`; runtime code must not import
ML/batch code. Existing PostgreSQL current decisions, scope, sensitivity and
segment inclusion remain authoritative. The first falsifying check is a lexical
rank5/dense-tail candidate surviving to reranking, while a revoked or excluded
candidate cannot be returned even if its vector/reranker score is highest.

Consumers located with `rg`: chat DI in `api/routes/chats.py`, durable indexing
in `infrastructure/vector/indexing.py` and ingestion worker, vector governance in
`db/vector_search.py`, source APIs and tests, configuration, Docker/Compose,
OpenAPI/frontend generated client. Changes are additive to the public API.

## Scope and acceptance

- Add authenticated text-search API independent of generation; chat uses the same
  service. No chat/generation request or external model-provider call in replay.
- New named vector generation for new encoder implementation/dtype/preprocessing;
  approved indexing is replayable and old collection remains recoverable.
- Fetch lexical corpus only from currently eligible included SQL segments, apply
  filters before candidate limits, then recheck rights after local reranking.
  Missing vectors/models/reranker fail503; no silent lexical fallback or old .84
  score gate. Scores rank evidence; no calibrated abstention claim is introduced.
- Replay all134 frozen questions and six diagnostic probes through actual HTTP,
  real authenticated sessions, PostgreSQL and Qdrant on isolated local resources.
  Seed the frozen extracted passages exactly (not a new PDF/EPUB ingestion claim).
- On the existing50-question test replay retain Hit@5≥.94, Hit@10≥.96, MRR@10≥.80,
  PDF/EPUB Hit@5≥.80; preserve span/hash locators. This is API parity verification,
  not another unseen-question study or permission to retune labels.
- Test revocation during reranking, segment inclusion, provider/people/region
  filters, pending index behavior, authorization and dependency failure. Measure
  HTTP p50/p95 separately from offline timings; record CPU/GPU and cold costs.
- Run backend/full checks, contracts, focused live SQL/vector checks, clean build
  and runtime smoke where affected. Required unavailable checks are escalated.

## Research and decision

Reuse established implementations measured by the prior study. Official
[Sentence Transformers retrieve/rerank](https://sbert.net/examples/sentence_transformer/applications/retrieve_rerank/README.html)
uses a bounded first stage followed by local CrossEncoder relevance scoring.
[Qdrant search](https://qdrant.tech/documentation/search/search/) supports filtering
and exact search; preserve the SQL revision prefilter and authoritative final
recheck required by ADR0006. [PyTorch installation](https://pytorch.org/get-started/locally/)
distinguishes CPU/CUDA builds; pin and document actual runtime, not GPU benchmark
latency as a CPU promise. The new ADR records dependency/index/recovery costs.

## Milestones

1. Runtime adapters, governed fusion and additive endpoint — complete.
2. Isolated HTTP API corpus replay and authorization regressions — complete.
3. Full gate, build/smoke, integration and durable project-note update — complete.

## Recovery and retention

Keep original source corpus and live `culturechamp_usertest` volumes untouched.
Use a uniquely named isolated Compose database/vector project and loopback API;
no exposed credentials in logs or reports. Retain failed/diagnostic reports with
only query IDs and locator keys. Preserve old collection until chosen generation
is replayed; no schema migration is currently expected. Retain private models outside worktrees for reproducibility; report exactly what was actually restarted.


## Final owner steering

EPUB intake was explicitly deferred. Preserve both originals privately and import
only the 19 PDFs through the existing official workflow. Integrate into main,
preserve the four pre-existing owner changes, and remove merged worktrees only
after checking ancestry and local status. The original model provider remains
untouched and no LLM endpoint is called.


## Observed delivery

See `docs/agentic/handoffs/2026-10-27-server-hybrid-retrieval.md` for measured
HTTP parity, final checks, official 19-PDF intake and idempotence, deployment,
scoped main integration and safe worktree retention. The main source corpus now
contains the existing four plus 19 PDFs, indexed with the new CPU generation.
