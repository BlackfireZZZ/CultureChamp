# Retrieval quality before generation

Status: in_progress. Owner: integration agent. Base: `agent/integration-backend`
at `09c6c893dd9f7bd9d4a966de1eb552d2b5807a5f` in the isolated
`CultureChamp-integration-backend` worktree; initial `git status --short` was
clean. The primary checkout remains at `f67a0586f55e4bf3aa5192628d95a0d0cb527096`.

## Objective and falsifiable hypothesis

Choose a reproducible retrieval pipeline for Russian academic and heritage PDFs
before enabling a generative provider. The current 120-word/30-word overlapping
window and multilingual-E5-small index are a baseline, not a quality decision.
The hypothesis is that preserving reading order and document structure, then
using model-token-aware passages and a stronger multilingual retriever, improves
the retrieval of exact supporting passages without increasing unsupported-query
false positives or losing source locators. It fails if expert-labelled held-out
recall, ranking, or locator accuracy do not improve within measured latency,
memory, and index-size budgets.

## Corpus-specific risks

- PDF-01/02 are Russian scholarly prose with titles, citations, references,
  printed page numbers, headers, footnotes, and line-wrap hyphenation.
- PDF-03 is two-column and has parallel Russian/English front matter. Its
  `pypdf` extraction has no paragraph breaks; raw newlines are visual lines.
  Sentence or paragraph chunking on that text alone would encode layout errors.
- PDF-02 contains a map with embedded legend text. Both text-layer parsers omit
  those visual labels from running prose; local OCR yields partial, erroneous
  figure children. This requires a separate figure-region review path.
- The current eight provisional queries include named peoples and Bikin,
  contested historical interpretation, three no-evidence/sensitive cases, and
  one explicitly synthetic table cell. They are too small and were used to tune
  the current cosine gate; they cannot select a release configuration.
- A retrieval hit must resolve to a single immutable revision and inspectable
  source location. For multi-page passages, every page/span needs a locator;
  a fabricated page or silently joined column fails acceptance.

## Evidence and comparable implementations

