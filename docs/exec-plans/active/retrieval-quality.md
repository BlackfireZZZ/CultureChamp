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
4. **Benchmark local retrievers.** Compare E5-small, BGE-M3 and Qwen3-0.6B
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
