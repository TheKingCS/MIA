# MIA OS: visual identity, the glass design system and the appearance engine (prompt 24, phase 1)

*Claude (Opus), 2026-11-15, answering Zac's handoff (kept verbatim:
[`prompts/24_VISUAL_IDENTITY_GLASSMORPHISM_APPEARANCE_ENGINE.md`](prompts/24_VISUAL_IDENTITY_GLASSMORPHISM_APPEARANCE_ENGINE.md)).
The handoff's own phase 1: the audit, where the design system belongs, the schemas and contracts, the plan. Nothing is
built here. The handoff calls its direction approved; the architecture choices below are proposed (DEC-0183,
DEC-0184), and three questions wait on Zac (Q-37 to Q-39). The dashboard reference image it names didn't arrive in
the session; the plan doesn't depend on it, but the presets' final values do. Muse owns the look (DEC-0017, DEC-0023):
the engine is Claude's, the values are Muse's to refine.*

## A. Audit: what exists (handoff §13, 1 to 4)

**One front end, one token file.** Every MIA surface on every device is the web front end (`web/`, DEC-0012,
DEC-0124); the Qt screens are the classic view. Values live in one place, `web/tokens.css` (238 lines: colours as
`--rgb-*` triplets, panels, ink, accent, meaning colours, type scale times `--scale`, radii, motion), and eleven style
sheets (6,917 lines) use them. **No new framework is needed or wanted** (the handoff agrees).

**A theme engine already exists** (DEC-0136, `core/themes.py`, 501 lines):

| Handoff asks for | What exists | Where |
|---|---|---|
| Themes as data, switched at runtime | yes: a theme is the tokens it sets, a material, a backdrop, the 3D room's light; applied by the page, no restart | `core/themes.py`, `web/shell.js` |
| Glass surfaces | one `glass` material (frosted, blurred on screens wider than 860 px, flat on phones for scrolling cost); also solid, chrome, wire | `web/themes.css` |
| A validated interface for any theme (built-in, custom, AI) | `clean_theme` (only allowed tokens, nothing that can break out of CSS or fetch), `build_theme` (refuses an accent that reads as a warning colour, text under 4.5:1 contrast) | `core/themes.py` |
| Preview before applying, tweak, save your own | the Theme Studio: live preview, up to 12 of his own themes, saved through approved, undoable actions | `web/studio.html`, `core/theme_actions.py` |
| Mix one theme's parts with another's | `combine(first, second, parts)`: colours, shape, room, sound, backdrop | `core/themes.py` |
| Backgrounds | backdrop pictures MIA paints (DEC-0140), a backdrop layer per theme with a strength | `core/themes.py`, `body::before` |
| Change by voice | `set_theme`, `wants_theme` ("make it glass"), mixing by voice | `core/assistant_*_actions.py` |
| Meaning colours that no theme can change | amber, red, green, gold, rarity and area hues are not theme tokens; high contrast overrides every theme | DEC-0014, DEC-0136 |
| Accessibility settings | text size, high contrast (`core/accessibility.py`); `prefers-reduced-motion` honoured in 8 style sheets | `web/tokens.css` and others |
| Layouts | two experiences, Spatial and Cards (DEC-0135, `core/display_style.py`); focus presets choose which apps show (`core/focus_presets.py`); the Qt Home's widget registry (`core/dashboard_widgets.py`) | — |
| Orb states | idle, listening, thinking, answered on the glasses, driven by the real voice states | `web/glasses.js` |
| Built-in themes | Stark (default, DEC-0023), Y2K Cyber, Cyberpunk, Glass | `core/themes.py` `THEMES` |

## B. The gaps, each classified

