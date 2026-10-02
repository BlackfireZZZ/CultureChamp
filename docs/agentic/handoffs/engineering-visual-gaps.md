# Engineering and visual pilot handoff

Objective and actual status: Connect a synthetic YandexGPT path, aggregate
request statistics, and a bounded image-in-PDF retrieval pilot. Implementation,
focused checks and the full clean-database gate pass. The verified branch was
fast-forward merged into local `main` at `46472d6` after incorporating the
newer `535a862` main changes. The primary checkout's user-owned dirty files
remained untouched.

Worktree / branch / base SHA: `/home/blackfire/.codex/worktrees/0eb7/CultureChamp`,
`agent/engineering-visual-gaps`, `3a837aabf7baf34cc5a74d41aafd40117a82ff9d`.
Primary path: `/mnt/BlackfireZZZ/Hackatons/CultureChamp`. At start the primary
checkout had user-owned edits to `docs/product/CONCEPT.md` and an untracked
`docs/product/POST_MVP_ROADMAP.md`; it later also had a user-owned `.env.example`
edit. Preserve all three and its private `.env`.

Owner of changed files: This integration agent owns the branch changes in
`backend`, `frontend/src`, `contracts`, `scripts` in the isolated
worktree, and this handoff. The primary checkout's dirty files remain owned by
the user and are not part of this task's commit.

Changed contracts and files: Chat send accepts optional UC-01–UC-06 starter
metadata; admin request statistics aggregate persisted turns; the OpenAPI
snapshot and generated frontend types follow. The existing model adapter now
requests JSON and accepts a Yandex `/v1` base endpoint. A separate PDF embedded
image extractor, private derived store, SQL metadata, Qdrant collection, worker,
governed search API and frontend mode implement the visual pilot.

Decisions and supporting evidence: ADR 0008 records official comparables and
the synthetic E5 caption, CLIP region and rendered-page comparison. The
YandexGPT live path used only self-authored text, and no real source content
were assumed.

Verification commands and observed results: Clean isolated PostgreSQL upgraded
through `d2a540f9c518`; `make migration-check` reported no operations. Focused
visual API integration passed with PostgreSQL/Qdrant. A real CLIP encoder
returned 512-dimensional vectors and Qdrant returned the synthetic image point.
`CORPUS_TEST_DATABASE_URL=... CORPUS_TEST_VECTOR_URL=... make check` passed on
that clean database: 112 backend, 24 frontend and 20 ML tests, Ruff, mypy,
frontend build, architecture, OpenAPI and Compose configuration. A prior
attempt against a reused synthetic database failed because unrelated approved
fixture rows remained; the clean-database run resolved the test precondition.
After merging the updated `main` into the branch, six mocked browser shell and
visual checks passed, and the live browser source-to-citation/revocation journey
passed against the current frontend, backend, worker, PostgreSQL and Qdrant.
`make smoke` passed backend liveness/readiness and frontend. A separate live
self-authored PDF check observed worker extraction, CLIP indexing, one
page-1 visual result, authorized original access and immediate denial after
revocation. Qdrant's six-point pilot collection occupied 688 KiB allocated
when empty and 728 KiB after indexing. An initial live browser run exposed a
cached-citation focus race; deferring focus until after the view switch fixed it.

What remains unverified and why: Cultural relevance, Russian-language visual
retrieval quality, real-source testing, expert answer review, actual target
user behavior and external-provider terms require human evidence. Synthetic
checks cannot establish them.

Risks and open questions: The pilot misses vector-only PDF drawings and scanned
pages without a reviewable text layer. CLIP can return an irrelevant top hit;
there is no calibrated abstention threshold. Large or malformed images are
excluded by extraction limits. Query traffic and Qdrant storage cost on a
representative corpus are unmeasured.

Exact next step: Discuss user scenarios and LLM prompts with the owner. Real
source and expert gates remain open before cultural release.

Cleanup completed or retention reason: The branch and worktree are retained as
the reproducible checked-out integration workspace. The `ccgaps` and
`ccyandextest` disposable Compose projects and their test volumes were removed
after the final audit. Local `main` and `origin/main` include the integration;
the primary checkout's three pre-existing dirty files remain untouched.
