---
version: alpha
name: CultureChamp
description: "A culturally grounded creative generation service. Warm editorial interfaces meet cross-stitch-inspired ornament, with equal-quality dark and light themes."
colors:
  dark-bg: "#080706"
  dark-surface: "#12100C"
  dark-surface-raised: "#1A1711"
  dark-text: "#F4E8BE"
  dark-text-muted: "#B9AA7C"
  dark-accent: "#D6C46C"
  dark-accent-strong: "#BC923F"
  dark-border: "#5D4A24"

  light-bg: "#F4EAD1"
  light-surface: "#FFF8E7"
  light-surface-raised: "#EDE0BE"
  light-text: "#1A1710"
  light-text-muted: "#665A42"
  light-accent: "#8E5A16"
  light-accent-strong: "#704010"
  light-border: "#CBB887"

  semantic-success: "#557A45"
  semantic-warning: "#9A651A"
  semantic-danger: "#A64232"
  semantic-info: "#496D7A"

typography:
  display-xl:
    fontFamily: "Oswald, Arial Narrow, sans-serif"
    fontSize: 64px
    fontWeight: 600
    lineHeight: 0.98
    letterSpacing: "0.025em"
  display-lg:
    fontFamily: "Oswald, Arial Narrow, sans-serif"
    fontSize: 48px
    fontWeight: 600
    lineHeight: 1
    letterSpacing: "0.02em"
  heading-md:
    fontFamily: "Oswald, Arial Narrow, sans-serif"
    fontSize: 32px
    fontWeight: 500
    lineHeight: 1.08
    letterSpacing: "0.015em"
  heading-sm:
    fontFamily: "Oswald, Arial Narrow, sans-serif"
    fontSize: 24px
    fontWeight: 500
    lineHeight: 1.15
    letterSpacing: "0.01em"
  label:
    fontFamily: "Oswald, Arial Narrow, sans-serif"
    fontSize: 14px
    fontWeight: 600
    lineHeight: 1.2
    letterSpacing: "0.06em"
  body-lg:
    fontFamily: "Noto Sans, Arial, sans-serif"
    fontSize: 18px
    fontWeight: 400
    lineHeight: 1.55
    letterSpacing: "0em"
  body-md:
    fontFamily: "Noto Sans, Arial, sans-serif"
    fontSize: 16px
    fontWeight: 400
    lineHeight: 1.5
    letterSpacing: "0em"
  body-sm:
    fontFamily: "Noto Sans, Arial, sans-serif"
    fontSize: 14px
    fontWeight: 400
    lineHeight: 1.45
    letterSpacing: "0em"

spacing:
  xxs: "4px"
  xs: "8px"
  sm: "12px"
  md: "16px"
  lg: "24px"
  xl: "32px"
  xxl: "48px"
  section: "80px"

rounded:
  none: "0px"
  xs: "2px"
  sm: "4px"
  md: "6px"
  full: "999px"

components:
  button-primary-dark:
    backgroundColor: "{colors.dark-accent}"
    textColor: "{colors.dark-bg}"
    borderColor: "{colors.dark-accent}"
    rounded: "{rounded.xs}"
  button-primary-light:
    backgroundColor: "{colors.light-text}"
    textColor: "{colors.light-bg}"
    borderColor: "{colors.light-text}"
    rounded: "{rounded.xs}"
  card-dark:
    backgroundColor: "{colors.dark-surface}"
    textColor: "{colors.dark-text}"
    borderColor: "{colors.dark-border}"
    rounded: "{rounded.sm}"
  card-light:
    backgroundColor: "{colors.light-surface}"
    textColor: "{colors.light-text}"
    borderColor: "{colors.light-border}"
    rounded: "{rounded.sm}"
---

# CultureChamp — Design Contract

> **One-line design language:** a culturally grounded creative workspace built with the visual grammar of embroidery — warm black or unbleached linen, restrained gold/ochre thread, tall condensed display type, geometric cross-stitch ornament, and occasional hand-drawn arrows — while the actual product remains clear, fast, task-first, and source-aware.

