# Expanded heritage retrieval benchmark

The selected local pipeline passed the predeclared engineering gate on 50 new,
held-out query formulations. See [the measured report](REPORT.md),
[the frozen configuration](round2/selection.json), and
[questions with exact supporting spans](round2/questions.jsonl).

Originals live in the ignored primary-checkout directory
`.private/corpora/heritage-2026-10-27/raw/`. 19 PDFs and 2 EPUBs were moved there with
unchanged filenames and verified SHA256 values; the private inventory records
old paths for reversal. No original or full extracted text belongs in Git.
The shared corpus contains 195 page/spine units and 2,073 overlapping 120/30-word
passages. The offline experiment does not itself approve application sources. Server integration and the separately authorized PDF intake are documented in the operations runbook.

## Run a fresh query locally

The primary checkout links the retained environment and models stored under `/home/blackfire/.local/share/culturechamp/retrieval/`:

```bash
cd /mnt/BlackfireZZZ/Hackatons/CultureChamp
OMP_NUM_THREADS=4 MKL_NUM_THREADS=4 .private/benchmark-venv/bin/python \
  -m ml.evals.heritage.search \
  --store .private/heritage-2026-10-27 \
  --model-cache-dir .private/models --device cuda \
  --query 'Какие исторические медовые напитки готовили с травами?' --limit 5
```

The CLI uses the exact revisions in the selection file, performs local inference,
and prints source excerpts, original filenames, physical PDF pages or EPUB spine
members, normalized character offsets, candidate counts and relevance scores.
Scores are ranking signals, not probabilities of factual support. Keep redirected
stdout under `.private/`: it contains source text. All retrieval commands set
Hub offline mode and disable Hub telemetry before importing model libraries.
The warm benchmark timings exclude process imports, model loading and first
CUDA initialization; a one-shot CLI is slower.

## Reproduce on another checkout

Use Python 3.13, Poppler 24.02.0 (`pdftotext`) and the original private files whose
hashes appear in [the corpus manifest](manifest.json). Place them in
`$HERITAGE_STORE/raw/`; do not fetch copyrighted originals from this repository.
The recorded CUDA environment targets the local RTX 4070 Ti. CPU mode is available
with `--device cpu`, but GPU timings do not transfer to it.

```bash
uv venv .private/benchmark-venv --python 3.13
uv pip install --python .private/benchmark-venv/bin/python \
  -r ml/evals/heritage/requirements-lock.txt
# Set this to the directory containing raw/; it must stay private.
export HERITAGE_STORE=/absolute/path/to/private/heritage-2026-10-27
.private/benchmark-venv/bin/python -m ml.evals.heritage.corpus \
  "$HERITAGE_STORE" --manifest ml/evals/heritage/manifest.json
# Only this explicit preparation step downloads public model weights.
.private/benchmark-venv/bin/python -m ml.evals.heritage.download_models \
  --model-cache-dir .private/models --models e5-small e5-large bge-m3 reranker
```

The extractor prints statistics only. `--sample` explicitly requests bounded
private excerpts. No full-book read is needed to inspect the benchmark.
Different parser output fails the frozen normalized-corpus hash; investigate and
version a new dataset rather than silently accepting changed offsets.

Development experiment (all 84 V1 queries are exposed development data in round2):

```bash
OMP_NUM_THREADS=4 MKL_NUM_THREADS=4 .private/benchmark-venv/bin/python \
  -m ml.evals.heritage.runner --store "$HERITAGE_STORE" \
  --questions ml/evals/heritage/round2/questions.jsonl \
  --diagnostics ml/evals/heritage/diagnostics.jsonl \
  --output .private/retrieval-dev.json --split dev --stemmer russian \
  --models e5-small --model-cache-dir .private/models --device cuda \
  --union --rrf --rerank --rerank-top 100
```

Replay the frozen selected configuration and reference baselines:

```bash
OMP_NUM_THREADS=4 MKL_NUM_THREADS=4 .private/benchmark-venv/bin/python \
  -m ml.evals.heritage.runner --store "$HERITAGE_STORE" \
  --questions ml/evals/heritage/round2/questions.jsonl \
  --output .private/retrieval-test-replay.json --split test --stemmer russian \
  --models e5-small --model-cache-dir .private/models --device cuda \
  --union --rerank --rerank-top 100 \
  --selected-config union-e5-small-bm25-russian-rerank100 \
  --reference-config e5-small bm25-russian \
  --expected-questions-hash a63e306afd1f156c0f59b4858fdb4056c44cc216914340c4dab0c9f7d3923e51
```

This is now a replay of a published test, not another independent validation set.
A subsequent tuning round requires a newly frozen held-out set. Outputs contain
locator keys and measurements; original texts, embeddings and index caches stay
in private storage. Index caching is keyed by corpus, immutable model revision,
prefixes, context limit and dtype. Original source hashes and gold spans are
validated before measurements.

## Verification and boundaries

```bash
make ml-check
make check
```

The focused counterexamples cover corrupt originals, stale evidence offsets and
hashes, wrong pages, cross-split families, overlapping/duplicate chunks, EPUB
spine ordering, unsafe inference from raw neighbors, and truncated candidate
pools. Benchmark inference needs the separate environment above; unit tests do
not need model weights or a generative API.

The offline runner uses exact NumPy dot products. The server now implements the
selected dense50 + Russian BM25S50 union and BGE reranking with Qdrant exact
search, SQL authorization before pooling and a final SQL recheck. The authenticated
`GET /api/v1/materials/search` endpoint is independent of generation; chat shares
its retrieval service. [API parity](round2/api-parity.json) replays all 134 frozen
questions over frozen segments in isolated PostgreSQL/Qdrant, with no LLM calls.
This verifies integration parity, not an independent test or upload-parser parity.
EPUB extraction remains offline; EPUB intake was explicitly deferred by the owner.
See [runtime operations](../../../docs/operations/retrieval.md).

Labels are source-checked agent judgments, not independent cultural expert
validation. Every question targets known evidence; qrels are not exhaustive for
all alternative supporting passages. Scanned PDFs, OCR, full cultural correctness,
end-to-end generation and calibrated no-evidence rejection are outside this gate.
