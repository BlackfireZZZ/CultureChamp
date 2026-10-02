# Image prompt MVP handoff

Objective and actual status: Explicit image-making requests now return a detailed,
model-agnostic text prompt grounded in approved evidence. The frontend labels it
as a prompt and offers an optional GigaChat link. Implementation and checks pass;
integration to `main` follows this handoff.

Worktree / branch / base SHA: `/home/blackfire/.codex/worktrees/0eb7/CultureChamp`,
`agent/image-prompt-mvp`, `4e8dc2cb6bd0cd7dbb0b00e905134605599208db`.
Primary path: `/mnt/BlackfireZZZ/Hackatons/CultureChamp`, `main`; its user-owned
`.env.example`, `docs/product/CONCEPT.md` and untracked
`docs/product/POST_MVP_ROADMAP.md` edits are preserved.

Owner of changed files: This integration agent owns the branch changes in
`backend/app/application/generation.py`, the fake model adapter, generation tests,
`frontend/src/features/chat/`, the UC-05 starter, product use-case documentation,
visual snapshots, this handoff and the master plan.

Changed contracts and files: The internal model payload adds `requested_output`.
The persisted chat API is unchanged. Image requests use the existing JSON fact,
interpretation, creative and citation contract; only the third rendered section
is labelled `Image prompt`. The link opens GigaChat in a new tab without sending
the prompt.

Decisions and supporting evidence: The image prompt is intended for any generator,
with no provider-specific syntax. GigaChat is an optional example because its
[official help](https://giga.chat/help/articles/how-to-generate-images) documents
image generation. No image service is integrated or required for the MVP.

Verification commands and observed results: Focused generation tests and the
frontend component test passed. `make check` passed with 101 backend tests
(18 skipped because optional PostgreSQL/Qdrant services were stopped),
25 frontend tests and 20 ML tests, plus Ruff, mypy, frontend lint/build,
architecture, OpenAPI and Compose checks. `npm run test:e2e --
e2e/shell.e2e.ts e2e/visual.e2e.ts` passed all 6 checks after updating the 14
affected starter snapshots; representative mobile and desktop images were
inspected. A synthetic live YandexGPT request using the private environment
returned `grounded`, one exact citation and an image-prompt section; it used no
real cultural source and did not print its private content or credentials.

What remains unverified and why: Synthetic tests cannot establish the cultural
accuracy or practical image quality of model output. Real approved sources,
expert review and target-user prompt evaluation remain open.

Risks and open questions: Intent routing requires explicit image and action
words in Russian or English. The cultural fact and citation fields are validated,
but the creative prompt's visual claims still require human review. No third-party
image generator receives data automatically.

Exact next step: Fast-forward this verified branch into `main`, push the result,
then discuss example user briefs and prompt quality with the owner.

Cleanup completed or retention reason: The isolated worktree and branch are
retained for traceability. The primary checkout's dirty files are untouched.