This file is the visual source of truth for frontend work. It is intentionally written as a contract for both humans and coding agents.

The product source of truth is [`docs/product/CONCEPT.md`](docs/product/CONCEPT.md).
Product examples below describe optional patterns; they do not expand the MVP scope.

**Normative language:** `MUST` / `MUST NOT` are hard rules. `SHOULD` / `SHOULD NOT` are defaults that require a reason to break. `MAY` is optional.

**Token precedence:** values in YAML front matter are normative. The prose below explains when and why to apply them. Do not create a new color, radius, type style, shadow, or ornament treatment just because a single screen seems to need one; reuse the closest existing token first.

The supplied festival poster is the primary visual reference for mood: black field, warm yellow-gold embroidery framing, narrow display lettering, and a loose hand-drawn directional arrow. It is a reference, not a production asset and not a template to copy literally.

### Product context

CultureChamp helps users turn a practical creative task into a contemporary result
grounded in verified cultural heritage sources. The primary interface should make
the task, generated result, source basis, and cultural context understandable.
Source exploration may support this workflow; a map or archive browser is optional.

The site MUST feel like **cultural knowledge made usable for creative work**, without
looking like a museum portal, government service, generic travel landing page, or
generic AI dashboard.

### Design priorities

In priority order:

1. **A clear creative task and usable result**
2. **Legible cultural sources, context, and traceability**
3. **A distinctive embroidery-based identity**
4. **Editorial storytelling**
5. Decorative flourish

If decoration competes with content, decoration loses.

---

## Overview

### Core character

The design combines two layers:

- **Contemporary product layer:** clear hierarchy, predictable interaction, a direct task-to-result flow, readable source context, accessible controls.
- **Textile identity layer:** cross-stitch-like geometry, border ornament, warm thread colors, narrow poster typography, and rare hand-drawn annotation.

The result SHOULD feel crafted and culturally grounded without pretending to reproduce one specific ethnic tradition.

### Cultural treatment

The embroidery language is deliberately **pan-regional and abstract**.

- Use geometric, botanical, animal, star, branch, grain, and textile-grid forms only when they are either generic abstractions or based on a documented source.
- MUST NOT invent a symbol and label it as belonging to a specific people, region, religion, or tradition.
- MUST NOT mix recognizable sacred, ritual, heraldic, or culturally specific symbols merely for decoration.
- When a motif is explicitly tied to a named tradition, the asset SHOULD carry provenance in its source file or metadata: origin, source/reference, and author/license if applicable.
- Cultural photography and illustrations MUST be credited when the source requires it.
- Avoid a fake “old Russia” or “folk theme park” aesthetic. The product is about living culture, including contemporary local scenes.

### Visual budgets

Agents follow budgets better than vague adjectives. Apply these limits:

- **One dominant accent family per screen:** warm gold/ochre.
- **At most two ornament zones visible in one viewport.**
- **At most one hand-drawn directional arrow visible in one viewport.**
- **At most one display-font hero moment per page.**
- Decorative embroidery SHOULD occupy **no more than ~25% of the visible area** on ordinary content pages. Landing/manifesto pages MAY reach ~35%.
- Cards, controls, and map UI MUST NOT each receive their own unique folk decoration.

### Source-of-truth behavior for agents

Before creating or changing frontend UI, an agent MUST:

1. Read this file.
2. Reuse existing design tokens and shared components.
3. Preserve the same visual logic in both themes.
4. Check the result at mobile, tablet, and desktop widths.
5. Check keyboard focus and reduced-motion behavior.
6. Avoid “improving” the design by adding generic gradients, glassmorphism, large radii, or extra accent colors.

A missing design decision is not permission to improvise a new mini-design-system. Choose the nearest established pattern, and only update this file when the design system itself is intentionally changed.

---

## Colors

### Palette intent

The reference image is dominated by near-black, pale thread-gold, ochre, and muted linen tones. The palette here translates that mood into accessible UI tokens.

The two themes are equal citizens:

- **Dark theme:** closest to the poster reference. Near-black canvas with warm cream/gold text and ornament.
- **Light theme:** unbleached linen/parchment canvas with near-black ink and deeper ochre accents.

