# ADR 0007: Treat retrieved text as untrusted model input

Status: Implemented for explicit instruction patterns in the text pilot;
provider-specific and expert reviews remain open.
Date: 2026-09-30

## Context and comparable evidence

An approved source revision is eligible evidence, but its extracted text and
catalogue metadata are still data rather than instructions to the assistant.
The existing role-separated prompt and JSON/citation validation rejected
fabricated IDs and facts absent from the excerpt. A challenge test showed two
remaining failures: a retrieved passage with an explicit assistant command was
sent to the model, and a quoted `Count: 7` was accepted against `Count: 70`.
Table evidence also reached the model without its sheet and cell locator.
The text pilot later exposed another context gap: approved revision tags for
region, people and period were visible in materials but absent from the model
evidence payload, making source disagreement harder to represent faithfully.

[OWASP LLM01](https://genai.owasp.org/llmrisk/llm01-prompt-injection/)
recommends separating external content, validating output formats, least
privilege and adversarial tests; it explicitly warns that RAG does not eliminate
prompt injection. The [BIPIA study](https://arxiv.org/abs/2312.14197) found that
models can confuse external text with actionable instructions and measured
mitigation from explicit boundary reminders. These findings support layered
controls, not a claim that string matching solves the attack class.
[W3C PROV-O](https://www.w3.org/TR/prov-o/) provides a comparable distinction
between a source entity and its attribution/provenance relationships. A
[cultural-heritage RAG provenance study](https://arxiv.org/abs/2509.20769)
structures chronological, geographical and cultural attributions alongside
retrieved evidence. This pilot uses bounded revision tags rather than adopting a
formal ontology or treating those papers as evidence of model accuracy.

## Decision

- Keep the system instruction in its own provider role. Send the brief and
  evidence as JSON data with exact revision, segment and full page/table locator.
  Attach existing revision-scoped region, people and period tags to that same
  evidence item; do not infer missing tags. Ask the model to preserve differences
  across those contexts. The model receives no source-administration tools or
  provider key.
- Before constructing model context, exclude any retrieved segment whose excerpt,
  title, creator, locator or context tag contains a small set of explicit role
  markers or commands to override instructions or reveal a system prompt,
  including direct English and
  Russian forms. Normalize Unicode for detection. Do not rewrite the stored
  source, index or admin review record. If nothing usable remains, return the
  insufficient-evidence response without a model call.
- Validate model-selected IDs against only the screened context, re-resolve each
  citation under current publication state and require the `fact` field to match a
  bounded span of a cited excerpt with word boundaries and numeric-prefix
  checks. Interpretive and creative fields retain visible labels, but their
  cultural accuracy is not algorithmically certified.

## Alternatives and risks

A system instruction alone leaves the model to enforce its own trust boundary.
Blindly removing suspicious substrings could splice unrelated source passages
into an apparently factual quote; excluding the whole segment avoids that
specific failure. The explicit-pattern screen can reject legitimate writing
about AI instructions and can miss obfuscated, indirect, multilingual or
semantically equivalent attacks. Word-boundary matching prevents the tested
numeric-prefix error but does not prove semantic support or contextual accuracy.
Tags are editorial metadata, not independent proof that an excerpt is true or
representative of everyone in the named community. The model can still put
unsupported claims in interpretation or creative prose.
Consequently G05 and answer-quality release gates remain open pending a
provider-specific adversarial run and qualified cultural review. A reviewer
should inspect a rejected segment in admin view and correct or exclude the
source through the governed review process.

## Verification

Challenge tests use a clean passage alongside an explicit injected passage,
an injected catalogue title, English/Russian role-control examples, a model
fact differing only by a numeric suffix, and a table citation whose complete
sheet/row/column locator is present in model context. The focused generation
suite first failed the instruction and numeric-prefix cases, then passed after
the change. The clean PostgreSQL/Qdrant full gate and built synthetic browser
journey passed. These tests do not establish quality with the selected external
provider or real cultural sources.
Additional synthetic checks keep distinct region/period tags with each evidence
revision and reject a role-control marker in a context tag. A live
PostgreSQL/Qdrant test verifies the permitted revision's tags on the mocked HTTP
wire. This checks context transport, not the model's handling of disagreement.