| Handoff section | Class | What's missing |
|---|---|---|
| §2 tokens | Extend | Surface-tier tokens, elevation, gradient and chart-palette tokens; 141 literal colours outside tokens (`docs/design/MIA_DESIGN_SYSTEM.md` §1) to retire |
| §2 five glass surfaces | **Build** | Today a material styles one list of classes alike; the five tiers (primary, secondary, floating, deep, interactive) each with its own opacity, blur, border, light and elevation |
| §3 three independent dimensions | **Build** (on the engine) | A theme bundles colours with environment; colour scheme and layout aren't separate settings (`combine` mixes once, it isn't a live pairing) |
| §3A six presets | Extend | Aquatic, Nebula, Evergreen, Aurelia, Glacial, Eclipse as data (Glass is close to Glacial) |
| §3B status colours in a scheme | Conflict, resolved below | DEC-0136 forbids a theme changing meaning colours |
| §3C layouts | Extend | Navigation position, density, sidebar, Home arrangement as one layout setting beside Spatial/Cards |
| §4 Appearance centre | Extend | The Theme Studio becomes Settings › Appearance with three parts and transparency, blur, density and motion controls |
| §5 living wallpapers | Extend then Defer | Static backdrops exist; light animated ones in phase A7; 3D environments are the Nexus room's line of work (`web/nexus3d.js`) |
| §6 per-app identity | Extend | The `--mod-*` tokens all point at cyan; give each app an atmosphere hue for its own data (proposed in the design system doc, waiting since 2026-11-07) |
| §7 desktop shell | Integrate | MIA's session is the web front end, so it inherits; KDE Plasma and window transitions are Prompt 10's (a Plasma colour scheme from MIA's scheme is a later option) |
| §8 orb states from real activity | **Build** | One presence state from the runtime (listening, thinking, responding, working, council, notification, warning, success), not per-page timers |
| §9 AI customisation | Existing in kind | Through `build_theme`'s checks and approved actions; extend to schemes and layouts |
| §10 reduced transparency, hardware fallback | Extend | A reduced-transparency setting (and the `prefers-reduced-transparency` media query); an effects level (full, light, none) chosen per device |

## C. The architecture (DEC-0184, proposed)

**Where it belongs:** the appearance engine stays in `core/themes.py` (data and validation, no Qt, no web code), served
through `/api/shell`; the design system stays in `web/tokens.css` (values) and `web/themes.css` plus `web/components.css`
(surfaces and components); the page applies it (`web/shell.js`). Apps consume tokens and surface classes only: no app
has its own colours beyond its atmosphere hue. Nothing about appearance enters `core/` beyond data.

**Three dimensions, three person settings, composed at render:**

| Dimension | Setting | Owns | Never touches |
|---|---|---|---|
| Theme (environment) | `display.theme` | the field and panel colours, the backdrop (picture or ambient), ambient light, the surface tiers' material values, the room's light, sounds | accents, layout |
| Colour scheme | `display.scheme` (new) | primary, secondary, tertiary accents, gradients, selection and focus, the chart palette, the orb's colour | meaning colours (below), layout |
| Layout | `display.layout` (new) | navigation position (left, bottom, top), density (comfortable, compact), sidebar (full, icons, hidden), the experience (Spatial, Cards, auto), Home's arrangement | colours |

`appearance(context)` composes them into one cleaned set for the page: the theme's tokens, then the scheme's, each
through `clean_theme`'s rules, then the layout's attributes. Changing one never changes another, so a theme switch
never moves his workspace (§3C). **Existing themes keep working:** each becomes a theme with a matching scheme
(Stark = the Stark environment + the cyan scheme), so nothing he saved is lost.

**Meaning colours stay out of schemes** (§3B against DEC-0136): a scheme may set its accents and its chart palette, not
amber (needs you), red (errors), green (ok) or gold (rewards). *Recommendation:* a scheme may shift those within their
own hue band for harmony (a warmer amber under Aurelia) only through a checked function that keeps each recognisable
and at contrast; never reassigned. This keeps DEC-0136.

**The five surfaces** (§2), each a token set the theme fills within clamped ranges:

| Tier | Used for | Opacity range | Blur range | Notes |
|---|---|---|---|---|
| Primary glass | an app's main panels | 0.55 to 0.92 | 0 to 24 px | readable body text required |
| Secondary glass | cards, widgets inside a panel | 0.40 to 0.85 | 0 to 16 px | lighter than its parent, never lower contrast |
| Floating glass | menus, popovers, the approval card | 0.80 to 0.97 | 0 to 28 px | always the most opaque: what he must read now |
| Deep glass | hero panels, Home's focus | 0.70 to 0.95 | 0 to 32 px | the strongest elevation |
| Interactive glass | buttons, chips, navigation | 0.30 to 0.80 | 0 to 12 px | its hover, focus, active and disabled states as tokens |

**Readability, checked in code:** `build_theme` already checks text on the panel colour. It grows a check on the
*effective* panel: the panel mixed with the backdrop's average colour at the tier's transparency. Each tier must keep
4.5:1 for body text (WCAG 2.2 AA). A theme that fails is refused with the reason, like an accent that reads as a
warning today.

**Fallbacks** (§10): an *effects* level per device (full, light: no blur and no animated backdrop, none: solid
surfaces), defaulting to light on phones (as today) and full on the PC; *reduced transparency* (his setting or the OS's
`prefers-reduced-transparency`) forces solid surfaces; *reduced motion* (setting or `prefers-reduced-motion`) stops
backdrop movement and orb animation beyond a fade; *high contrast* overrides everything (as today). Animated backdrops
pause when the page is hidden, on battery, or while homeostasis is easing off (DEC-0173).

**The orb's states** (§8) come from one place: a presence state the runtime publishes (`/api/live` already bumps on
change) from real events: the microphone open (listening), a model call running (thinking), an answer streaming
(responding), a skill, workflow or job running (working), council members answering (council), a message offered
through the gate (notification), a failing app or job (warning), an action executed (success). Never a timer
pretending. The orb's colour is the scheme's primary accent; warning and success use the meaning colours.

