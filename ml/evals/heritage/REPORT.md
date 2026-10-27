# Local retrieval study — 27 October 2026

The selected pipeline met every frozen engineering acceptance threshold on the first round-two held-out run: **47/50 Hit@5, 48/50 Hit@10, MRR@10 0.8277**. E5-small alone scored 42/50 Hit@5 on those same questions. No generative model or remote inference API was called.

## Corpus, source custody and labels

The owner supplied 19 PDFs and two EPUBs as loose files beside the repository. They were moved, without renaming or byte changes, to the primary checkout’s ignored `.private/corpora/heritage-2026-10-27/raw/`. SHA256 was checked after every move; the private inventory preserves original paths. The originals and complete extracted text remain outside Git. The existing application database and its approved-source corpus were not changed.

Poppler 24.02.0 text extraction plus local normalization produced 195 physical PDF-page/EPUB-spine units, 1,266,443 characters and 2,073 passages. EPUB members retain spine order and normalized character offsets; no PDF-style page numbers are invented for EPUBs. The 120-word windows overlap by 30 words and never join source units. Two rendered PDF pages were checked against extracted prose (S07 physical page 10 and S15 page 5); this is a sample, not a corpus-wide extraction audit. A rejected S12 sample showed column-order noise. OCR and scanned-only sources were not evaluated.

Labels were authored from bounded local source samples, before retrieval runs. The lead did not load entire books into chat context. Across rounds there are **134 unique answerable questions in 67 evidence families**, each with a direct and a paraphrased wording. Six deliberately unsupported probes are separate diagnostics. Each gold span records source hash, physical page/spine member, normalized start/end and an exact quotation. These are source-checked agent judgments, not independent expert judgments or exhaustive relevance labels.

## Frozen acceptance and scoring

Before the first experiment: supporting-span Hit@5 ≥ 0.90, Hit@10 ≥ 0.95, MRR@10 ≥ 0.75, and each PDF/EPUB Hit@5 slice ≥ 0.80. Returning the right title or page alone does not count. A hit requires a single returned chunk to cover at least 80% of a gold span in the exact immutable source unit. Union character coverage and all-evidence coverage are measured separately; duplicate/overlapping chunks cannot multiply covered characters. One new family contains two gold spans. No threshold or old gold label was weakened after a miss.

## Development comparisons and the failed first test

The original 84 questions were split into 42 development and 42 test queries, grouped by evidence family. All methods used the same extracted corpus. The dense stage uses normalized E5 query/passage prefixes or unprefixed BGE embeddings. Dense ranking is exact NumPy dot product, not an approximate-index/storage-engine comparison. BGE-M3 dense mode alone was tested; its sparse and late-interaction modes were not.

| V1 development configuration | Hit@5 | Hit@10 | MRR@10 | Warm p95, ms |
|---|---:|---:|---:|---:|
| `bm25-raw` | 0.548 | 0.595 | 0.452 | 0.2 |
| `bm25-russian` | 0.786 | 0.857 | 0.620 | 0.1 |
| `e5-small` | 0.690 | 0.810 | 0.598 | 5.5 |
| `rrf-e5-small-bm25-russian` | 0.881 | 0.881 | 0.670 | 5.7 |
| `e5-large` | 0.810 | 0.905 | 0.624 | 14.6 |
| `rrf-e5-large-bm25-russian` | 0.905 | 0.929 | 0.709 | 14.8 |
| `bge-m3` | 0.810 | 0.857 | 0.676 | 10.4 |
| `rrf-bge-m3-bm25-russian` | 0.905 | 0.905 | 0.721 | 10.5 |
| `bm25-russian-rerank30` | 0.881 | 0.881 | 0.768 | 113.3 |
| `e5-small-rerank30` | 0.976 | 0.976 | 0.832 | 119.8 |
| `rrf-e5-small-bm25-russian-rerank30` | 0.952 | 0.952 | 0.810 | 119.6 |
| `e5-large-rerank30` | 0.952 | 0.952 | 0.792 | 124.7 |
| `rrf-e5-large-bm25-russian-rerank30` | 0.952 | 0.952 | 0.798 | 124.0 |
| `bge-m3-rerank30` | 0.976 | 0.976 | 0.827 | 125.5 |
| `rrf-bge-m3-bm25-russian-rerank30` | 0.952 | 0.952 | 0.807 | 122.3 |

V1 selected E5-small + BGE reranker top-30 on development only (41/42 Hit@5/10). On the first held-out test it improved E5-small’s Hit@5 from 28/42 to 39/42, but **failed**: Hit@10 was 39/42 = 0.9286 and EPUB Hit@5 was 3/4 = 0.75. [The first selection](selection.json) and [failure report](test-selected.json) remain intact. Two needed spans were at dense ranks 32 and 48; another was outside dense top-50 but at lexical rank 5. Repeating or relabeling this test would not be independent validation.

## Round two: preserve both candidate pools

