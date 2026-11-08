# One MIA, many looks: experiences and themes

*Claude, 2026-11-08, from Zac's handoff "MIA — Selectable Interface Experiences & Multi-Theme Architecture" (05:35).
It follows the handoff's section 6: audit, decide what's shared, propose, then build in steps with tests in both
experiences. Decisions: DEC-0135 (two experiences) and DEC-0136 (themes), both from Zac's requests; the open
questions at the end are his.*

**Built 2026-11-08 06:30:** step 1 of the Theme Studio (section 5): `core/themes.py` (the four themes as data, the
allowlist and its check), `web/themes.css` (the materials), `web/shell.js` (applies the theme on every page, cached
on the device), `web/nexus3d.js` (the room's light from the theme), Settings' Look section and the `set_theme` voice
tool.

## 1. Audit

### What MIA already separates well

| Layer (the handoff's names) | Where it lives today | State |
|---|---|---|
| **MIA Core**: intelligence, memory, tools, missions, every app's logic | `core/` (stores, actions, assistant tools, `web_*` screen assemblers) | Already shared: every web page reads its data from core and changes things only through `/api/actions` (DEC-0013, DEC-0017). Nothing about the look is in core except which look a person picked. |
| **Experience**: how you arrive and move around | `web/shell.js` (`MIAShell.look()`, the sidebar, the bottom bar), `web/welcome.js` (where MIA opens), `web/nexus.js` + `web/nexus3d.js` (the Nexus), `web/hub.js` (an area as cards or as a room) | DEC-0135 made it a per-person choice: **Spatial** or **Cards**, by device by default. |
| **Theme**: colours, type, materials, light, motion | `web/tokens.css` (DEC-0023's Stark look as tokens), used by every stylesheet; the 3D room's own colours in `web/nexus3d.js` | One theme, Stark, but built as tokens, so swapping them reskins every page. |

### The cards design worth keeping, as it is

The Dashboard (`index.html`, `welcome.js`), the frame (sidebar on the PC, bottom bar on the phone), the app pages built
to the DEC-0113 canvas (`ui.css`, `concept.css`, `components.css`), the hub tiles and the Garage's flat cards. None of
this is replaced: it is the Cards experience, and every app page is shared by both experiences.

### The spatial build

The Nexus (`nexus.html`: a WebGL 2 room, with the CSS ring as its keyboard path and fallback), the Garage's room
(`hub.js` `garageRoom` on the same engine), the glasses' flat ring of areas. The engine had its colours written into
it (the cyan accent, the floor, the bloom); themes need it to read them instead.

### How themable the web is

- Every page loads `tokens.css` first and reads `--bg`, the panel layers, `--line`, `--text`, `--accent` and their
  `--rgb-*` triplets, the radii, the fonts, the motion timings.
- About 140 colours are written directly in the other stylesheets, mostly black shadows and the glasses' own
  see-through palette. The few that matter for a theme (some panel glows) can move to tokens as each theme shows
  where they stand out.
- High contrast (`[data-contrast="high"]`) is an accessibility mode, not a theme; it must keep winning over any theme.

## 2. The architecture

```
MIA Core (core/)            the same for everyone, every look: data, tools, actions, memory, personality
   │  /api/shell → display: {style, theme}
Experience (web/)           Spatial or Cards: where MIA opens, the navigation, an area as a room or as cards
   │  reads the theme's tokens and room settings
Theme (data in core/themes.py, applied by web/shell.js)
                            tokens (colours, panels, type, shape, motion, backdrop) + the room's light and effects
```

- **A theme is data, not code.** `core/themes.py` holds each theme as a set of token values and room settings. The
  page applies them as CSS custom properties on the page (so every stylesheet follows) and hands the room settings to
  the 3D engine. Built-in themes, and later the ones Zac or MIA make in the Theme Studio, go through the same path.
- **What a theme may change** (an allowlist, checked in core): the field and panel colours, lines, text, the accent,
  radii, fonts (system fonts only: MIA is offline), label spacing, motion timings, an extra backdrop layer, and the
  room's light (accent, bloom, fire, mist, the backdrop's palette, scanlines, grain).
- **What it may not change: meaning.** Amber (needs you), red (errors, destructive), green (ok), gold (rewards),
  rarity colours, area hues on portals, and printed labels stay the same in every theme, so a warning never hides in
  a theme's palette (DEC-0014, DEC-0130). High contrast overrides every theme.
- **No duplicated apps.** A theme never chooses a different page or layout; an experience never changes what an app
  does. Both only change how the same page looks or how you reach it.
- **Switching is live.** The choice comes with the shell on every page and is cached on the device, so a new page
  opens already themed, and a change in Settings or by voice applies on the next screen without a restart.

## 3. Starter themes

| Theme | Spatial | Cards |
|---|---|---|
| **Stark** (default, DEC-0023) | Cyan holographic room, as built | The current look |
| **Y2K Cyber** | The vapor and mist in a magenta, violet and blue liquid palette, more fire and mist, film grain | Chrome-and-neon panels with rounder corners, a 2000s system font, a liquid backdrop |
| **Cyberpunk** | Hot magenta accent on a deep violet-black room, scanlines, heavier mist | Hard edges, a condensed technical font, magenta and electric-blue lines |
| **Glass** | A quieter room: less fire and bloom, soft white light | Translucent frosted panels, light type, wide radii, slower and softer motion |

All four are first cuts by Claude for Muse to refine (DEC-0017).

## 4. Devices

- **PC:** both experiences in full; the room at full effects.
- **Phone:** both experiences; the room with fewer pixels and the same theme.
- **Glasses:** the flat ring and cards; a theme brings only its accent (the display shows light; black is
  see-through, so backdrops and panels don't apply). Later step.
- **Future MIA Home devices and the Quest:** the same theme data; each renderer takes what it can show.

## 5. Theme Studio, in steps

1. **Pick** (built now): experience and theme in Settings' Look section and by voice; switching is live.
2. **Preview and tweak** (built 2026-11-08 07:15, `web/studio.html`, Settings and Diagnostics → Theme Studio): the Studio page shows a sample of both experiences in a theme; sliders and colour pickers for
   the allowed tokens and room settings; saved as the person's own theme (data, in their folder).
3. **Make and share:** new themes from scratch or by mixing parts of two; import and export as a small JSON file
   (checked against the same allowlist, so an imported theme can't hide warnings or inject anything).
4. **MIA designs one:** "make me a theme like a rainy Tokyo night" becomes a proposed theme (tokens and room
   settings chosen by code from MIA's description), previewed before it's kept.
5. **Sound sets:** a theme may bring its own chimes (web/sound.js), opt-in.

## 6. Zac's answers (05:48)

1. The four starter themes and names: yes.
2. Y2K's loud graffiti: yes. Built as its own layer (`web/img/themes/y2k-graffiti.svg`): abstract tags, drips and
   sparkles, loud at the edges and in the gaps, faded toward the middle where you read.
3. Next: Claude's choice. Built step 2 of the Theme Studio.

## 7. The Theme Studio as built (step 2)

- Start from any theme (built-in or yours); tweak five colours (accent, background, panels, text, lines), corners, the
  font (system stacks), the panels' material, and the room's fire, glow, mist, scanlines, grain and mist palette.
- The whole Studio page is the preview, plus a little 3D room; nothing is kept until you save.
- Core builds the tokens from those choices (`core/themes.build_theme`) and refuses an accent that would read as
  amber, red, green or gold (within 20° of their hues, unless pale or grey) and text under 4.5:1 contrast; the page
  says so as you pick and greys out Save.
- Save, Save and Use, Delete are actions (`theme.save`, `theme.delete`: approved, undoable). Your themes appear in
  Settings' Theme list and answer to their names by voice ("use Lavender"); "make the accent purple" and "make it
  glass" make your own version (`tweak_theme`); "delete my theme Lavender" (`delete_theme`).

## 8. Open for Zac

1. Theme Studio step 3 (import and export) or step 4 (MIA designs a theme from a description) next?

1. The four starter themes and their names, or others first?
2. Should the Y2K theme be allowed a loud graffiti texture in the backdrop (it's behind panels, never under text)?
3. Theme Studio next, or more areas' rooms first?