The light theme MUST NOT become a generic white SaaS theme. The dark theme MUST NOT become a neon “tech” theme.

### Dark theme roles

- `dark-bg` — page canvas.
- `dark-surface` — cards, search panels, drawers.
- `dark-surface-raised` — active or floating surfaces.
- `dark-text` — primary text.
- `dark-text-muted` — metadata, captions, secondary labels.
- `dark-accent` — primary thread/gold accent, active controls, ornament.
- `dark-accent-strong` — secondary embroidery tone and occasional emphasis.
- `dark-border` — quiet separators and component borders.

Primary text, muted text, and accent colors are chosen to remain comfortably legible on the near-black background. Do not lower their opacity until contrast becomes marginal.

### Light theme roles

- `light-bg` — page canvas, intentionally warm.
- `light-surface` — cards and form surfaces.
- `light-surface-raised` — selected or raised surfaces.
- `light-text` — primary ink.
- `light-text-muted` — metadata and secondary copy.
- `light-accent` — interactive ochre accent.
- `light-accent-strong` — strong emphasis and selected ornament.
- `light-border` — separators and quiet frames.

### Theme implementation

Frontend code SHOULD expose semantic CSS variables and remap them per theme rather than hard-code theme-specific hex values inside components.

Recommended semantic layer:

```css
--color-bg
--color-surface
--color-surface-raised
--color-text
--color-text-muted
--color-accent
--color-accent-strong
--color-border
```

Theme selection SHOULD:

- respect `prefers-color-scheme` on first visit;
- allow a visible manual toggle;
- persist an explicit user choice;
- avoid a flash of the wrong theme during hydration.

### Color rules

- MUST NOT use pure white as the main light background.
- SHOULD NOT use pure black except in external media that requires it.
- MUST NOT use gradients as a general decoration.
- MUST NOT introduce purple/blue “AI” gradients.
- Semantic success/warning/danger/info colors are for meaning, not branding.
- Never rely on color alone for state.
- Ornament MAY use `accent` + `accent-strong` + a low-emphasis text/border tone, but SHOULD NOT become rainbow embroidery.

---

## Typography

### Typeface contract

**Display:** `Oswald` is the implementation baseline because it provides the tall, compressed poster character needed here and supports Cyrillic. It is not claimed to be the exact font in the reference image.

**Body:** `Noto Sans` provides a calm, readable counterweight and broad language coverage.

If the team later approves a custom display typeface closer to the reference, agents MUST replace the display token centrally rather than sprinkling a new font across individual components.

### Display type

Use display typography for:

- hero titles;
- section titles;
- navigation emphasis;
- category labels;
- short calls to action.

Display text SHOULD often be uppercase or small caps-like in feeling, but do not uppercase long phrases or body copy.

The poster feeling comes from **condensation + controlled tracking + scale**, not from novelty pseudo-Slavic letterforms.

MUST NOT use:

- faux Old Church Slavonic fonts;
- distressed “ethnic” novelty fonts;
- decorative display type for paragraphs;
- more than two font families in the product UI.

### Body type

Creative results and source context MUST be comfortable to read.

- Long-form measure: ~60–75 characters per line.
- Default body line height: 1.5–1.6.
- Metadata may use `body-sm`.
- Do not shrink informative text below 14px on desktop/mobile UI.
- Native-language names SHOULD be preserved where data permits; transliteration/translation may be secondary, not a visual replacement.

### Responsive type

On screens below 640px:

- `display-xl` SHOULD clamp down to ~42–48px.
- `display-lg` SHOULD clamp down to ~36–40px.
- headings MAY wrap; never compress letter spacing until letters collide.
- body sizes remain unchanged unless a platform accessibility setting requires larger text.

A fluid implementation with `clamp()` is preferred over multiple one-off media-query sizes.

---

## Layout

### Grid

Base spacing rhythm: **8px**, with a 4px half-step only for fine alignment.

Recommended page geometry:

- Mobile: 16px side padding.
- Tablet: 24px side padding.
- Desktop: 32–48px side padding.
- General content max width: 1200–1280px.
- Reading column max width: 720–760px.

