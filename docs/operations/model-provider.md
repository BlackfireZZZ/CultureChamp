# External text model configuration

The backend defaults to the deterministic `fake` provider. It exercises chat,
citations, quotas and failure handling but does not create useful cultural prose.
The fake provider is available only with `APP_ENV=development`. Any other
environment rejects it at server startup, and a missing provider during a chat
request returns HTTP 503 instead of silently selecting the fake provider.
Each accepted generation attempt consumes a user and global UTC daily quota slot,
including a retry after a failed request. A provider transport retry may make a
second HTTP call within the same reserved generation; reconcile provider billing
against actual usage before setting a spending target.
The `generation_attempts` table keeps reported input/output tokens and whether
the result passed the gateway's output limit for each reserved application attempt.
A rejected overlength response still records its reported usage. Missing usage
means the call failed before a valid usage report or predates this accounting
change; it does not prove that the provider charged zero. Transport retries share
one application attempt, so their separate usage is not observable here.

The provider adapter accepts an operator-selected HTTPS endpoint compatible with
Chat Completions. Yandex AI Studio was exercised on 2026-10-02 with the private
operator configuration and a self-authored synthetic source. The user has also
authorized the supplied document corpus for model-backed local testing. The
exact model URI and key remain server-only; document files stay outside Git.
[Yandex's OpenAI-compatible API guide](https://yandex.cloud/en/docs/tutorials/ml-ai/ai-model-ide-integration)
specifies the `https://ai.api.cloud.yandex.net/v1` base and a
`gpt://<folder-id>/<model-id>/latest` model URI.

The backend reads these settings; the frontend and ingestion worker do not:

| Setting | Meaning |
|---|---|
| `MODEL_PROVIDER` | `fake` (default) or `openai_compatible` |
| `MODEL_API_ENDPOINT` | HTTPS Chat Completions URL or its `/v1` base; the adapter appends `/chat/completions` to a `/v1` base |
| `MODEL_API_NAME` | Exact model ID accepted by that endpoint |
| `MODEL_API_KEY` | Backend-only bearer key; supply outside Git and do not print Compose configuration |
| `MODEL_POLICY_APPROVED` | `true` only after operator review of provider region, retention/training terms and data rules |

An external configuration missing the policy decision, URL, model or key fails
server startup. The adapter does not follow redirects, bounds response bytes,
requests and time, and returns generic errors without raw provider responses.
The model key remains in backend process configuration; production should inject
it from a secret manager rather than a checked-in `.env` file.

The request asks for `response_format: {"type": "json_object"}` and sends an
explicit four-key answer schema in its system instruction. The selected
endpoint must return a non-streaming Chat Completions choice with
`finish_reason: "stop"`, text content, and positive integer `usage.prompt_tokens`
and `usage.completion_tokens`. The adapter rejects `length`, `content_filter`,
tool/function calls, absent usage and malformed counts with a generic failure.
This keeps truncated or unmetered completions out of chat and preserves the
per-call output-token check. Some otherwise compatible endpoints omit usage;
validate this response contract with a synthetic request before activation.
The finish-reason values follow the [official Chat Completion response type](https://github.com/openai/openai-go/blob/main/chatcompletion.go#L2644-L2662).

After selecting a service and approving its terms, set `MODEL_API_ENDPOINT`,
`MODEL_API_NAME`, `MODEL_API_KEY` and `MODEL_POLICY_APPROVED=true` through the
operator's private environment. From the repository root, run:

```bash
MODEL_PROVIDER=openai_compatible uv run --package culturechamp-backend \
  python -m app.infrastructure.model.preflight --send-synthetic
```

This opt-in command sends a fixed, self-authored synthetic excerpt and invented
region tag through the same model gateway and answer/citation validator as chat.
It reads no source database or uploaded original, and prints only pass/fail,
reported token counts and elapsed time. It can make a second HTTP call if the
provider returns a temporary failure. Without `--send-synthetic` it sends
nothing; fake or incomplete external configuration fails. Passing this check
proves only the selected endpoint's wire and answer shape for one synthetic
prompt. For the local demonstration, verify the same-origin chat path with the
supplied published revisions and confirm that the response cites actual passages.

For an isolated Yandex synthetic check, the operator's ignored `.env` may keep
`MODEL_POLICY_APPROVED=false` for ordinary startup. Set the flag to `true` only
in the test process, using the private key and model already in that file. The
tracked `.env.example` must contain placeholders only. Do not paste the key into
shell commands, test output, Git, frontend settings or Compose diagnostics.

The 2026-10-02 synthetic preflight passed through the actual Yandex endpoint:
368 input tokens, 96 output tokens and 1,249 ms elapsed. The first call had
returned fenced JSON with a non-contract citation field; the JSON response
format and exact key instruction fixed that mismatch. The built backend,
worker, PostgreSQL and Qdrant then passed
`scripts/live_yandex_synthetic.py` on an isolated Compose project: a private
self-authored TXT stayed hidden before review, an approved
`provider_transfer` revision produced a grounded exact segment citation, and
revocation made that historical citation unavailable. Backend telemetry recorded
one call, 338 input tokens, 91 output tokens, 1,170 ms, one attempt. A content
scan found no key in backend logs or frontend assets. The experiment does not
measure a production bill or answer quality on cultural sources.

When the external adapter is active, chat retrieves only revisions whose current
publication state includes model-context visibility. The current schema calls
that field `provider_transfer`; for the user-supplied local corpus it records the
already given authorization and the operator's activation of that revision.
PostgreSQL filters revision IDs before Qdrant ranking and rechecks returned
segments before a model call. If none qualify, chat returns an insufficient-
evidence answer without contacting the endpoint.

Set the key through the private deployment environment, activate the supplied
revisions for model context, and run a same-origin chat request. Inspect the
resulting answer and citations, metadata-only logs and per-attempt token record;
verify that the browser bundle and network traffic contain no provider key or
direct provider request. The earlier synthetic wire check established endpoint
shape; cultural answer quality needs inspection on the supplied corpus.
