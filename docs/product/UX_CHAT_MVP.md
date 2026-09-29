# MVP chat, materials, and administration interface plan

## Status and scope

U01 review draft based on [the concept](CONCEPT.md), [use cases](USE_CASES.md),
[S03](../decisions/0003-access-model-data.md), and the
[S01 proposal](FIRST_CORPUS_SLICE.md). The first slice concerns Indigenous peoples
of Primorye and three **text** briefs:
a museum introduction about changing practices, a public conversation about
environment and ways of life, and an editorial brief on material culture. Two PDF
articles are candidates only. Neither their rights nor cultural approval is
established, so the user materials view starts empty. UC-01 gifts and UC-03 naming
remain general product starters, but this candidate corpus does not support them;
the eventual response must state the evidence gap. Sample interface text must not
imply approval or community endorsement.

## Navigation and content hierarchy

1. **Chat** is the signed-in user home: conversation list, current dialogue,
   editable brief, six starter tasks, and a reachable "What can I do?" guide.
2. **Materials** is secondary: only approved sources, then exact revision detail
   with author/origin, rights, context, and page/section or table locator.
3. **Administrator / Documents** is a separate server-protected area: inventory,
   processing/review state, exact revision, structure, tags, rights, sensitivity,
   and errors. Approval and revocation are explicit actions after source policy
   and APIs exist. The UI never decides visibility.
4. A citation carries `revision_id + locator`; opening it preserves the originating
   chat location. Missing or withdrawn material gets an honest unavailable state,
   never a silent redirect to a newer revision.

## Responsive wireframes

| Width | User chat | Materials | Administrator |
|---|---|---|---|
| 360 px | 16 px side padding; top bar with Chat, Materials, theme and a 44 px conversation-list button. List opens a labelled drawer. Dialogue is one column; composer remains in document flow above mobile keyboard. Starters form one scrollable column. | Search, filter button and approved-only list stack; filters open a labelled sheet. Detail is one reading column with source metadata before content and a Back to chat link. | Inventory list is cards with title, revision ID and **text** state; filter sheet and detail are separate screens. No dense desktop table or inline approval control. |
| 768 px | 24 px side padding; 240 px conversation rail and remaining dialogue when space permits. Starter cards use two columns. Composer stays below dialogue. | Filter/search row above two-column results; detail keeps a 720 px maximum reading width. | Filter bar and compact list; detail opens as a full page so structure and errors remain legible. |
| 1280 px | 32 px page edges; 280 px list rail, flexible dialogue column capped near 760 px, optional quiet right margin. No separate right "AI" panel. | Search/filter row plus results list; source detail has reading column and a narrow metadata rail outside it. | 300 px filter/list rail and revision detail. Metadata, structure and errors use labelled sections, not color-only badges. |
| 1440 px | 48 px page edges and max 1280 px content; list 300 px, dialogue max 760 px; spare space is whitespace rather than expanded line length. | Max 1280 px shell; result/detail proportions remain as at 1280. | Max 1280 px shell; inventory and detail retain readable column widths. |

At every width the header and all controls remain reachable without horizontal
scrolling. A single abstract stitched trim may mark the shell; decoration stays
outside the reading column. Use the light/dark semantic tokens, Oswald headings,
Noto Sans body, square controls, 44 px targets, and visible 2 px focus in
[DESIGN.md](../../DESIGN.md). No motif is attributed to a community without a
documented source.

## Keyboard and state paths

| Flow | Keyboard path | Loading / empty / error / success |
|---|---|---|
| Chat | Tab to conversation list or its drawer button, starters, editable textarea, Send, help. Enter sends; Shift+Enter inserts a line. Escape closes drawers and returns focus to trigger. | Empty chat shows one task action. Pending send keeps draft visible and announces progress. Timeout preserves draft with Retry. Successful answer is announced without forcing focus away. |
| Starter guide | Help button opens a labelled dialog; Tab traverses UC-01–UC-06, Enter fills composer, Escape closes and restores focus. | Guide is available before any conversation. Choosing a starter never submits it. |
| Materials | Tab through search/filter, result, source locator and Back to chat. Escape closes filter/detail overlays. | Empty: no approved materials yet. Loading: text status. Error: retry. Unavailable revision: explicit withdrawal/unavailability. |
| Admin | Tab through filter, revision link, sections, then explicit review action. Confirmation requires focusable Cancel/Confirm. | Loading and processing states use text. Empty inventory explains import status. Errors identify the failed operation without source text leakage. Success confirms exact revision ID and state. |

All dialogs and drawers require focus containment and restoration when implemented.
No route visibility substitutes for direct API authorization. Reduced-motion mode
removes decorative movement while preserving progress text.

## Delivery boundary

The initial interface can show deterministic **demo** conversations and an empty
approved-material state. It must label them as previews and make no real citation
claim. U02 needs G04; U04 needs C09; U06 needs C08/C10. These remain integration
tasks even if the visual shell exists.