Do not center every piece of content. The reference has strong asymmetry: large title area, directional gesture, and framed edges. Use this principle deliberately.

### Embroidery frame

Desktop layouts MAY use vertical or corner embroidery rails that echo the poster.

Rules:

- Side rails are decorative, not structural navigation.
- Rails MUST be outside the primary reading column.
- On widths below ~1024px, reduce complexity.
- On mobile, side rails SHOULD collapse into a top/bottom trim, corner fragment, or section divider.
- Never let an ornament reduce tap targets, overlap copy, or cover map controls.

### Optional map screens

If a map is introduced to support source exploration, it is a functional surface,
not a decorative poster or the default primary workflow.

- Ornament belongs around the shell, not over dense geographic content.
- Floating panels should use standard surfaces and borders.
- Selected cultural entries MAY use a stitched/diamond marker silhouette, but markers must remain readable at a glance.
- Cluster markers MUST prioritize counts and interaction over decoration.
- Do not place an ornamental frame between the user and essential native map controls.
- On mobile, prefer a map + bottom sheet pattern.

### Editorial/content screens

Long-form cultural entries SHOULD use:

- strong title;
- location + culture/language metadata;
- source/author/provenance area;
- documentary media;
- restrained ornament at section opening or ending.

A page should not look like every paragraph is printed on a folk postcard.

### Search and filters

When source search is available, it MUST remain obvious and usable without
displacing the creative task.

- Search field can be large and prominent.
- Filter chips SHOULD be rectangular or softly squared, not generic pill clouds.
- Selected filters use accent + explicit state icon/check where useful.
- Long filter sets should collapse into a drawer/sheet on mobile.

### Responsive behavior

Canonical review widths:

- 360px — small mobile
- 768px — tablet
- 1280px — desktop
- 1440px+ — wide desktop

The layout MUST work at all four without horizontal scrolling, clipped ornament, or unreachable controls.

---

## Elevation & Depth

This design is primarily **flat and layered by contrast**, not by shadow.

### Rules

- Default cards: 1px border, no shadow.
- Floating map/search panels MAY use one restrained shadow if necessary for separation.
- Avoid soft “floating SaaS card” stacks.
- No glassmorphism.
- No frosted transparent panels over cultural photography unless readability requires a simple solid/near-solid scrim.
- Depth should come from background/surface contrast, borders, overlap, and scale.

Recommended maximum shadow when truly needed:

```css
box-shadow: 0 8px 24px rgba(0, 0, 0, 0.18);
```

In light theme, reduce opacity if the shadow feels muddy.

---

## Shapes

### Geometry

The base geometry is textile-derived:

- square;
- rectangle;
- diamond;
- stepped/pixel corners;
- line-based botanical curves;
- occasional hand-drawn curve for annotation.

Default radius is `2–4px`. `6px` is the practical upper bound for ordinary panels.

MUST NOT turn the interface into a collection of large 16–32px rounded cards.

`full`/pill radius is reserved for controls whose semantics genuinely benefit from it (for example, a compact switch), not for the default badge/chip style.

### Embroidery / cross-stitch grammar

Core ornament assets SHOULD be authored as SVG and aligned to a consistent internal stitch grid. The visible mark MUST be an X-shaped stitch; a smooth outline with scattered crosses does not satisfy the embroidery treatment. Arrange stitches into complete motifs so that the pattern remains recognizable at its rendered size.

Preferred characteristics:

- visible thread crosses with a consistent stitch pitch;
- stepped diamonds, stems, and leaves formed by the crosses themselves;
- mirrored or rotational symmetry;
- branch/leaf/flower abstractions;
- sparse animal or object silhouettes when justified;
- 1–3 thread colors per motif;
- hard edges, not blurry raster filters.

Implementation rules:

- Prefer `currentColor` or CSS variables so the same SVG works in both themes.
- Keep individual motifs reusable and composable.
- Do not generate a brand-new ornament for every page.
- Do not use low-quality raster screenshots of textile patterns as UI chrome.
- Decorative SVGs MUST be `aria-hidden="true"` unless they communicate actual information.