All 84 exposed V1 queries explicitly became development data. Before further inference, a new test was frozen: 50 queries / 25 families, including 19 new PDF families and three new families for each EPUB. Every same-unit new gold span is more than 1,000 normalized characters from development gold spans. The new qrels SHA256 is `a63e306afd1f156c0f59b4858fdb4056c44cc216914340c4dab0c9f7d3923e51`. This is unseen-query validation on the same corpus, not unseen-document validation.

| Round-two development configuration | Hit@5 | Hit@10 | MRR@10 | Warm p95, ms |
|---|---:|---:|---:|---:|
| `bm25-russian` | 0.821 | 0.881 | 0.640 | 0.1 |
| `e5-small` | 0.679 | 0.833 | 0.560 | 5.3 |
| `rrf-e5-small-bm25-russian` | 0.893 | 0.917 | 0.686 | 5.4 |
| `union-e5-small-bm25-russian` | 0.679 | 0.833 | 0.560 | 5.4 |
| `bm25-russian-rerank100` | 0.905 | 0.917 | 0.798 | 183.6 |
| `e5-small-rerank100` | 0.964 | 0.964 | 0.846 | 197.6 |
| `rrf-e5-small-bm25-russian-rerank100` | 0.976 | 0.976 | 0.852 | 194.5 |
| `union-e5-small-bm25-russian-rerank100` | 0.976 | 0.976 | 0.852 | 334.7 |

The selected union keeps dense top-50 and Russian-stemmed BM25 top-50, deduplicates them and reranks at most 100 with BGE-reranker-v2-m3. Union and reranked RRF top-50 tied on development (82/84 Hit@5/10, MRR 0.8516). Union was frozen before the new test to preserve the complete pools after the demonstrated candidate-truncation failure; its extra latency was accepted. This does not establish that union is superior to reranked RRF on unseen data: only the selected union and predeclared reference baselines were evaluated on the new test. Dense `rerank100` variants have at most 50 initial candidates; their actual pool counts are recorded.

## Final held-out result

| Configuration | Hit@5 | Hit@10 | MRR@10 | Warm p50 / p95 |
|---|---:|---:|---:|---:|
| `bm25-russian` | 41/50 (82%) | 43/50 (86%) | 0.6750 | 0.1 / 0.1 ms |
| `e5-small` | 42/50 (84%) | 43/50 (86%) | 0.6629 | 5.2 / 5.4 ms |
| `union-e5-small-bm25-russian-rerank100` | 47/50 (94%) | 48/50 (96%) | 0.8277 | 298.2 / 332.2 ms |

All frozen point-estimate gates passed. PDF Hit@5 is 36/38 (94.7%); EPUB is 11/12 (91.7%). All 50 questions’ gold evidence entered the pre-rerank pool (67–98 unique candidates), so the remaining errors are ranking errors. All-evidence Hit@5/10 equals 0.94/0.96, including the one two-span family; that single example cannot establish general multi-hop quality.

The paired wordings are correlated. Requiring both styles of each family to hit gives 22/25 families at top-5 and 23/25 at top-10; family-level MRR uses the worse wording and is 0.7087. The family Hit@5 Wilson 95% interval is approximately 0.700–0.958 (families treated as independent). The result meets the declared query-level engineering gate, not a statistical guarantee of population recall. New questions must be frozen for future tuning.

Remaining top-10 misses are `R2-S04-04-paraphrase` (the general nature-cult object list) and `R2-S21-25-paraphrase` (Aksakov’s older epic hero). Neither was relabeled or used for another tuning round. Several alternative passages can be useful but remain unjudged; metrics target the annotated evidence, not every relevant passage in the library.

## Resources, reproducibility and limits

- Selected run: RTX 4070 Ti 12 GiB; warm p50 298.2 ms, p95 332.2 ms. Timings include query encoding, lexical search, exact dense ranking, union and reranking; imports/model loading and tokenizer-audit overhead are excluded. A fresh one-shot CLI smoke took 6.59 seconds with imports, loading and first CUDA initialization.
- Measured selected-run peak CUDA allocation: about 1.20 GiB; reserved: 1.51 GiB. Host peak RSS: about 4.93 GiB. These process measurements are not concurrent production capacity estimates. Models were unloaded between benchmark stages; the inspection CLI also unloads the encoder before loading the reranker.
- Dense FP32 vectors occupy 3,184,256 bytes, lexical index 1,980,387 bytes, excluding weights, source text and metadata. The final run reused the vector cache; its sub-millisecond load is not fresh indexing time. The first E5-small vector build is recorded separately in `dev-dense.json`.
- No passage/query/pair exceeded the 512-token encoding limits in the selected run. Encoder and reranker model revisions, FP16 inference dtype, package versions, corpus and qrels hashes are recorded in the reports and selection.
- Raw nearest-neighbor ranking returned candidates for all six deliberately unsupported probes. No calibrated rejection mechanism was selected; relevance scores do not establish truth, absence of evidence, permission, or cultural appropriateness.
- No source files or full text were sent to an external service. Model-weight downloads were separate preparation; retrieval set Hub offline mode and telemetry opt-out before imports. No chat/generation endpoint was called.
- At the original offline-study delivery, the deployed backend was unchanged. Its E5-small ONNX O4 adapter, provisional cosine gate, title rescue, PostgreSQL visibility recheck and Qdrant API path are not equivalent to this PyTorch offline baseline. Preserve revision authorization and versioned index replay during any later integration.

