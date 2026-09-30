# Text-pilot backup and restore

PostgreSQL is authoritative for accounts, chat retention, source revisions,
metadata amendment history, rights decisions, exact locators and vector
completion markers. Private source files are authoritative original bytes.
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
Compare source/revision/metadata-event/decision and chat counts with the backup
manifest. Check that each restored revision has version 0 and that its latest
metadata event matches its current description, tags and `metadata_version`;
verify every restored original byte hash against `source_revisions.sha256` and
its `storage_key`. Challenge one approved, one revoked and one expired record
through the API before serving traffic. The restored Qdrant collection should
start empty: run the worker and wait for index replay, then verify a cited answer
and that the revoked revision remains absent. If restoring Qdrant for speed,
reconcile it against PostgreSQL and current model ID before enabling search.

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

The procedure follows [PostgreSQL's `pg_dump` and `pg_restore` documentation](https://www.postgresql.org/docs/current/backup-dump.html)
and [Qdrant snapshot/recovery guidance](https://qdrant.tech/documentation/operations/snapshots/).
The project uses replay for its small text index; Qdrant snapshots may reduce
rebuild time for larger media collections but need version and rights checks.