For the MVP chat, embroidery MUST be a recognizable visual element. The empty
chat uses one substantial, fully cross-stitched botanical and geometric panel
beside the task on wide screens; at narrow widths it becomes one horizontal
stitched band above the task. An existing dialogue uses the same band as a quiet
header. Reuse the same stitch unit, palette, and motif logic in both variants.
This is one ornament zone in each view and stays outside answer text, citations,
and the composer. The motif is an original pan-regional abstraction: its leaves
and diamonds make no claim about a named people's tradition. Review the actual
rendered light and dark screens at 360, 768, 1280, and 1440 px; if the motif
disappears at ordinary viewing size, increase its clarity within the two-zone
and area budgets rather than adding unrelated decorations. Keep chat controls
near-square to suit the stitch grid; round icon controls remain an option when
their semantics and touch target warrant it.

### Hand-drawn arrow

The loose arrow from the reference is a signature secondary device.

Use it to:

- point from a short annotation to a CTA;
- visually connect two steps on a landing page;
- call attention to an onboarding action.

Rules:

- One visible arrow per viewport by default.
- Stroke: ~2–3px on desktop, ~2px mobile.
- Open arrowhead, imperfect curve, no filled cartoon arrow.
- Color: muted text or accent, never semantic danger/success.
- It MUST NOT replace standard navigation icons.
- If animated, draw once in ~450–700ms; do not loop.
- Under `prefers-reduced-motion: reduce`, render the final static path immediately.

### Texture

No texture by default.

A nearly imperceptible woven/paper texture MAY be used on large static hero backgrounds at very low opacity, but it MUST NOT reduce text contrast or appear over the map, forms, or dense archive content.

---

## Components

### Navigation

Desktop navigation SHOULD be calm and typographic.

- Logo/wordmark left.
- The primary creative task is easy to reach.
- Source exploration is easy to reach when available.
- Theme toggle is visible but not louder than the core content.
- Active item may use an underline, short stitched rule, or accent text.

Mobile navigation SHOULD use a conventional menu/drawer or bottom navigation if the information architecture justifies it. Do not invent obscure gesture-only navigation.

### Buttons

**Primary**
- Dark theme: gold/linen fill with near-black text.
- Light theme: near-black fill with warm-light text.
- Square/near-square corners.
- Clear hover/pressed/focus states.
- Labels may use the display/label style.

**Secondary**
- Transparent/solid surface with 1px border.
- Accent or primary text.
- No heavy shadow.

**Text action**
- Plain text with underline or directional mark.
- Must retain a visible hover/focus treatment.

Buttons MUST have a minimum touch target of 44×44px.

### Cards

Default cultural entry cards:

- thin border;
- no shadow;
- optional documentary image;
- title;
- location;
- category/type;
- concise excerpt;
- source/review status when relevant.

A decorative stitched corner or short motif MAY appear on featured cards only.

Do not apply a different embroidery pattern to every category. Categories should be differentiated primarily by text/iconography/data, not faux-ethnic decoration.

### Tags and badges

- Prefer squared tags with 2–4px radius.
- Use borders and typography more than filled rainbow colors.
- Keep semantic status badges distinct from cultural taxonomy.
- Avoid excessive chip density.

### Inputs

Inputs MUST look like functional product controls, not themed props.

- 1px border.
- Solid theme surface.
- 44px minimum control height.
- Clear label outside the field when possible.
- 2px visible focus ring using accent.
- Errors include text + icon, not red border alone.

Search MAY be larger and more prominent than standard inputs.

### Cultural entry detail

A detail view SHOULD make provenance visible without making the page feel bureaucratic.

Recommended information order:

1. Name/title
2. Place / region
3. Culture / language / scene / category
4. Short description
5. Media
6. Story/context
7. Sources / contributor / verification metadata
8. Related places and entries

### Map markers and callouts

Markers MUST be visually distinct in light and dark map contexts.

