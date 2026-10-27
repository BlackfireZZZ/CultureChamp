# ADR0009: Governed local hybrid retrieval and direct context API

Status: accepted for implementation by the owner's27October2026 instruction.

## Context and evidence

The frozen expanded corpus study selected E5-small dense50 + Russian BM25S50,
deduplicated union≤100, BGE-reranker-v2-m3. New held-out results were47/50 Hit@5,
48/50 Hit@10, MRR.8277. The earlier top30 pipeline failed; its failure and all
labels remain in `ml/evals/heritage/`. The owner authorized server integration,
HTTP benchmark replay, main integration and local corpus expansion without LLM
calls. EPUB intake work was subsequently explicitly deferred; preserve the two
original EPUBs privately rather than introducing that upload format now.

Official [Sentence Transformers retrieve/rerank](https://sbert.net/examples/sentence_transformer/applications/retrieve_rerank/README.html)
separates efficient candidate retrieval and bounded pair scoring. Our pipeline
adds two first-stage pools and strict SQL visibility; library examples alone do
not enforce source rights. [Qdrant search](https://qdrant.tech/documentation/search/search/)
supports exact ranking and filters; exact mode reproduces this bounded study.
The existing ADR0006 prefilter and final authority rules remain mandatory.

## Decision

Use pinned local Sentence Transformers E5-small plus local BGE cross-encoder,
with verified safetensors hashes. Runtime inference is offline; a separate
explicit preparation command downloads only pinned public weights. CPU uses
FP32 and CUDA uses FP16; each has a distinct named Qdrant generation/model ID.
Old ONNX collections are retained, not compared to new vectors. Existing approved
indexer replays every approved revision whose model marker differs.

Build BM25 only from current scoped, included SQL segments with the matching
vector generation. Cache at most two exact visible(id,text) corpora per process.
Supply revision AND included-segment allowlists before Qdrant's50-candidate limit,
union with lexical50, and rerank at most100. Recheck SQL approval, sensitivity,
provider scope, tags, inclusion and generation AFTER reranking. No old cosine
cutoff/title boost applies; no calibrated absence-of-evidence claim is made.
Missing models, vector service or reranker fail503, without silent lexical fallback.
The legacy governed dense class remains for old diagnostic tests; application DI
uses the new shared hybrid implementation.

Add authenticated `GET /api/v1/materials/search` (user role), limit1..20, exact
locators/text/ranking scores, no-store. Chat retrieval uses the identical service.
This endpoint invokes neither generation nor a model-provider API. Existing chat
transport contracts remain compatible; OpenAPI/client snapshots are regenerated.

## Costs, limits and recovery

New runtime dependencies are isolated from batch code; Linux locked installations
use PyTorch's official CPU wheel index to avoid shipping CUDA libraries into a
CPU container. GPU replay uses the retained dedicated CUDA environment and states
its device. Docker sets bounded CPU thread counts; GPU timings are not CPU promises.
Model objects persist and serialize inference per process. Private weights are
separate from private source originals, under the same managed storage volume.

SQL lexical corpus materialization is O(visible text), and exact dense search is
linear at this corpus size. Measure API latency/query plan; change the strategy
before large corpus growth rather than truncating authorization allowlists.
No schema change is needed. Original files stay outside Git; approvals remain
attributed owner-authorized internal reuse, not invented expert validation.

Rollback code can select the retained old collection and reindex matching model
markers; do not compare new queries to old vectors. Never delete old source or
index volumes to roll back. User-requested worktree cleanup happens only after
main integration and preserving needed ignored data outside those worktrees.