**AI customisation** (§9): "a darker version of this theme" and "warmer" are `build_theme` with adjusted choices; "a
theme from this picture" extracts the palette in code (the model may name it, not choose its numbers) and goes through
the same checks; "reorganise my dashboard" proposes a layout through the layout schema. Every result is a proposal he
previews and approves, saved through the theme actions (undoable). Nothing generated bypasses `clean_theme`, the
contrast checks or high contrast.

## D. Schemas and contracts

Published in phase A3 as `docs/schema/appearance.schema.json` and checked by a test:

- **Theme:** `{id, name, about, tokens: {field and panel tokens}, surfaces: {primary|secondary|floating|deep|interactive:
  {opacity, blur, border, light, elevation}}, backdrop: {kind: none|picture|ambient, ref, strength}, room, sound}`.
- **Scheme:** `{id, name, accent, secondary, tertiary, gradient: [colours], chart: [6 to 8 colours], meaning_tune:
  {amber, red, green, gold}: small hue shifts, checked}`.
- **Layout:** `{nav: left|bottom|top, density: comfortable|compact, sidebar: full|icons|hidden, experience:
  auto|spatial|cards, home: [widget ids in order]}`.
- **Component contract:** every component uses a surface tier class and tokens, never a literal colour; a test fails on
  a new literal colour in `web/*.css` outside `tokens.css` (the existing 141 are a baseline that may only shrink, like
  `work/doc_baseline.json`).

## E. The plan

| Phase | What | Tests and acceptance | Model |
|---|---|---|---|
| A1 | This document; DEC-0183, DEC-0184; Q-37 to Q-39 | — | Opus (done) |
| A2 | Core visual system: the five surface tiers as tokens and classes; elevation, gradient, chart tokens; the literal-colour baseline test; components moved onto tiers (`components.css`) | the token contract test; screenshots of every page in the current themes unchanged in layout | Opus |
| A3 | The engine: `display.scheme` and `display.layout`; `appearance()` composing them; existing themes split into theme plus scheme; the effective-contrast check; reduced transparency and effects levels; the schema | a contrast matrix test over every theme × scheme × tier; switching each live without a reload; settings surviving a restart | Opus, Fable reviews |
| A4 | The six presets as data (Aquatic, Nebula, Evergreen, Aurelia, Glacial, Eclipse) with matching schemes; Muse refines values | each passes the contrast matrix; screenshots of Home, an app page and the approval card in each | Opus, then Muse |
| A5 | Settings › Appearance (the Studio grown: themes, schemes, layouts with previews; transparency, blur, density, motion; save, restore defaults); the orb's presence states from the runtime; the MIA session's default dashboard | the acceptance list below, items 2 to 4 and 9; S-01's Home in each preset | Opus |
| A6 | Apps onto the shared system, one at a time: literal colours retired, atmosphere hues (Workshop steel, Finance, Greenhouse leaf…) | the literal-colour baseline falling; nothing functional changed (the suite) | Opus |
| A7 | Advanced: animated ambient backdrops, custom schemes and layouts by voice, a theme from a picture, Plasma colour scheme from MIA's, spatial environments | performance fallbacks proven on the phone and a light profile | Opus, Fable for anything touching the session |

**What isn't changed:** no app is replaced by a mockup; the Qt classic view keeps its own look; meaning colours, high
contrast and text size keep working through every phase; the suite passes at every step.

## F. Acceptance (handoff §12), how each is shown