- Default marker: simple geometric/stitch-inspired symbol.
- Hover: clear enlargement or outline.
- Selected: accent-strong + visible outline.
- Callout card: standard surface, no over-decoration.
- Marker icons MUST remain comprehensible at small sizes.

### AI assistant

Generation is the central product workflow, not a separate sci-fi experience.

- No purple gradient, glowing orb, robot mascot, or glass chat panel.
- Messages should be rectangular editorial blocks with subtle borders.
- Generated results SHOULD show source/provenance links and distinguish sourced
  cultural facts from interpretation and new creative content.
- Suggested prompts MAY be introduced with the hand-drawn arrow or a short embroidered divider.
- The generation interface must keep the creative result and cultural basis legible.

### Contribution flow

Community contribution screens SHOULD feel welcoming but serious.

- Step structure must be explicit.
- Save/progress state must be visible.
- Ask for provenance/source information in a clear way.
- Preview the resulting public entry before submission.
- Avoid gamification visuals that trivialize cultural material.

### Empty, loading, and error states

- Empty: one short message + one next action + optional small ornament.
- Loading: skeletons or compact progress; optional stitch-line motif, but no distracting animation.
- Error: clear explanation and recovery action.
- Never use decorative animation as the only loading feedback.

### Icons

Use one coherent icon family across the product. If no library is established, a simple outline set is preferred.

- Stroke ~1.5–2px.
- Avoid mixing filled, 3D, emoji, and outline icons.
- Cultural symbols are not a generic icon library; do not use them decoratively without meaning.

### Photography and illustration

Prefer documentary, place-specific, contributor-provided, archival, or commissioned visual material.

MUST NOT default to generic stock imagery of “traditional people in costume” when the content is about living culture.

Do not apply one nostalgic color grade to all cultures and eras. Media should retain its own historical and geographic character.

---

## Do's and Don'ts

### Do

- **DO** use the embroidery frame as the strongest recurring brand device.
- **DO** keep the central product UI clear for the creative task, result, and sources.
- **DO** use dark near-black + warm gold as the reference-led dark identity.
- **DO** make the light theme feel like linen/paper, not pure white.
- **DO** use a tall condensed display face for short headings and labels.
- **DO** use hand-drawn arrows rarely and intentionally.
- **DO** keep ornament SVG-based, reusable, theme-aware, and accessible.
- **DO** preserve cultural provenance and distinguish generic abstract ornament from specifically sourced motifs.
- **DO** test both themes and all canonical widths before calling a frontend change complete.
- **DO** keep focus states visible and respect `prefers-reduced-motion`.

### Don't

- **DON'T** use generic SaaS gradients, glassmorphism, neon AI colors, or giant rounded cards.
- **DON'T** fill every blank area with ornament.
- **DON'T** place embroidery over dense map data or important controls.
- **DON'T** invent “ethnic-looking” symbols and assign them to a culture.
- **DON'T** use novelty pseudo-Slavic fonts.
- **DON'T** make every category a different color or motif.
- **DON'T** use hand-drawn arrows as normal navigation controls.
- **DON'T** sacrifice readability to mimic the poster literally.
- **DON'T** allow dark and light themes to become two different design systems.
- **DON'T** introduce new design tokens in a one-off component without an intentional system-level decision.

### Definition of done for any frontend screen

Before merging a screen or component, verify:

- [ ] Uses only approved color/type/spacing/radius tokens, or intentionally updates this contract.
- [ ] Looks coherent in both dark and light themes.
- [ ] Works at 360, 768, 1280, and 1440+ px widths.
- [ ] Ornament does not interfere with content or controls.
- [ ] No more than the allowed ornament/arrow/display-type budget is used.
- [ ] Text and interactive states meet WCAG 2.2 AA contrast expectations.
- [ ] All interactive elements are keyboard reachable.
- [ ] Focus state is visible.
- [ ] Touch targets are at least 44×44px where applicable.
- [ ] Reduced-motion mode is respected.
- [ ] Decorative SVGs are hidden from assistive technology.
- [ ] Cultural motifs with specific attribution have documented provenance.
- [ ] No generic gradients, glassmorphism, excessive radii, or ad-hoc accent colors were introduced.
