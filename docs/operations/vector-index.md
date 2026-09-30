# Text vector index operations

The current text slice uses Qdrant collection `culture_text_e5_small_v1` and
`intfloat/multilingual-e5-small` embeddings, restricted to model snapshot
`614241f622f53c4eeff9890bdc4f31cfecc418b3` and ONNX O4 weights SHA-256
`4654c156f3e4171abc9c716cdb771bf9116455d15ac1aab364aeeede0e3205b0`.
The named vector is
`text_e5_small_v1` with 384 dimensions. Original files and citation text stay in
private storage and PostgreSQL, respectively. The vector index contains segment
UUIDs and revision UUID payloads; PostgreSQL makes every current access decision.
The collection has a `uuid` payload index on `revision_id`. Search selects
approved, scoped revision IDs in PostgreSQL and filters Qdrant candidates by
those IDs before ranking; it rechecks the returned segments in PostgreSQL.
An existing collection missing the payload index makes search unavailable until
the worker creates it. The allowlist is never truncated, so query size and
latency must be measured as the approved corpus grows.

## Normal indexing

After an exact revision is approved, the ingestion worker finds revisions without
a matching `source_vector_indexes` record, embeds their text segments and upserts
the points. A complete upsert is followed by the database record. Repeating the
job is safe because point IDs are stable segment IDs. Approval may briefly make
chat search return HTTP 503 until the worker has indexed the revision. This is an
explicit unavailable state, not an empty evidence answer. Revocation takes effect
in PostgreSQL immediately; the worker then removes its points from Qdrant.

The model is downloaded locally by FastEmbed on first use. The Compose
`source_private` volume stores the model cache under
`/workspace/.private/embedding-cache`. The model download transfers no source
content. An offline deployment must preseed this cache with the pinned model
weights and verify the model hash before accepting approved content.

## Rebuild after index loss or model change

If the Qdrant collection is missing, search returns HTTP 503. The worker detects
that loss, clears completed-index markers, recreates the collection and replays
approved revisions. Search stays unavailable while approved revisions lack
markers. During idle cycles the worker also audits one approved, indexed revision
at a time. It retrieves its exact segment IDs and revision payloads from Qdrant
without vectors. A missing or mismatched point invalidates that revision's SQL
completion marker; search returns HTTP 503 until the next worker pass upserts
the revision again. The audit cursor wraps across revisions and is reset on worker
restart. Detection time grows with the number of indexed revisions, at roughly
one revision per two seconds while the worker is idle. Monitor this lag at scale;
the audit is not an immediate guarantee against partial point loss. Qdrant's
[retrieve-points API](https://api.qdrant.tech/api-reference/points/get-points)
supports ID-based verification without transferring vectors, and its
[idempotent upsert](https://qdrant.tech/documentation/concepts/points/) makes
replay safe.

For a controlled rebuild, stop the ingestion worker and chat backend first. Back
up PostgreSQL, private source storage and Qdrant. Restore or create the Qdrant
collection for the configured model, then remove only the completed-index markers:

```sql
DELETE FROM source_vector_indexes;
```

Start the worker. It replays all currently approved, eligible revisions from
PostgreSQL. Keep chat unavailable until the marker count matches the approved
revision count and a synthetic paraphrase, held-source and revocation check pass.
Do not restore an old Qdrant snapshot as an authority for visibility. A model or
chunking change needs a new named collection/generation and an evaluation before
traffic switches; merely changing the dimension on an existing collection is
unsafe.

## Operational limits

The local Docker port is bound to loopback for development. Production requires
service authentication, network isolation, backups, resource limits and monitoring
for indexing lag, model failures, Qdrant availability, query latency and stale
points. The current indexer performs serial work and the search adapter retrieves
at most 100 vector candidates before current-rights filtering; measure recall at
larger corpus size. The text model, chunking and no-evidence threshold are not
release quality decisions until the frozen evaluation and expert review pass.
