# MVP use cases and prompt guide

This guide turns the [product concept](CONCEPT.md) and the agreed two-role workflow
into testable scenarios. It is also the content source for the chat's starter prompts
and a short in-app "What can I do?" guide. The examples are task templates, not
claims that any particular cultural fact is present in the approved corpus.

## MVP boundaries

- Roles: **user** and **administrator**. Only administrators can inspect and manage
  ingestion state or unpublished source material. Users see approved material only.
- The user's default destination is a text chat with conversation history, an input
  composer, and concrete starter tasks. Model input and output are text in the MVP.
- A secondary materials view lets users browse approved source documents and their
  context. Citations in chat open the exact available source location from that view.
- Generated text distinguishes source-supported facts, interpretations, and new
  creative suggestions. If the approved corpus cannot support a cultural claim,
  the answer says so instead of inventing a citation.
- Administration includes a structured document inventory with tags, source
  metadata, ingestion/approval state, and processing errors. Ingestion and approval
  are planned separately from browsing the inventory.
- Image, audio, music, and video input or generation follow the first text release.
  They are part of the full-concept backlog, with modality-specific source
  representations, embeddings and quality review. They must not be implied to work now.

## Primary user journey

1. The user opens the chat and sees examples of specific creative tasks.
2. The user chooses a starter or writes a brief, including an intended use and any
   region, community, period, or format constraints they know.
3. The system searches approved source material and drafts a text response through
   a server-side model API adapter. The UI shows loading, interruption, and failure
   states without losing the user's brief.
4. The response presents a usable creative result. Cultural claims refer to
   identifiable, accessible source locations; interpretation and invention are
   labelled as such. Unsupported or sensitive requests receive a clear boundary.
5. The user opens a citation to inspect the original document, page/section or
   sheet/row when available, then returns to the conversation.
6. The user can continue the conversation, start a new one, and revisit prior chats.

## Starter tasks

Each starter fills the composer with an editable prompt. The prompt should ask for
both a useful output and its evidence, without asserting that the corpus contains
the requested tradition.

| ID | Label | Editable prompt template | What the result must make clear |
|---|---|---|---|
| UC-01 | Gift concept | "Suggest three contemporary gift concepts connected to [region/community] for [recipient/occasion]. Use only approved sources for cultural details, cite each detail, and flag ideas that are your own interpretation." | Distinct options, intended use, cited cultural basis, creative interpretation. |
| UC-02 | Event concept | "Draft a short event concept for [audience/occasion] inspired by documented practices from [region/community]. Explain the sources and identify any elements that need expert or community review." | Program idea, sources, sensitive-element boundary. |
| UC-03 | Naming direction | "Propose naming directions for [project] connected to [place/community]. Explain the documented words or references used, and do not invent a translation or traditional meaning." | Names as proposals; language and etymology claims require sources. |
| UC-04 | Story or greeting | "Write a short [story/greeting] for [audience] using verified references to [place/community]. Mark newly invented plot or wording separately from documented facts." | Usable text with a clear fact/fiction boundary. |
| UC-05 | Image-generator prompt | "Write a detailed, model-agnostic image prompt for [subject/use] informed by approved materials from [region/community]. Specify composition, visible materials, colors, light and viewpoint. Cite supported cultural details and separate new staging choices." | A copyable text prompt, source citations and an explicit fact/interpretation boundary; no generated image in MVP. |

An explicit request such as "generate a photo" returns a ready-to-use text prompt
for any image generator. The interface may link to [GigaChat](https://giga.chat/)
as one example; Лад does not send the prompt to that service. The
image prompt may use only visually describable source-supported cultural details.
If evidence is missing, the assistant does not invent a culturally specific
prompt. Image generation, quality and third-party usage terms remain outside
this MVP text workflow.
| UC-06 | Explore sources | "What approved materials do you have about [topic], and which ones are most relevant to [task]?" | A source-oriented answer with navigable document references. |

The starter set is a hypothesis. Validate labels and wording with target users and
replace examples that prompt unsupported or stereotyped outputs.

## Boundary scenarios

| ID | Input condition | Expected behavior |
|---|---|---|
| UC-07 | No approved source supports a requested cultural detail | Explain the gap, avoid a fabricated reference, and offer a narrower task or general creative suggestion clearly labelled as unsourced. |
| UC-08 | Sources disagree by region, time, or interpretation | Keep distinctions visible, cite both where permitted, and avoid presenting one account as universal. |
| UC-09 | A source is restricted, unpublished, revoked, or sensitive | Exclude it from user retrieval and citations; do not leak its title or contents through chat or the materials view. |
| UC-10 | A cited source changes or is withdrawn after an answer | Keep the historical citation identity, indicate that the source is no longer available or approved, and do not silently link to a different revision. |
| UC-11 | A text source contains instructions to the model | Treat that text as evidence data, not as a command; do not let it change system rules or reveal secrets. |

## Materials view

The secondary user tab lists **approved** documents with a title, source
organization or author, document type, region/community/time tags where known,
and a concise description. A detail view shows the original
document or a faithful text/table representation and stable locations such as a
section, page, sheet, row, or cell. Filters and search help discovery; they do not
replace chat as the primary interaction.

The first ingestion fixtures determine which file formats can be viewed directly.
If a format cannot be rendered faithfully, show an explicit limitation and provide
the approved original file through an authorized route.

## Administrator journey

1. The administrator opens a document inventory grouped or filtered by source,
   type, tags, ingestion state, and approval state.
2. A document detail shows origin, attribution, version, extracted structure,
   table locations, processing errors, and whether it can appear in user retrieval.
3. Authorized ingestion creates a new revision and processes it outside the request
   path. The administrator reviews extraction and metadata before approval.
4. Approval makes an exact revision eligible for user search and chat; revocation
   removes it from both. Reprocessing does not erase the prior revision's audit trail.

## Interface map

| Area | Primary content | Key behavior |
|---|---|---|
| User: Chat (default) | Chat list, main dialogue, composer, starter prompts and help entry | Responsive and keyboard-accessible; source references are clickable and understandable without color. |
| User: Materials | Approved document list and source detail | Filters, stable location links, return path to the originating chat. |
| Administrator: Documents | Inventory, structure, tags, status and errors | Unpublished content stays admin-only; review and approval actions are explicit. |

Follow [`DESIGN.md`](../../DESIGN.md) for visual tokens and states. The chat should
keep a familiar list-and-dialogue layout while using the project's typography,
palette, borders, focus treatment, and restrained ornament.

## Open decisions to resolve before implementation

- Which region/community, creative tasks, and approved source collection define the
  first evaluable slice?
- Is user chat history tied to an account, or is a temporary guest mode permitted?
- Which model API provider and embedding service meet cost, data-location, language,
  privacy, and reliability requirements?
- Which document formats and table structures occur in the initial fixtures, and
  how should the original files be shown or downloaded in the document reader?
- Who may approve or revoke a source, and what evidence establishes "verified"?
- What retention and deletion rules apply to chat briefs, source files, extracted
  text, and model-provider requests?

These are tracked as decision and validation tasks in the
[MVP master plan](../exec-plans/active/creative-rag-mvp.md).
