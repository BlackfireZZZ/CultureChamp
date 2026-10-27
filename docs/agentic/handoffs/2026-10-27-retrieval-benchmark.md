# Expanded retrieval benchmark handoff

Objective and actual status: completed local retrieval-only engineering comparison.
Selected union of E5-small dense 50 and Russian BM25 lexical 50, BGE-reranker-v2-m3
reranking up to 100. Round-two held-out Hit@5=47/50, Hit@10=48/50, MRR=.8277,
PDF 36/38 and EPUB 11/12 at 5. The first failed held-out test is retained.

Worktree / branch / base SHA:
`/home/blackfire/.codex/worktrees/retrieval-corpus-benchmark/CultureChamp`,
`agent/retrieval-corpus-benchmark`,
`0a760e5a97f05b0e18f1b48ba5d5aa0856ec611e`.
Primary path: `/mnt/BlackfireZZZ/Hackatons/CultureChamp`, `main` at the same base.
Integration uses a checked uncommitted patch/file copy; no code was pushed.

Owner of changed files: lead owns extraction, dataset, reports, documentation,
verification and integration; explicitly authorized subagent owned runner/scoring
tests and search CLI, with non-overlapping writes. Lead integrated and reviewed.

Changed contracts and files: `ml/evals/heritage/` adds hash-bound source/span
fixtures, local extraction, benchmark and fresh-query CLI, pinned download helper,
requirements snapshot and measured reports. `Makefile` includes the new tests;
root/eval READMEs link the study; completed plan records gates and failed test.
No runtime/API/database contract changed. Original files stay in ignored private
storage; the private inventory records all old paths and exact hashes.

Decisions and supporting evidence: complete corpus, samples, variants, frozen
selections, measured results and caveats in `ml/evals/heritage/REPORT.md`; commands
in its README. New qrels were frozen before each round, with family isolation.
Reranked RRF50 tied union100 on development; union preserves full candidate pools
at accepted extra latency. No unseen-test superiority over RRF is claimed.

Verification commands and observed results: `make check` passed, including 118
backend tests (20 opt-in integration skips), 33 frontend tests/build and 38 ML/eval
tests plus static/contract/Compose gates. `git diff --check` and private-source
hash/ignore scans passed. Independent review found two stale prose/link details,
which were corrected. Fresh-query union CLI smoke passed; excerpts stayed private.

What remains unverified and why: expert judgments, exhaustive alternative qrels,
scans/OCR, calibrated unsupported-query rejection, full API-path latency and
runtime integration were outside this retrieval-only comparison. E5 baseline
uses PyTorch FP16, unlike runtime ONNX O4 and its gate/title heuristic.

Risks and open questions: agent-authored paired query styles are correlated;
family Hit@5 is 22/25, with a wide interval. Index authorization still belongs to
PostgreSQL. Model scores do not establish truth or source permissions.

Exact next step: use the documented local CLI for fresh context inspection.
For runtime adoption, preserve visibility rechecks, version the index and compare
the actual API path; any new tuning needs a newly frozen independent question set.

Cleanup completed or retention reason: loose originals moved with hashes;
full text/models/smoke outputs ignored. Retain worktree for prepared dependencies
and model cache. Preserve the user's `.env.example`, concept, frontend CSS and
untracked post-MVP roadmap. Project code remains local and uncommitted.
