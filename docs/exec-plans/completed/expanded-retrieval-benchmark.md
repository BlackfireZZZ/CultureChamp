# Expanded local retrieval benchmark

Status: complete for the retrieval-only engineering study, 2026-10-27.

## Purpose and hypothesis

Find an inspectable local retrieval configuration for the owner's 19 PDFs and two
EPUBs without calling a generative model or remote inference API. Hypothesis:
Russian lexical normalization, dense retrieval and bounded fusion/reranking improve
passage retrieval over the existing E5-small 120/30-word windows.

## Context and ownership

Primary checkout: `/mnt/BlackfireZZZ/Hackatons/CultureChamp`, branch `main`, base
`0a760e5a97f05b0e18f1b48ba5d5aa0856ec611e`. Its initial dirty files were
`.env.example`, `docs/product/CONCEPT.md`, `frontend/src/index.css` and untracked
`docs/product/POST_MVP_ROADMAP.md`; preserve all four. Implementation worktree:
`/home/blackfire/.codex/worktrees/retrieval-corpus-benchmark/CultureChamp`, branch
`agent/retrieval-corpus-benchmark`, initially clean. The lead owns extraction, corpus/questions, documentation, experiment execution and integration.
The explicitly authorized retrieval_review subagent owns only
`ml/evals/heritage/runner.py` and `test_scoring.py`; it also provides upstream
research and read-only review. File ownership does not overlap.
The uncommitted concept was read as product context; no changes to it are required.
Existing study: `ml/evals/README.md`; runtime consumers found with `rg` in
`backend/app/infrastructure/db/vector_search.py`, `vector/text_vectors.py` and
`application/retrieval.py`. No batch imports may enter the online worker.

## Scope and non-goals

Move the supplied loose files into ignored private storage, preserving names and
hashes. Extract locally with physical PDF pages and EPUB spine-item locators.
Write source-grounded questions before retrieval runs, with immutable exact evidence
spans, source hashes and disjoint development/test question families. Compare
established open-source implementations and record versions, licenses, upstream
popularity and measured resource costs. External downloads may fetch code/weights;
no source text goes to external inference. No generation, automatic publication,
source approval, production database changes or unsupported claim certification.
A ranked hit is not proof that a claim is true. Labels are agent-authored engineering
judgments, not expert cultural validation. No unspecified legal ban is assumed;
the owner accepted local OSS/no remote APIs as the operational constraint.

## Acceptance frozen before experiments

- Every supplied source is hashed, extracted and represented by source-grounded questions.
- Supporting-span Hit@5 >= 0.90 and Hit@10 >= 0.95 on the frozen test split.
- MRR@10 >= 0.75; format slices Hit@5 >= 0.80.
- All annotated evidence offsets and returned locators resolve against exact hashes.
- Report evidence coverage for multi-span questions separately from any-hit success.
- Report warm query p50/p95, indexing duration, memory and index size.
- Record explicit unsupported questions as diagnostics; nearest-neighbor ranking
  alone cannot establish corpus-wide absence or safe abstention.
- Select on development only. Evaluate test once after configuration selection;
  if it fails, report failure and obtain a new independent test before claiming
  a subsequent held-out pass. Never silently move thresholds or relabel misses.

## Milestones and progress

1. Corpus and frozen evaluation contract — completed: 21 originals moved with hashes,
   195 units, 1,266,443 normalized characters, 2,073 fixed 120/30-word chunks.
   84 questions/42 evidence families frozen; SHA256
   `df6711df09a07af2ded745ef9cb10bf6ba9161583af54bba79d0ec232d9679b3`.
   Test has 21 families/42 queries; direct/paraphrase are correlated pairs.
   Separate six unsupported probes are diagnostics, not a corpus absence proof.
2. Baselines and comparable local retrieval configurations — completed.
   Initial development BM25 raw Hit@5=23/42; Russian stemming=33/42.
   Neither meets the frozen gate. No test results have been inspected.
