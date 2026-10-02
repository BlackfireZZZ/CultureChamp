# Source admission, rights and revocation policy (S02)

## Isolated local testing

An administrator may record the user's explicit attestation for a disposable local
development corpus with a `local-test://user-attestation/<date>` evidence reference.
This path requires `LOCAL_TEST_SOURCE_APPROVAL=true`, `APP_ENV=development`, and
the fake model provider. Provider transfer remains prohibited. The decision reason
must state that external reuse rights and cultural accuracy are unverified; this
local test grant is not a publication or production rights decision. Production
continues to require an HTTPS rights evidence reference and the review below.

## Decision principle

Publication, DOI assignment and extractable text establish identity and access,
not permission for redistribution or generation and not community approval. An
exact revision is eligible for user retrieval only after a named accountable
reviewer records all gates below. Unknown evidence means **hold**, not approval.

## Review record for each exact revision

1. **Identity and provenance:** record title, creator, publisher/holding body,
   stable origin URL/DOI, supplied file provenance, acquisition date, byte hash,
   language, stated region/people/period, and whether a primary account or an
   author's interpretation. Compare bibliographic details with the publisher.
2. **Credibility and scope:** identify the expertise and method, contradictions,
   outdated terminology, and claims that require corroboration. Tag the level of
   evidence at passage level when a source mixes observation and interpretation.
3. **Rights by use:** record the exact license or written permission and its source,
   holder, version, date and scope separately for private processing, text mining,
   external-model transmission, public snippets, original-file display/download,
   and derivative creative use. A readable PDF or open-access label alone does not
   authorize every use. Limit excerpts and links to what the decision permits.
4. **Sensitivity:** screen for sacred, ritual, restricted, personal and community-
   sensitive content. Seek a qualified community or institutional reviewer when
   needed. Exclude a passage or the whole revision if its use cannot be justified;
   a legal reuse right does not override a cultural restriction.
5. **Extraction and location:** compare samples against the rendered original,
   verify reading order and stable page/section/table locators, and note omissions.
6. **Decision:** record reviewer identity and authority, decision time, evidence
   links, allowed uses, exclusions, and the exact immutable `revision_id` and hash.
   Technical ingestion and cultural/rights approval are distinct acts. A source
   needs both before user retrieval. The final approval authority is to be named
   by the project owner; this draft does not assign it to the uploader.

## Visibility and sensitive cases

| State | User search/chat/materials | Admin inventory | Prior citation |
|---|---|---|---|
| Candidate, processing, rejected or rights unknown | Invisible, including title and metadata | Reviewable by authorized staff | No user citation issued |
| Approved exact revision, with permitted use and no unresolved restriction | Only the permitted passages and metadata; original file only if specifically permitted | Full review record | Resolves to the same revision and locator |
| Disputed or newly identified sensitive passage | Immediately suspend its user eligibility pending review; if passage isolation is uncertain, revoke the revision | Preserve evidence and reason | Explain unavailable status without leaking restricted text |
| Revoked revision | Excluded before ranking and from any model context | Retain immutable record and audit trail under retention rules | Keep historical identity, never redirect to another revision; show unavailable status |

An approval applies to one `revision_id`, its bytes and reviewed extraction. A
replacement PDF, changed text, changed rights scope, or changed sensitivity
assessment needs a new review decision. Preapproval metadata corrections are
recorded with an audit event and cannot rewrite the cited bytes or locator
meaning. The reviewer compares the corrected description and tags with the
original and extracted text. Postapproval correction needs a new review
workflow; it is not an in-place edit. Revocation must update eligibility
immediately even if a search index or cache is stale.
Downstream retrieval and source display must check the authoritative revision
decision at read time. Reindexing or retries cannot reinstate a revoked revision.

## Candidate fixture decisions as of 2026-09-30

| Fixture | Reviewer and rights decision | Sensitivity and visibility |
|---|---|---|
| PDF-01, Kazin 2022 | Accountable editorial/rights reviewer **not yet assigned**; article identity visible in PDF, publisher match and reuse scope unverified. **Hold.** | Interpretive discussion of religion/civilization; outside first slice. Admin-only test fixture, no user retrieval or model transmission. |
| PDF-02, Danilova and Karim 2020 | Accountable editorial/rights reviewer **not yet assigned**; publisher page found, exact license and allowed uses unverified. **Hold.** | Indigenous cultural and ecological context requires scoped review; admin-only test fixture. |
| PDF-03, Gvozdev 2024 | Accountable editorial/rights reviewer **not yet assigned**; publisher article found, exact license and allowed uses unverified. **Hold.** | Includes generalizations and discussion of spiritual practices; admin-only test fixture. Two-column extraction also needs review. |

The [fixture inventory](../../data/retrieval-fixtures/README.md) identifies the
bytes. The publisher pages for [PDF-02](https://science.vvsu.ru/scientific-journals/journal/current/article/id/2147048284/2020_2_19_Perspektivyehtnoehkologicheskikhissledovanijjkultu)
and [PDF-03](https://www.ebsvkr.ru/ru/nauka/article/89702/view) support
bibliographic checking, not a reuse grant. Crossref distinguishes license scope
for versions and text mining in its [license metadata guidance](https://www.crossref.org/documentation/schema-library/markup-guide-metadata-segments/license-information/).
The Library of Congress's [sensitive-materials access policy](https://www.loc.gov/acq/devpol/materialsindigenouspeoplesaccess.pdf)
is a comparable, community-aware access model, not jurisdictional authority for
these Russian sources. Its distinction between access, reproduction and community
permission informs the separate gates above.

## Challenge checks

- A publisher PDF with no explicit reuse grant remains held even when a DOI and
  extracted text exist.
- A disputed Udege or Nanai passage is removed from user retrieval while its
  source, review history and prior citation identity are retained for authorized
  audit. If safe passage-level isolation cannot be proven, revoke the whole revision.
