# Local hybrid retrieval operations

The shared server search service uses pinned E5-small dense top 50, Russian BM25S
top 50, deduplication and BGE cross-encoder reranking of at most 100 candidates.
See ADR 0009 and `ml/evals/heritage/REPORT.md` for measured selection and limits.
No generative model is involved in search or model provisioning.

`docker compose up -d --build` runs `retrieval-prepare` before backend and worker.
That explicit preparation downloads public pinned safetensors and tokenizer files
into the private shared volume, verifies weight hashes, and never uploads corpus
content. Inference uses only local files and disables Hub telemetry. Existing
provider settings are unchanged. Keep the private volume across restarts.

CPU is the Compose default (`RETRIEVAL_DEVICE=cpu`, four numerical threads).
The first measured CPU search took 48.3 seconds. GPU HTTP p95 0.519 seconds was
measured on a host CUDA environment, not in this CPU image. A CUDA deployment
needs matching PyTorch/CUDA dependencies and GPU access; setting the device alone
does not add CUDA support to the CPU image. Model caches are configured with
`RETRIEVAL_MODEL_CACHE`; no cache/model failure silently falls back to old search.

Approved indexing automatically replays revisions missing the current model ID.
Collection/model IDs include implementation and dtype; retain the old collection
for rollback. To roll back, restore the previous application image/configuration
and its corresponding collection; never mix old vectors with a new model marker.
Current SQL approvals, text scope, sensitivity, inclusion, people and region
filters are authoritative before pooling and are rechecked after reranking.

Authenticated `GET /api/v1/materials/search?q=...&limit=5` returns source locators,
text and ranking scores with `Cache-Control: no-store`. Optional `region` and
`people` filters apply to both candidate pools. Pending indexes or missing local
models return 503. Scores are not confidence estimates; unsupported queries can
still return neighbors. This endpoint and chat use the same retrieval service.

## Supplied corpus intake

Originals stay under `.private/corpora/heritage-2026-10-27/` in the primary
checkout. Never stage originals, extracted books, credentials or receipts.
`ml.evals.heritage.load_corpus` uploads the inventoried PDFs using official admin
HTTP APIs, polls the worker, downloads and hashes originals, then records the
owner-authorized internal approval. Metadata preserves source titles and evidence
URLs; owner authorization is not public licensing or expert cultural validation.
EPUB intake was explicitly deferred; both originals remain private.

```bash
.private/benchmark-venv/bin/python -m ml.evals.heritage.load_corpus \
  --base-url http://127.0.0.1:8000 \
  --store .private/corpora/heritage-2026-10-27 \
  --metadata ml/evals/heritage/source_metadata.json \
  --credentials /absolute/private/intake-credentials.json \
  --output .private/corpora/heritage-2026-10-27/intake-main.json
```

Credentials JSON contains `username` and `password` and must be private. The
importer verifies every input hash before mutation and is idempotent by uploaded
hash. A second run verifies reuse rather than duplicating sources; it refuses to
silently reapprove a revoked source. It does not seed SQL or call generation.
The benchmark API replay is separately isolated and seeds frozen segments;
application intake uses the normal upload/worker/approval/indexing workflow.