1. Documented design system: this document, `docs/design/MIA_DESIGN_SYSTEM.md` updated, the schema.
2. Three dimensions independent: a test sets each and checks the others' output unchanged.
3. Switched without restart: a browser test switches theme, scheme and layout on a live page.
4. Persisted: person settings (already durable, synced).
5. All presets consistent: the contrast matrix test and a screenshot set per preset.
6. Apps consume shared tokens: the literal-colour test at zero for migrated apps.
7. Readability: the effective-contrast check on every tier.
8. Fallbacks: the effects levels and reduced transparency demonstrated on the phone and the PC.
9. Visual previews: the Appearance page shows each choice rendered, not hex values.
10. Functionality intact: the full suite and the parity test unchanged.
11. Future AI themes: every theme, scheme and layout goes through the same validated builders.

## G. Risks

| Risk | Mitigation |
|---|---|
| Glass hurts readability over busy backdrops | the effective-contrast check refuses it; floating surfaces always the most opaque |
| Blur costs GPU, scrolling stutters on the phone | effects levels; blur off on phones by default (already); measured in A3 |
| Meaning colours drift into schemes and a warning stops reading as one | schemes can't set them; hue tuning only through a checked function |
| Two looks diverge (DEC-0023's Stark and the new glass identity) | Stark stays a theme on the same engine; one token file |
| Visual work crowds out function | phases A2 and A3 are infrastructure; A6 migrates app by app with the suite green |

## H. Decisions and questions

- **DEC-0183** (Zac's handoff: the direction is approved): glass is MIA OS's visual identity. The default look moves
  from Stark (DEC-0023) to a glass theme; Stark stays a theme. DEC-0023's rules that stay: one token file, no
  hard-coded colours, meaning colours fixed; "one cyan accent" becomes "the scheme's accents".
- **DEC-0184** (proposed): the appearance engine is three settings (theme, scheme, layout) on the existing engine, with
  five surface tiers, the effective-contrast check, effects levels, and the orb's state from real activity; no new
  framework; meaning colours stay out of schemes.
- **Q-37:** which preset is the default? Recommendation: Aquatic with the cyan scheme, so MIA keeps her colour.
- **Q-38:** Muse owns the look (DEC-0017, DEC-0023). Claude builds the engine and first values for the six presets;
  Muse refines them. Is that the split Zac wants?
- **Q-39:** the dashboard reference image: please attach it again so it can be kept in `docs/design/` and the presets
  tuned against it.

## I. The reference picture, read (Zac, 2026-11-15; Q-37: Aquatic, "but base it on the picture")

Kept as [`docs/design/reference/prompt24_glass_dashboard.jpg`](../design/reference/prompt24_glass_dashboard.jpg)
(cropped to the photo; the phone's status bar left out). An illustrative render: the names and faces in it are
placeholders, not people MIA knows.

**What it shows:** one large glass panel floating over a real, softly lit room (concrete walls, warm wood), so the
environment is a photograph-like dim space, not a gradient field; the panel is dark blue-graphite glass with the room
showing through, frosted; a thin, bright cyan glow runs around the whole window's edge, not around each card; inside,
a narrow icon rail on the left, a top bar (title, notifications, the person), and a grid of quieter cards with rounded
corners (larger on the window, smaller on cards), each with a small spaced-capitals label; charts run from cyan through
blue to violet; increases in muted green; white text; generous spacing; nothing neon beyond the one edge.

**Its palette, read in code** (median-cut quantisation of regions of the picture, `Pillow`), the starting values for
Aquatic, which Muse refines (Q-38):

| Role | From the picture | Note |
|---|---|---|
| Window edge glow (primary accent) | `#7fddec` to `#23c4e8` | MIA's cyan today is `#35d4ff`: kept, it sits inside this range |
| Glass panel (primary) | `#2b323c` to `#33434d`, frosted over the room | about 0.6 to 0.7 opacity with a strong blur |
| Cards (secondary) | `#2f3840`, slightly lighter than the panel | quieter borders, no glow |
| Chart gradient | cyan `#23c4e8` → blue `#3f79e5` → violet `#5955cb` | the scheme's secondary and tertiary accents |
| Progress fill | blue `#567fd8` on a deep track `#12223c` | |
| Increase (meaning: ok) | muted green `#487b6c` on `#243e39` | stays the meaning colour (DEC-0136) |
| Text | near white | as `--text` today |
| Environment | the room's neutral greys (`#3e4041` to `#575f5f`) behind the glass | a backdrop picture, blurred; Aquatic's own scene can be an underwater one with the same values |

**What this changes in the plan:** the window-edge glow is a property of the *deep* tier on the shell's frame only
(not every surface); the environment can be a calm photographic backdrop; the chart palette is the scheme's three
accents. Everything else stands.
