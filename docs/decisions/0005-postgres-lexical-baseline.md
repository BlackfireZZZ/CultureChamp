# ADR 0005: Provisional PostgreSQL lexical baseline

Status: Superseded by ADR 0006. Historical measurement only; never a chat retrieval default.
Date: 2026-09-30

## Context and falsifiable decision

The current source corpus has immutable segments and append-only revision
decisions. Retrieval must filter the latest exact decision, processing state,
publication state and sensitivity **before** ranking and limiting results. The first
provisional qrels have eight cases, including one explicitly synthetic table
mechanics case. They are agent labels, not expert ground truth. The measurement used local, temporary PostgreSQL data only.

PostgreSQL's [text-search controls](https://www.postgresql.org/docs/17/textsearch-controls.html)
define query normalization and cover-density ranking, and its
[GIN operator support](https://www.postgresql.org/docs/17/gin.html) supports
indexed `@@` matching. The same eight queries and exact fixture bytes were
used to compare `simple` and `russian` text-search configurations. No dense
or hybrid index was adopted.

## Decision

The GIN expression index on `to_tsvector('russian', text)` remains an offline
comparison baseline. It must not be used as the product's RAG retrieval path.
The earlier decision to make it the pilot default was incorrect for the intended
semantic and multimodal product. Normalize up to 24 distinct query terms, OR
them, rank matching segments with `ts_rank_cd`, and break ties by revision,
ordinal and segment ID only when reproducing the historical measurement.
The application service bounds the query and result count. The SQL joins the
latest decision and requires review-pending processing, `approve`, `user_text`
and sensitivity clearance before `ORDER BY` and `LIMIT`. An external provider
path additionally requires `provider_transfer`. Optional region and people
filters use exact revision tags.

This default is reversible through a migration. It does not decide the final
relevance threshold, no-evidence detection, embedding model or release gate.
An evidence hit is a candidate passage, not proof of a cultural fact. Generation
must separately validate support and cite only segments it actually used.

## Same-set measurement

The offline runner hash-checked all three supplied PDFs, parsed their page text in
the bounded subprocess, loaded it and the synthetic table cell into a temporary
PostgreSQL table, and wrote only locator keys and ranks to the run files. The
same eight provisional qrels and `k=5` were used for both configurations.

| Configuration | Recall@5 | MRR@5 | nDCG@5 | No-evidence false-positive rate |
|---|---:|---:|---:|---:|
| `simple` | 0.40 | 0.50 | 0.443 | 0.667 |
| `russian` | 0.80 | 0.60 | 0.634 | 1.000 |

The Russian configuration found the synthetic table cell; the simple
configuration did not place it in the top five. The false-positive rates are
unacceptable as a standalone answer policy: lexical overlap can return
irrelevant passages for a request with no supported answer. The tiny corpus,
agent labels, page-sized chunks and mixed English/Russian table case make these
numbers diagnostic only. They do not establish a cultural quality claim.

On four synthetic database candidates containing the same search marker, a
held revision and a revoked revision with repeated marker text were absent from
results. A later revocation removed a previously visible revision on the next
query. A plan with sequential scans disabled showed a bitmap scan on the GIN
index, current-decision index lookup before sorting, and 0.841 ms execution on
this tiny local dataset; it is not a latency forecast for a real corpus.

## Next falsifying checks

Obtain expert-confirmed qrels and a real permitted table before choosing a
release threshold. Compare any dense/hybrid alternative on the same frozen
corpus and query set with latency and cost. Test claim-level no-evidence and
sensitive-content guardrails; a lexical score alone cannot make that decision.
Recheck the plan and latency at realistic corpus size. Revocation and publication-state
checks must remain on the authoritative database path even if an index is stale.
