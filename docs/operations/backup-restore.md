# Text-pilot backup and restore

PostgreSQL is authoritative for accounts, account grant events, chat retention,
source revisions, metadata and segment review history, publication decisions, exact locators
and vector completion markers. Private source files are authoritative original bytes.
Qdrant is a derived index and can be rebuilt from approved PostgreSQL
revisions after the database and originals are restored. A Qdrant snapshot
alone must never decide source visibility.

This procedure covers the local single-node text pilot. Institutional media
collections, multiple Qdrant nodes and production object storage require a
separate backup design and restore drill. Only an operator with access to
private source files and database credentials should run it.

## Consistent backup

1. Stop new admin intake and chat writes. Wait for or stop the ingestion worker.
   Record the application commit, migration revision and the backup timestamp.
2. Create a restricted backup directory (`umask 077`). Use the PostgreSQL 17
   client from the database container and `pg_dump -Fc` for a portable archive:

   ```bash
   umask 077
   COMPOSE_PROJECT_NAME=culturechamp docker compose exec -T db \
     pg_dump -U culturechamp -d culturechamp -Fc > culturechamp.dump
   COMPOSE_PROJECT_NAME=culturechamp docker compose exec -T backend \
     tar -C /workspace/.private -cf - sources > culturechamp-sources.tar
   sha256sum culturechamp.dump culturechamp-sources.tar > SHA256SUMS
   ```

3. Encrypt the archives before transfer. Keep the encryption key outside the
   archive location and test that the backups can be read. The private model
   cache is reproducible from the pinned weights and is not part of the source
   archive. Backups containing chat content must age out within the extra
   30-day window in [ADR 0004](../decisions/0004-access-model-data.md). A
   retention schedule and encrypted remote backup destination are not yet
   implemented.

`pg_dump` gives a consistent database snapshot but cannot make a simultaneous
snapshot of the separate file volume. Quiescing writes keeps revision rows and
original bytes aligned. Database-only or source-only backup is insufficient.

## Isolated restore and verification

Restore to an empty database and private source directory while the application
and worker are stopped. Use matching or compatible PostgreSQL/PostGIS images and
the recorded application commit. For the local pilot:

```bash
sha256sum -c SHA256SUMS
COMPOSE_PROJECT_NAME=culturechamp docker compose exec -T db \
  createdb -U culturechamp culturechamp_restore
COMPOSE_PROJECT_NAME=culturechamp docker compose exec -T db \
  pg_restore -U culturechamp --no-owner --no-acl -d culturechamp_restore \
  < culturechamp.dump
mkdir -p restored-private
tar -xf culturechamp-sources.tar -C restored-private
```

Point `DATABASE_URL` at the restored database and run `make migration-check`.
Compare account/grant-event/source/revision/metadata-event/segment-review-event/decision and chat
counts with the backup manifest. Check that each restored revision has version 0
and that its latest metadata event matches its current description, tags and `metadata_version`;
for a revision with segment review events, check the latest excluded IDs against
`source_segments.included` and `segment_review_version` before replaying Qdrant;
verify every restored original byte hash against `source_revisions.sha256` and
its `storage_key`. Challenge one approved, one revoked and one expired record
through the API before serving traffic. The restored Qdrant collection should
start empty: run the worker and wait for index replay, then verify a cited answer
and that the revoked revision remains absent. If restoring Qdrant for speed,
reconcile it against PostgreSQL and current model ID before enabling search.
Rolling back migration `f406c9a2b7e1` discards exclusion projections and audit
events. For a failed deployment after reviewers have made exclusions, restore
the paired PostgreSQL/private-original backup or roll forward; do not use a
schema downgrade to recover those decisions.

Do not copy a test restoration over an active database or source volume. Do not
delete the last known-good backup until the independent restore checks pass.

## Observed synthetic drill, 2026-09-30

The isolated `culturechamp_chatjourney` stack used self-authored CSV files and
the fake model. A PostgreSQL custom archive restored into a separate
`culturechamp_restore` database. Source and restored counts matched:
5 conversations, 7 turns, 5 revisions, 5 segments and 10 decisions; Alembic
reported no new operations. Five archived originals extracted into a separate
directory and each SHA-256 matched both its content-addressed filename and the
restored `source_revisions.sha256` set. In the
browser journey, deletion of the test Qdrant collection triggered worker replay;
the next turn again cited the approved exact revision. This proves the mechanics
on a small, quiescent synthetic set. It does not prove production restore time,
encrypted storage, continuous backup, retained approvals after full-stack
replacement or recovery objectives at scale.

## Failure response and observability

- If PostgreSQL is unavailable, stop ingestion and generation; restore the
  database and originals together before starting the worker. Do not trust
  Qdrant to reconstruct source decisions or chat history.
- If only Qdrant is lost, the worker recreates the collection and replays
  currently approved revisions. Chat may return 503 during replay; check
  indexing lag and confirm exact-revision citations after recovery.
- If the model provider is unavailable, return a generic 503 without exposing
  prompts or keys. The browser keeps the draft and retries with the same
  request ID. A synthetic 503 path passed the live browser check; a real
  provider outage drill remains open.
- Monitor PostgreSQL and Qdrant readiness, worker failure/retry counts, index
  lag, chat 429/503 rates, backup age, restore-test age, latency percentiles
  and provider token/cost estimates. Thresholds and alert routing need measured
  pilot traffic; they are not configured yet.

Each reserved model call emits one `model_call` line through the backend's
Uvicorn error logger. `docker compose logs backend | rg 'model_call '` shows
`outcome`, elapsed `duration_ms`, provider `attempts`, and reported input/output
tokens. The duration covers the provider phase and quota finalization; it does
not include retrieval or HTTP transport. Failed calls without a parsed response
have `None` token counts. An over-limit parsed response records its reported
usage in the log even though its quota reservation fails. These lines contain
no prompt, response, user ID, request ID, key or excerpt. Provider retries may
incur usage absent from the final response; reconcile actual invoices before
calling these counts cost. Pricing, production log retention, p95 thresholds
and alert routing remain pending the selected provider and pilot traffic.

The backend starts Uvicorn with `--no-access-log` because its default access
format includes the client address and raw request line. A replacement
`http_call` event records only an allowlisted method, matched route template (or
`unmatched`), response status and elapsed milliseconds. Use those status counts
for 429/503 rate checks without storing query strings, object IDs or client IPs.
A built Compose smoke sent a marked query and unknown path; the backend log
contained 200/404 metadata events and neither marker. This covers routine HTTP
events; exceptions and infrastructure logs still need a deployment review.
The CLI behavior follows [Uvicorn's logging settings](https://www.uvicorn.org/settings/).

The procedure follows [PostgreSQL's `pg_dump` and `pg_restore` documentation](https://www.postgresql.org/docs/current/backup-dump.html)
and [Qdrant snapshot/recovery guidance](https://qdrant.tech/documentation/operations/snapshots/).
The project uses replay for its small text index; Qdrant snapshots may reduce
rebuild time for larger media collections but need version and publication-state checks.
