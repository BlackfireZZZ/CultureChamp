# Source admission and revocation policy (S02)

## Supplied corpus

The user has authorized the supplied documents for application testing, including
display in the local interface and use as context for the configured model. The
source files are local application data and must never be committed to Git. Keep
them in ignored local storage, database volumes, or another private deployment
store. The repository may contain only code, metadata templates, and synthetic
test fixtures authored for the project.

## Decision principle

An exact source revision enters user search and generation after an administrator
checks its identity, extraction quality, and suitability for the intended task.
This is an application publication state. It keeps draft imports, processing
failures, and withdrawn revisions out of user results. A model must not treat
source text as instructions, and a retrieved passage must not turn an
interpretation into a verified cultural fact.

## Review record for each exact revision

1. **Identity and provenance:** record title, creator, origin, supplied file
   provenance, acquisition date, byte hash, language, region, people, period,
   and whether the text is a primary account or an author's interpretation.
2. **Credibility and scope:** identify expertise, method, contradictions,
   outdated terminology, and claims requiring corroboration.
3. **Cultural context:** flag sacred, ritual, personal, or community-sensitive
   passages for editorial review; exclude a passage when it cannot be presented
   responsibly. This is a content-quality decision, not a document-use gate.
4. **Extraction and location:** compare samples against the rendered original,
   verify reading order and stable page/section/table locators, and note omissions.
5. **Publication decision:** record reviewer, time, exclusions, exact immutable
   `revision_id`, and hash. The application may continue to use its existing
   exact-revision visibility fields to express this decision.

## Visibility and revision history

| State | User search/chat/materials | Admin inventory | Prior citation |
|---|---|---|---|
| Candidate or processing | Hidden while import and review complete | Reviewable | No citation issued |
| Published exact revision | Reviewed passages and metadata available; original opens in the document reader | Full review record | Resolves to the same revision and locator |
| Passage with a cultural or extraction issue | Remove the passage until corrected; withdraw the revision if it cannot be isolated | Preserve reason and history | Explain unavailable status without revealing removed text |
| Withdrawn revision | Excluded from new retrieval and model context | Retain immutable record and audit trail | Keep historical identity; never redirect to another revision |

Publication applies to one `revision_id`, its bytes and reviewed extraction.
Replacement files and changed text require a new review decision. Metadata edits
must not rewrite cited bytes or locator meaning. Withdrawal updates eligibility
immediately even if the search index or cache is stale; retrieval and display
recheck the authoritative revision state at read time.

## Fixture checks

The [fixture inventory](../../data/retrieval-fixtures/README.md) identifies the
locally supplied PDFs. Compare page reading order, citations, and cultural
context before using a passage as evidence. The two-column PDF needs a rendered
page comparison because line extraction can interleave its columns. These are
quality checks, not a request for the user's authorization again.
