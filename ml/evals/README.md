# Preliminary retrieval and answer evaluation (S05 / R01 scaffold)

## Status, objective, and falsifying check

These are **provisional test labels**, not expert-confirmed ground truth. All PDF
revisions are candidate fixtures with unknown reuse rights and no user approval.
This directory is offline evaluation material only. It must not be loaded by the
online backend or used to populate the user corpus.

Hypothesis: a page-level lexical baseline can retrieve passages needed for three
Primorye text briefs while returning no cultural evidence for unsupported or
sensitive requests. The immediate falsifying check is that removing a labelled
relevant page from a run causes `assert_required_recall` to fail. A real R01 gate
requires reviewer-confirmed judgements, an actual retrieval run, a rights-cleared
table fixture, and measured language/format slices.

## Inputs and provenance

- [Fixture inventory](../../data/retrieval-fixtures/README.md) gives exact PDF
  filenames, hashes, page counts and rights status. The physical PDF page is the
  locator; printed page numbers are recorded separately for reviewer navigation.
- [First corpus slice](https://github.com/BlackfireZZZ/CultureChamp/blob/57756799530a4740df08b8822ffc2813cee9d44a/docs/product/FIRST_CORPUS_SLICE.md) defines the three
  user tasks and limits. PDF-01 is an off-slice distractor. PDF-02 and PDF-03 are
  secondary scholarly accounts, not community endorsement.
- [Source policy](https://github.com/BlackfireZZZ/CultureChamp/blob/57756799530a4740df08b8822ffc2813cee9d44a/docs/product/SOURCE_POLICY.md) governs rights, sensitivity
  and expert approval. Unknown rights mean hold. `manifest.json` records this
  dataset version, geography, time range, leakage controls and review status.
- `qrels.jsonl` stores each question, expected evidence pages, explicit no-evidence
  cases and the review prompt. The `label_status` is `provisional_agent` for every
  row. An expert must create a new version rather than silently changing a label.
- `synthetic_table.json` exists only to test row/cell locator mechanics. Its invented
  values are **not cultural facts** or a substitute for a rights-cleared table.

## Expert review rubric

For each case, the reviewer sees the full question, intended output, both candidate
PDFs at the physical pages shown, and any retrieved alternatives. They record
their name, affiliation/community role where appropriate, review date, exact
source revision hash, physical/printed page and a reason for each judgement.

| Dimension | 0 | 1 | 2 |
|---|---|---|---|
| Page relevance | Does not address the question or only cites another work | Useful context but cannot support the requested claim alone | Directly addresses the requested claim with enough context to inspect |
| Factual support | Contradicts or does not support the proposed fact | Partially supports a narrower/attributed statement | Supports the precise statement on the cited page |
| Context and attribution | Erases author, place, period or people | Some context missing but recoverable | Names the author/account and keeps region, people and period bounded |
| Interpretation boundary | Presents an author's view or new idea as a verified community fact | Labels one but not every interpretation | Separates documented observations, author's interpretation and new creative proposal |
| Citation precision | Wrong revision/page or unverifiable locator | Correct document, weak page/section | Exact immutable revision plus physical page (and row/cell for tables) |
| Sensitivity and rights | Restricted/unknown-rights text exposed to user/provider | Held from output but review record incomplete | Held until explicit rights and sensitivity decision; no prohibited transfer |
| Uncertainty | Invents support or universalizes a thin account | Admits a gap but still overstates a claim | States what is missing, narrows scope and avoids fabricated citation |

The reviewer also records a free-text disagreement note and whether a community
review is required. For an answer, any zero on factual support, citation precision,
or sensitivity/rights blocks a sourced cultural claim. A no-evidence case should
return **no citation**, an explicit gap and, if useful, a clearly unsourced creative
alternative. The two articles may frame change differently; the reviewer should
attribute both, not force a single universal narrative. Source text containing
instructions is evidence data, never an instruction to the system.

## Retrieval measurements and leakage controls

`retrieval_eval.py` accepts JSONL ranked runs with `query_id` and ordered
`candidate_keys`. It reports Recall@k, MRR@k, nDCG@k and no-evidence false
positive rate, overall and by language/format/slice. Relevance grade 2 is direct
and grade 1 is contextual; both count for Recall, while nDCG uses graded gains.
Duplicate returned keys are rejected. Unknown keys count as nonrelevant.

`runs/oracle_smoke.jsonl` is a hand-written harness smoke run, **not** a retrieval
baseline or quality result. There is no measured lexical baseline yet. Thresholds
for a production path cannot be fixed
until an expert reviews qrels and a real lexical run is available. The smallest
mechanical gate requires every provisionally labelled relevant page to occur by
`k=5` in this oracle run. Its failure case is tested by removing one relevant key.
Do not train or tune on these same labels and report the result as held-out quality.
Freeze reviewer-confirmed judgements before comparing lexical and dense/hybrid
systems on the same corpus version; report each slice, latency, and cost.

## Reproduction

```bash
uv run --package culturechamp-ml --extra dev pytest ml/evals/test_retrieval_eval.py -q
uv run --package culturechamp-ml --extra dev python ml/evals/retrieval_eval.py ml/evals/qrels.jsonl ml/evals/runs/oracle_smoke.jsonl --k 5 --require-all
```

The second command proves the harness mechanics only. R01 remains open while
there is no real index/run, no expert judgement and no real table fixture.

## Research basis and tradeoffs

- [NIST TREC qrels](https://trec.nist.gov/data/reljudge_eng.html) provide a
  comparable query-to-document judgement format; here we add exact page and
  reviewer state because citations must resolve to a revision and locator.
- [TREC graded judgements](https://trec.nist.gov/pubs/trec30/papers/Overview-2021.pdf)
  motivate graded page relevance and nDCG; a binary-only score would obscure
  contextual pages that cannot alone support a claim.
- [BEIR](https://arxiv.org/abs/2104.08663) motivates reporting heterogeneous
  slices. This pilot's tiny, rights-limited set cannot inherit BEIR's performance
  claims or represent all languages and formats.