| Source | Relevant finding | Difference and risk here |
|---|---|---|
| [Docling technical report](https://research.ibm.com/publications/docling-technical-report) and [document model](https://docling-project.github.io/docling/concepts/docling_document/) | PDF layout, reading order, tables, and provenance are represented separately from plain text. | Validate its output visually on our two-column page and footnotes; do not assume a converter is accurate on the held PDFs. |
| [Docling HybridChunker](https://docling-project.github.io/docling/concepts/chunking/) | Splits a hierarchy with the embedding tokenizer, merges compatible small sections, and repeats table headers. | Use as a candidate, not a universal optimum; preserve exact PDF spans and table cells in our own contract. |
| [Document Segmentation Matters, ACL 2025](https://aclanthology.org/2025.findings-acl.422/) | Boundary choice changes retrieval and QA results; fixed lengths can split related evidence or dilute a short fact. | Its open-domain results do not establish a best size for Russian ethnographic prose. |
| [Late Chunking](https://arxiv.org/abs/2409.04701) | Long-context token encoding before chunk pooling can preserve context; the paper also reports cases where naive chunks are comparable or better. | Evaluate only after correct reading order and with a compatible long-context encoder. |
| [BGE-M3 paper](https://arxiv.org/abs/2402.03216) and [model card](https://huggingface.co/BAAI/bge-m3) | Multilingual 1024-dimensional embeddings, up to 8192 tokens, and dense/sparse/late-interaction signals; its authors recommend hybrid retrieval and reranking. | Language coverage is not proof of quality on our communities, names, and historical material. |
| [Multilingual-E5-large model card](https://huggingface.co/intfloat/multilingual-e5-large) | The same query/passage prefix family as the current small model, 1024 dimensions and a 512-token input limit; the authors report stronger Russian Mr.TyDi ranking than E5-small. | A same-family capacity increase is a cleaner model ablation than changing training family; benchmark local passages and GPU memory rather than inheriting the public score. |
| [Qwen3-Embedding-0.6B model card](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B) | 0.6B parameters, 1024 dimensions and long context with task instruction format. | Compare exact model preprocessing and measured VRAM on the local 12 GiB RTX 4070 Ti; do not assume longer input should replace passage search. |
| [Qdrant hybrid guidance](https://qdrant.tech/documentation/search-tuning/how-to-tune-hybrid-search/) | Compare dense and sparse legs before RRF/DBSF fusion; candidate depth and scoring depend on the collection and labels. | Keep PostgreSQL rights checks authoritative after retrieval; fusion must not become a rights bypass. |

## Ordered implementation and gates

1. **Freeze evaluation contracts.** Add page- and passage-level judgments with
   exact hashes, spans, reviewer identity and uncertainty. Cover Russian names,
   transliteration, two-column passages, references/footnotes, table lookups,
   conflicting accounts, and unanswerable/sensitive requests. Split by question
   family and source before tuning. Current labels remain diagnostic only.
2. **Audit extraction.** Compare the existing parser and a layout-aware
   candidate on representative pages of each held PDF, using the unchanged local
   files. Record reading-order, heading, table and footnote errors, runtime and
   memory. Do not expose held text to users or a remote provider. A human checks
   a rendered page against extracted reading order before approval.
3. **Benchmark passage construction.** Keep the 120/30-word baseline. Try
   hierarchy/paragraph-aligned chunks bounded by the exact embedding tokenizer
   at predeclared budgets (e.g. 256/512 tokens), plus parent context returned
   after child retrieval. Keep page/cell provenance and measure truncation,
   index expansion, passage relevance and duplicate overlap. Late chunking is
   an optional measured candidate, not the default.
4. **Benchmark local retrievers.** Compare E5-small, E5-large, BGE-M3 and Qwen3-0.6B
   dense search on the same extracted corpus, queries and candidate depth.
   Measure peak GPU memory and latency. Test sparse and dense+sparse fusion
   separately for exact names/toponyms; rerank only a bounded candidate set.
   Use versioned Qdrant collections and model snapshots; no score threshold
   transfers between models.
5. **Select and integrate.** Require expert-held-out Recall@5/10, nDCG@10,
   no-evidence false-positive rate, locator accuracy, rights/revocation checks,
   p50/p95 latency, peak VRAM, and bytes per indexed source. Roll out with a
   replayable new index generation. Keep the current runtime active until this
   gate is met; do not enable generative claims from provisional retrieval.

## Current observations and blockers

The local GPU reports 12,282 MiB total and 11,126 MiB free at plan creation;
available VRAM changes with other workloads. The three PDFs may be processed
locally for internal validation per the owner's instruction. Expert review,
rights-cleared user release, real table material and provider transfer remain
separate external decisions. A preliminary result from eight agent-labelled
questions is only an engineering diagnostic, never release evidence.

The offline study runner now verifies fixture hashes, indexes each candidate in
a disposable Qdrant collection, and writes only locator keys and measurements.
The first ablation holds multilingual-E5-small and `pypdf` constant: fixed
120-word windows yielded Recall@5 1.00 and nDCG@5 0.848; sentence-aligned
256-token windows yielded 0.90 and 0.867; 384-token windows yielded 0.70 and
0.765. With Docling extraction, fixed 120-word windows yielded 0.90 and 0.695;
layout-block 256-token windows yielded 0.90 and 0.775. The study ranks pages by
their highest-scoring child chunk, so strategies with more chunks also get more
chances to score; these page-level labels cannot establish which individual
passage supports a claim. Raw no-evidence
false-positive rate was 1.00 in every run: every query received a nearest
neighbor. The observed score of 0.84 in the existing E5 gate was tuned on the
same eight questions and must not be transferred to another model or parser.

Holding `pypdf` and fixed 120-word windows constant, the local INT8
Qwen3-Embedding-0.6B-Q CPU run yielded Recall@5 0.90 and nDCG@5 0.816; BGE-M3
FP16 on CUDA yielded 0.60 and 0.627. BGE-M3 peaked at 1,149.7 MiB CUDA
allocated (1,250.0 MiB reserved), so it fits the available GPU, but size and
fit alone do not justify replacing E5. Qwen's model version is
`af95f2c416ffe9379369ad64f9113e865db6112c`; BGE-M3's is
`5617a9f61b028005a4858fdac845db406aefb181`. This compares only dense
vectors, not BGE-M3's sparse/late-interaction modes or a reranker. The small,
already-seen query set cannot rank the models for release.

Multilingual-E5-large FP16, snapshot
`3d7cfbdacd47fdda877c5cd8a79fbcc4f2a574f3`, is a promising same-family
candidate: with `pypdf` and fixed 120-word windows it yielded Recall@5,
MRR@5 and nDCG@5 of 1.00 on the eight provisional cases; peak CUDA allocation
was 1,137.6 MiB. Its sentence-aligned 256-token run yielded Recall@5 1.00,
MRR@5 0.90 and nDCG@5 0.915. Docling extraction with the same fixed windows
yielded Recall@5 1.00, MRR@5 0.74 and nDCG@5 0.766; Docling layout-block
256-token windows yielded 0.90, 0.90 and 0.862. These are neither held-out nor
passage-level judgments. The no-evidence false-positive rate remains 1.00
without a separately calibrated abstention mechanism. Keep E5-large as a
candidate, not a production decision.
The score diagnostic makes this concrete: one unsupported motif question had
top cosine 0.8262, while a supported editorial question had a relevant top
score of 0.8165. No single score cutoff separates even these two cases without
an error. Query-level evidence classification and claim/passage verification
must be evaluated separately; the E5-small 0.84 cutoff cannot be reused.

Visual inspection of PDF-03 physical page 2 found that Docling placed left-column
body blocks before right-column blocks and separated page furniture, unlike the
flat `pypdf` text. This is a one-page parser check, not a corpus-level extraction
pass. The custom layout-block windows are an ablation inspired by Docling's
document model; they do not implement or claim to reproduce `HybridChunker`.
Across all 32 pages, a naive whitespace word-count comparison of the `pypdf`
output and Docling body output found ratios of 0.75–0.96 on PDF-02 and
0.89–0.97 on PDF-01/PDF-03. This is **not** a valid content-coverage metric:
`pypdf` inserts whitespace around punctuation and retains line hyphenation,
while Docling normalizes them and removes page furniture. Direct inspection of
PDF-02 physical page 7 showed the same running prose and caption in both
outputs. A real coverage audit must align normalized character sequences and
visually sample unmatched regions before claiming loss or gain.

That page also has a map with small labels and a legend inside the figure.
Neither the `pypdf` text output nor Docling body output with OCR disabled
contains that figure text. A one-page local Docling EasyOCR run in
`layout_regions` mode produced four text items attached as children of the
picture, rather than body text; `full_page` produced six. Visual inspection
found recognition errors in both, including map-zone labels. The body-only
ablation intentionally excludes these picture children. Figure regions need a
separately evaluated OCR/visual representation and region locator, followed by
inspection against the source image. Neither parser/OCR mode can be treated as
ground truth for those details.
The next gate is expert-confirmed passage-level relevance and locator judgments,
including a held-out split, before any production chunking or model switch.
