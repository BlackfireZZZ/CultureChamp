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

The provider adapter accepts an operator-selected HTTPS endpoint compatible with
Chat Completions. No service, model ID, endpoint or key is selected for this pilot.

The backend reads these settings; the frontend and ingestion worker do not:

| Setting | Meaning |
|---|---|
| `MODEL_PROVIDER` | `fake` (default) or `openai_compatible` |
| `MODEL_API_ENDPOINT` | Full HTTPS Chat Completions URL, without embedded credentials |
| `MODEL_API_NAME` | Exact model ID accepted by that endpoint |
| `MODEL_API_KEY` | Backend-only bearer key; supply outside Git and do not print Compose configuration |
| `MODEL_POLICY_APPROVED` | `true` only after operator review of provider region, retention/training terms and data rules |

An external configuration missing the policy decision, URL, model or key fails
server startup. The adapter does not follow redirects, bounds response bytes,
requests and time, and returns generic errors without raw provider responses.
The model key remains in backend process configuration; production should inject
it from a secret manager rather than a checked-in `.env` file.

The selected endpoint must return a non-streaming Chat Completions choice with
`finish_reason: "stop"`, text content, and positive integer `usage.prompt_tokens`
and `usage.completion_tokens`. The adapter rejects `length`, `content_filter`,
tool/function calls, absent usage and malformed counts with a generic failure.
This keeps truncated or unmetered completions out of chat and preserves the
per-call output-token check. Some otherwise compatible endpoints omit usage;
validate this response contract with a synthetic request before activation.
The finish-reason values follow the [official Chat Completion response type](https://github.com/openai/openai-go/blob/main/chatcompletion.go#L2644-L2662).

When the external adapter is active, chat retrieves only revisions whose current
approval includes `provider_transfer`, in addition to user-text and sensitivity
clearance. PostgreSQL filters the allowed revision IDs before Qdrant ranking and
rechecks returned segments before a model call. If none qualify, chat returns an
insufficient-evidence answer without contacting the endpoint. The three locally
held PDFs are not approved for user excerpts or provider transfer.

Before activating a real provider, record its exact endpoint/model and terms,
set the key through the deployment secret channel, approve provider transfer on
specific reviewed revisions, and run a synthetic request through the same-origin
chat API. Inspect the resulting citation and metadata-only logs; verify that the
browser bundle and network traffic contain no provider key or direct provider
request. A real API request and provider-specific response parsing remain
unverified until those inputs are supplied.
