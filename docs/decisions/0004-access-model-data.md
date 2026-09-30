# ADR 0004: Pilot identity, conversation retention, and model data boundary

## Status

Accepted for the bounded MVP pilot. Numeric limits and retention need user and operator validation before release.

## Context and hypothesis

The MVP has a user chat with history and a separate administrator document workflow. Source revisions may be unpublished, revoked, restricted, or sensitive. A named, invite-only pilot should make chat ownership and source access testable while limiting accidental disclosure and model cost. This is a product and security hypothesis, not evidence of demand.

## Decision

### Identity and access

- Pilot users have individual accounts with stable, opaque subject IDs. There is no anonymous or guest chat in the MVP. Public landing/help content may remain unauthenticated. A later guest mode needs its own retention and abuse decision.
- The server resolves a short-lived session to a subject and role on every protected request. The browser receives only a Secure, HttpOnly, SameSite=Strict, host-only session cookie. It never stores access or provider tokens in local storage. Unsafe requests require same-origin verification and CSRF protection. Session lifetime is at most 12 hours; logout invalidates the session. Login attempts are rate limited. HTTPS is required outside local development.
- Roles are `user` and `admin`. Admin access is granted explicitly; a user never inherits it through a client-selected role, route, or request body. The first administrator is created by a one-time, offline operator bootstrap with a unique account and password secret supplied outside Git. Bootstrap fails if an administrator already exists. Subsequent role changes require an authenticated admin action with an audit record; no public registration or admin bootstrap endpoint exists.
- Authorization is deny-by-default at the API and application use-case boundaries. Lists and retrieval filter to approved, non-revoked, permitted exact revisions **before** ranking or serialization. A user lookup by guessed ID for an unpublished/restricted/revoked revision returns the same 404 as an absent ID. Admin endpoints return 403 for authenticated users. Chat read/write/delete checks subject ownership regardless of ID. The model has no authority to relax these rules.

### Conversations and deletion

- Chat briefs and generated text are private to the owning subject. Store them in the application database for 30 days after the last activity, then delete content and ownership links through a scheduled purge. User-initiated deletion removes active conversation content promptly; backups age out within 30 additional days. Operational events may retain non-content IDs, timing, and outcome for 30 days. Never log raw prompts, source excerpts, credentials, or personal data.
- Exact source revision and locator IDs may remain in historical citation metadata, but an unavailable or revoked source must not be served to the user. A deleted chat cannot be reconstructed from application logs. The eventual schema and purge worker must be tested before this retention promise is offered to users.

### Model provider and budget

- Only the backend can call a model provider. It sends the current user brief and the minimum approved, rights-permitted evidence excerpts needed for one request. It does not send unpublished/revoked/restricted source text, other chats, user identity, email, admin notes, original files, or secrets. A preflight policy checks source rights, provider region, retention/training terms, and applicable data rules. Until a provider and those terms are approved, only the deterministic fake provider is enabled.
- The provider key is an operator-managed backend secret, never a frontend variable, response, repository value, exception string, or log field. A suspected leaked key is revoked at the provider, replaced, and investigated with metadata-only request logs; in-flight requests are stopped where possible.
- Initial protective ceilings: one active generation per user, 20 generations per user per day, 100 globally per day, 8,000 input and 2,000 output tokens per call, and a 30-second end-to-end deadline. The adapter may retry one transient failure only when the remaining deadline and budget permit. Quotas must be enforced by shared server state before an external provider is enabled; per-process counters are only suitable for tests. Exceeding a limit yields a safe 429 or bounded failure without contacting the provider.

## Threat review and falsifying checks

| Scenario | Required behavior | Smallest check |
|---|---|---|
| Browser bundle, network panel, or log reveals provider token | No provider key or raw prompt appears; browser talks only to same-origin API | Search built assets and capture browser requests; inject a provider exception containing a canary and inspect logs/responses |
| Stolen user session | Attacker can act until invalidation/expiry; short lifetime, logout, rotation, and audit limit exposure | Replay after logout and after expiry returns 401; rotated cookie invalidates old one |
| User guesses admin route or revision ID | Server rejects role and object access independent of UI | Direct API tests: user→admin 403; unpublished/revoked/unknown ID→indistinguishable 404 |
| User guesses another chat ID | No chat content or existence disclosure | Direct read/update/delete tests with two subject IDs |
| Prompt or source text asks for secrets or hidden sources | Model input contains no secret/hidden source; output cannot authorize access | Fake-provider capture and adversarial fixture |

## Alternatives and consequences

Anonymous persistent chats would need device-bound ownership and a separate abuse model; they are deferred. Browser-held bearer tokens increase token exposure to script access. A general identity provider may later replace local pilot accounts, but it must preserve opaque subject IDs and server-side role checks. The chosen session and retention policy requires account/session storage, CSRF enforcement, purge jobs, audit events, and recovery tests. These are integration gates, not implied by this ADR alone.

## Research basis

- [OWASP Authorization Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html): deny by default and verify every request; applied to roles and exact-revision access.
- [OWASP API Security Top 10, API5](https://api-security.owasp.org/editions/2023/en/0xa5-broken-function-level-authorization/): direct API calls can bypass UI restrictions; motivates negative role tests.
- [OWASP Session Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html) and [CSRF Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html): cookie attributes and CSRF defenses; SameSite alone is insufficient.
- [OWASP Secrets Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html): key lifecycle, revocation, and log exclusion.
- [OWASP Denial of Service Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Denial_of_Service_Cheat_Sheet.html): application and infrastructure rate limits; thresholds remain pilot assumptions.
- [OWASP LLM Prompt Injection Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/LLM_Prompt_Injection_Prevention_Cheat_Sheet.html): retrieved text is untrusted data; it cannot change permissions.

## Pilot implementation evidence

The server stores Argon2id password hashes and SHA-256 digests of random session
tokens in PostgreSQL. Login is limited to five attempts per username per 15-minute
window; a successful login resets that counter and rotates an existing cookie.
The local HTTP pilot uses a development-only cookie name without `Secure`; outside
development the cookie is host-prefixed and `Secure`. Both use `HttpOnly` and
`SameSite=Strict`; unsafe requests require a matching Origin and CSRF token.
These choices follow the [OWASP password-storage](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html),
[session](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html),
and [CSRF](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html)
guidance. A real HTTPS deployment, admin account audit, recovery, and the chat
retention purge have not been verified.