3. Selection, verification, reproducible report and project-note update — completed.

## Research evidence and risks

- BM25S: https://github.com/xhluca/bm25s and https://arxiv.org/abs/2407.03618.
  Efficient sparse scoring; Russian morphology requires explicit preprocessing.
- Sentence Transformers: https://github.com/huggingface/sentence-transformers.
  Established local embeddings/cross-encoders; download and VRAM costs differ.
- BGE: https://github.com/FlagOpen/FlagEmbedding and
  https://huggingface.co/BAAI/bge-reranker-v2-m3 (Apache-2.0).
  Multilingual capability is not corpus-specific evidence.
- Qdrant: https://github.com/qdrant/qdrant; existing runtime index remains authoritative
  only after PostgreSQL visibility filtering. Offline exact vector search isolates
  model/chunk quality from approximate-index effects.

## Validation and recovery

Smallest falsifying check: remove or shift the gold evidence span and require the
fixture validator/scorer to fail. Exercise overlapping chunks and duplicate hits so
page/title matches cannot inflate passage scores. Run ML Ruff/mypy/pytest and the
repository full gate. Inspect diff for source originals/full extracted text/secrets.
Any unavailable required check must be recorded and escalated. Private files stay
in the primary checkout; worktree uses an ignored reference to that same directory.
Retain the branch and reports for review; moving originals is reversible via manifest.

## First held-out result and second round

V1 selected E5-small + BGE reranker top30 from development (41/42 Hit@5/10,
MRR .8321). The first frozen test improved from E5-small 28/42 Hit@5 to39/42,
but FAILED the unchanged gate: Hit@10 .9286<.95 and EPUB3/4<.80. Keep the
failure, labels and selection intact. Miss analysis found relevant spans at dense
ranks32 and48, and one outside dense50 but at lexical rank5. This motivates
preserving both first-stage top50 pools before reranking, rather than silently
relabeling a nearby hit or reducing acceptance.

Round2 explicitly reclassifies all84 exposed queries as development. A new
independent test was authored and frozen before union experiments:50 queries,
25 families (19PDF,6EPUB), including one two-span family. Every same-unit new gold
span lies>1000 normalized characters from old gold spans. Questions SHA256:
`a63e306afd1f156c0f59b4858fdb4056c44cc216914340c4dab0c9f7d3923e51`.
The thresholds and scorer are unchanged. Compare dense50, lexical50, RRF50 and
full deduplicated union≤100 before local BGE reranking; report candidate ceilings
and the larger latency explicitly. The new test is not used for configuration selection.

## Final observed outcome and integration

Round2 selected `union-e5-small-bm25-russian-rerank100` before test. First and
only held-out run passed unchanged point-estimate gates: Hit@5=47/50 (.94),
Hit@10=48/50 (.96), MRR@10=.8277; PDF36/38, EPUB11/12 at5. Both-style family
success is22/25 at5 and23/25 at10; confidence and provisional-label limitations
are explicit in `ml/evals/heritage/REPORT.md`. No additional tuning follows this
pass. Raw unsupported probes still receive neighbors; no calibrated abstention
or expert cultural validation was established.

`make check` passed: backend118 passed/20 opt-in integrations skipped,
frontend33 passed and built, ML38 passed, static/architecture/contracts/Compose
checks passed. The18 added counterexample tests run in the standard ML gate.
Independent read-only review checked metrics, split/offset integrity, commands,
source privacy and immutable pins. Fresh-query CLI smoke passed with93 unique
candidates; its excerpts were saved only under ignored private storage.

Verified changes are integrated into the primary checkout by checked patch/file
copy, with no code commit or push. The four pre-existing dirty files are preserved
by before/after hashes. Keep the worktree for its prepared private environment
and weights. Runtime/deployment and the approved-source database are unchanged.
The project Vault receives a separate durable result note; its synchronization
status is reported separately from local code.
