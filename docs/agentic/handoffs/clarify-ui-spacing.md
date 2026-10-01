# Plain-language UI and spacing handoff — 2026-10-02

## Objective and actual status

Remove internal use-case codes from visible UI, make administrative codes readable,
and correct uneven spacing in the chat at phone, tablet and desktop widths. The
isolated implementation was verified, fast-forwarded into `main`, and pushed to
`origin/main`.

## Worktree / branch / base SHA

- Primary: `/mnt/BlackfireZZZ/Hackatons/CultureChamp`, `main`, base
  `3a837aabf7baf34cc5a74d41aafd40117a82ff9d`. Its user-owned concept edit
  and untracked roadmap remain untouched.
- Isolated: `/mnt/BlackfireZZZ/Hackatons/CultureChamp-frontend-completion`,
  `agent/clarify-ui-spacing`, from the same base SHA.

## Owner of changed files

This slice owns `DESIGN.md`, frontend UI, frontend tests and visual baselines,
and this handoff.

## Changed contracts and files

- Starter cards and the task guide show descriptive names only. Internal IDs
  remain in starter data and statistics transport; statistics renders names.
- Source inventory and detail translate status, decision, tag and file-format
  codes into Russian labels. The inventory heading and introductory copy use
  clearer wording.
- At tablet width, the history rail becomes a labelled menu so the task column
  stays wide. Cards use three aligned columns where space permits. The composer
  is shorter, restoring a gap below the visible cards. Phone copy and ornament
  spacing were adjusted and user messages no longer carry a side indent.
- `DESIGN.md` records plain-language labels and chat spacing rules.
- The visual suite now covers the starter guide in both themes at 360, 768,
  1280 and 1440 px, alongside the existing canonical screens.

## Decisions and supporting evidence

At 768 px, the prior fixed history rail left the task column too narrow. At
360 px, the heading and composer pushed examples out of view. Rendered snapshots
before and after the change were inspected at phone, tablet and desktop widths.
The backend and analytics identifiers are preserved because they are contracts;
only presentation maps them to readable names.

## Verification commands and observed results

- `make check`: passed architecture, backend Ruff/mypy/94 tests (17 database
  skips), frontend lint/23 tests/build, ML Ruff/mypy/20 tests, contract check
  and Compose configuration.
- `npm run test:e2e`: six passed; the environment-gated live test was skipped.
- `npx playwright test e2e/visual.e2e.ts --update-snapshots`: passed; canonical
  screenshots updated and eight starter-guide screenshots added.
- `git diff --check`: passed.

## What remains unverified and why

Target users have not reviewed the revised wording and spacing. Linux Chromium
screenshots do not establish rendering on other platforms.

## Risks and open questions

At phone width the examples remain scrollable above the persistent composer;
the guide provides a complete list without scrolling the chat.

## Exact next step

The integrated code commit is `6bbf3bc52999f0eda7fb230c1dd7cdb38901530c`.
Continue review with target users. The primary checkout's user-owned changes to
`.env.example`, the concept draft, and the roadmap draft were preserved.

## Cleanup completed or retention reason

Retain the isolated worktree and branch as review evidence after integration.
