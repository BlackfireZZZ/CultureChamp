# ADR 0008: Document visual search staging gate

Status: Accepted for a bounded engineering pilot; release quality remains unproven.
Date: 2026-10-02

## Context and falsifiable question

The present PDF path extracts text but misses labels inside figures. The local
audit of candidate PDF-02 physical page 7 found a map and legend whose labels
were absent from both plain PDF text and Docling body text; local OCR introduced
recognition errors. Candidate PDFs are absent from this checkout and remain local application data outside Git. The question is whether a
visual representation retrieves a relevant, precisely located region that the
current caption/neighbor-text path misses, at an acceptable latency and index
cost, without treating a visual match as evidence for a cultural claim.

## Comparable implementations and limits

- [Docling's document model](https://docling-project.github.io/docling/concepts/docling_document/)
  represents pictures, tables and page bounding boxes with provenance. It is a
  candidate for region discovery, but its output on the two-column PDF and map
  needs visual review. A bounding box from a parser is not verified semantics.
- [Qdrant named vectors and multi-representation search](https://qdrant.tech/documentation/tutorials-search-engineering/multi-representation-search/)
  allow separate vector spaces and query-time rank fusion. CultureChamp still
  needs PostgreSQL prefiltering and post-search review of exact revision publication state.
  Qdrant point payloads cannot authorize a result.
- [ColPali](https://proceedings.iclr.cc/paper_files/paper/2025/file/99e9e141aafc314f76b0ca3dd66898b3-Paper-Conference.pdf)
  retrieves rendered pages using many patch vectors and MaxSim. Its page-level
  ViDoRe results motivate a page baseline, but do not establish region precision,
  Russian cultural-document quality, or a workable CPU/index budget here.
  [Qdrant's multivector documentation](https://qdrant.tech/documentation/manage-data/vectors/)
  explains the index and scoring primitive.
- The compatible [CLIP text](https://huggingface.co/Qdrant/clip-ViT-B-32-text)
  and [vision](https://huggingface.co/Qdrant/clip-ViT-B-32-vision) ONNX ports
  make a cheap local region/page diagnostic possible. Their model cards describe
  English-oriented text embeddings. That is a mismatch for Russian queries and
  specialized motifs; no production choice follows from this probe.

## Synthetic diagnostic

`scripts/visual_retrieval_probe.py` makes a self-authored six-page raster PDF
with circles, triangles, stripes, a star and dots. It uses six English positive
queries and two unsupported queries. Manually supplied captions stand in for
source captions, so the text leg is deliberately incomplete. The text leg uses
the current pinned E5-small preprocessing; the other legs use a compatible
CLIP text encoder with either an image crop or a Poppler-rendered full page.
No cultural source or prompt enters the experiment.

On 2026-10-02, warm-cache local runs observed:

| Path | Recall@1 | Wrong top hits, six positives | Unsupported queries with a top hit | Encoding time, six documents plus eight queries | Raw float32 vectors |
|---|---:|---:|---:|---:|---:|
| E5-small captions | 4/6 | 2 | 2/2 | 0.97 s | 18,432 B |
| CLIP image regions | 6/6 | 0 | 2/2 | 1.09 s | 12,288 B |
| CLIP rendered pages | 6/6 | 0 | 2/2 | 0.17 s after the CLIP model and queries were loaded | 12,288 B |

The PDF was 119,220 B. In-memory rank computation took 0.014, 0.007 and
0.004 ms per query respectively. These timings omit model cold start, PDF
rendering, Qdrant network and persistent-index overhead; raw vector bytes are
lower bounds, not a Qdrant collection-size measurement. The dataset is tiny,
visually simple, English-only and tuned by construction. The unsupported-hit
rate means no path has an abstention rule. It cannot justify production
deployment or a cultural assertion.

An isolated Qdrant v1.16.3 collection with the pilot's 512-dimensional named
vector and indexed revision ID occupied 688 KiB of allocated container storage
when empty and 728 KiB after six synthetic points (`du -sk`), a 40 KiB delta.
The vectors alone are 12 KiB. The empty-collection overhead dominates this
small sample; sparse-file apparent size is much larger and was not treated as
allocated storage. This is a point-in-time six-item cost observation, not a
representative corpus forecast.

## Decision and implemented pilot

Keep ADR 0006's separate representations and authoritative revision checks.
Do not merge visual and text cosine scores. The pilot indexes embedded raster
images found in PDF pages with pinned CLIP text and vision ONNX snapshots, a
separate Qdrant collection and named vector, and a deterministic point ID from
revision/page/image ordinal. The private derived PNG has a SHA-256 storage key;
PostgreSQL binds it to the immutable revision and physical page. The worker
replays missing collections and audits point sets. It does not create captions,
OCR or cultural claims. The API returns a visual match and an authorized link to
the whole original PDF at the physical page; it makes no bounding-box claim.
The original route rechecks current authorization. Search requires currently
approved, sensitivity-cleared published original and user-text visibility before
ranking and again after ranking, with no excluded segments. A stale Qdrant
point cannot authorize a result. The UI labels matches as experimental.

This pilot deliberately excludes drawings that are only PDF vector commands,
page-layout-only matches, scan-only documents without a reviewable text layer,
and image formats outside approved PDFs. CLIP's English-oriented query encoder
is a known Russian-language risk. It is not connected to grounded chat or
provider transfer. No model-generated caption or OCR text is treated as fact.

## Next release gate

Before selecting that candidate, evaluate a source-like, locally supplied and
expert-labelled Russian document set with figures, photographs, drawings,
ornaments, diagrams, tables and scans. Record recall@k, false matches,
abstention, precise page/region accuracy, warm/cold latency, model memory,
rendering cost and actual Qdrant collection bytes. Run the same labels with
caption/neighbor text, compatible region embeddings and page render retrieval.
Only then choose region, page or combined rank presentation and set calibrated
abstention behavior. The current pilot API and synthetic diagnostic are
engineering evidence, not a human review or release gate.