## Established open-source components

Popularity snapshot: 27 October 2026, 00:05 MSK. Stars are a community-adoption signal, not quality evidence; the local benchmark selected the configuration. The owner accepted local OSS without external inference as the operational dependency constraint; no specific legal denylist was supplied. Permissive licenses alone do not certify jurisdictional status.

| Upstream | Observed GitHub stars | License / role |
|---|---:|---|
| [BM25S](https://github.com/xhluca/bm25s) | 1,816 | MIT; sparse scoring, Russian preprocessing supplied explicitly |
| [Sentence Transformers](https://github.com/huggingface/sentence-transformers) | 19,228 | Apache-2.0; local encoders and cross-encoder inference |
| [FlagEmbedding](https://github.com/FlagOpen/FlagEmbedding) | 12,278 | MIT library; BGE dense/reranker weights have their own licenses |
| [Qdrant](https://github.com/qdrant/qdrant) | approximately 35.3k | Apache-2.0; existing runtime, not a separately measured storage candidate |

The first three counts came from GitHub REST; Qdrant REST was rate-limited, so its rounded count came from the official repository page. Comparable implementations: [BM25S paper](https://arxiv.org/abs/2407.03618), [Sentence Transformers retrieve-and-rerank](https://sbert.net/examples/sentence_transformer/applications/retrieve_rerank/README.html), [BGE reranker model card](https://huggingface.co/BAAI/bge-reranker-v2-m3), [Qdrant hybrid tuning](https://qdrant.tech/documentation/search-tuning/how-to-tune-hybrid-search/), and [Hub offline/telemetry environment settings](https://huggingface.co/docs/huggingface_hub/en/package_reference/environment_variables). The BGE reranker weights are Apache-2.0. E5 model cards specify prefixes and MIT licensing: [small](https://huggingface.co/intfloat/multilingual-e5-small), [large](https://huggingface.co/intfloat/multilingual-e5-large). Russian stemming uses [PyStemmer/Snowball](https://github.com/snowballstem/pystemmer), MIT/BSD. None of these upstream popularity figures proves Russian cultural relevance.

## Verification and delivery

Implementation and non-overlapping subagent ownership, preserved user changes, base SHA and experiment decisions are in the [execution record](../../../docs/exec-plans/completed/expanded-retrieval-benchmark.md). Reproduction and a fresh-query CLI are in [README](README.md). Benchmark reports intentionally contain locator keys and measurements; originals, extracted corpus, model weights and full-text CLI results remain Git-ignored.

`make check` passed in the isolated worktree after the final implementation: architecture
boundaries, backend Ruff/mypy and 118 tests, frontend lint/typecheck plus 33 tests
and production build, ML Ruff/mypy plus 38 tests, OpenAPI/client contract check
and Compose configuration validation. Twenty backend integration tests skipped
without their opt-in service fixtures; no live generation call was used. The 18
new focused tests are included in `make ml-check`. Independent subagent review
confirmed the reported metrics, commands, pins, split integrity and privacy
boundaries. Two source-containing CLI smoke outputs stayed Git-ignored.

The verified source changes were transferred to the primary checkout as an
uncommitted patch/file copy after checking the same base SHA and non-overlapping
paths. The four pre-existing dirty user files were hash-checked before and after
integration. Code and source originals remain local; no project branch was pushed.
The worktree is retained because it holds the prepared experimental environment
and model cache needed for the documented immediate search command.


## Server integration (27 October 2026)

The selected union pipeline is now implemented in the server through the shared
retrieval service and authenticated generation-free materials search API. The old
ONNX/title-rescue/0.84 path is no longer the application default. SQL scope and
current authorization apply before candidate limits and again after reranking.
A new model/dtype collection separates vectors from the previous generation.

[Actual HTTP parity replay](round2/api-parity.json) used real authentication,
PostgreSQL, Qdrant and local CUDA models: development Hit@5 82/84, test Hit@5
47/50, Hit@10 48/50, MRR@10 0.8277; test HTTP p95 0.519 s. All returned locators
were checked and generation attempts remained zero. This reuses published labels;
it is not another unseen test. Frozen segment seeding isolates retrieval from
parser differences and does not establish EPUB upload support.

The Compose image uses CPU PyTorch. Its first authenticated FP32 search succeeded
but took 48.3 s; the redundant full CPU replay was stopped after this smoke.
Do not apply GPU latency to this deployment. See `round2/api-cpu-smoke.json`.
The clean container build and import smoke passed. The full gate passed: backend
126 tests (23 opt-in skips), frontend 33 tests/build, ML 38 tests, Ruff/mypy,
architecture, OpenAPI/client and Compose checks. Three additional live hybrid
SQL/Qdrant tests passed, including permission changes during reranking.

The owner subsequently requested integration into main, official PDF intake and
cleanup of merged worktrees, and explicitly deferred EPUB intake. This supersedes
the earlier uncommitted-delivery/worktree-retention status. Models and the CUDA
environment are retained outside worktrees; original documents remain private.
