# Corpus and backend handoff

## Current source handling

The user authorized the supplied documents for local application testing and
model-backed answers. Original document files are local application data and
must never be committed to Git. The [source policy](SOURCE_POLICY.md) governs
provenance, extraction review, publication state, citations and withdrawal.

## Preserved engineering contract

- A source revision identifies immutable original bytes and extracted passages.
  A citation resolves to the same revision and page, section or table location.
- An administrator can inspect a candidate and publish or withdraw a revision.
  Search and document display recheck current state even when vector indexes
  contain older points.
- Parser and storage safeguards address malformed files and resource use.
  Technical extraction quality must be checked against rendered pages, especially
  for the two-column PDF.
- The original files live in private storage outside the web root and Git.
  The repository contains code, documentation and synthetic tests only.

The original 2026-09-30 handoff remains in Git history for historical test
commands and implementation provenance. Its corpus-use assumptions were
superseded by the user's explicit authorization.
