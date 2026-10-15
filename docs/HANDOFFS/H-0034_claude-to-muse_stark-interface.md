# H-0034: MIA's new look, the Stark engineering interface (DEC-0023)
- From: claude · To: muse (cc zac, chatgpt) · Date: 2026-10-15
- Related: DEC-0023, DEC-0018, DEC-0016, H-0029, docs/design/STARK_INTERFACE.md

## What happened

Zac asked for a complete visual reskin of MIA, inspired by Tony Stark's
workshop, the Iron Man HUD and engineering software: an inventor's own
operating system. He approved it as **DEC-0023, which supersedes
DEC-0018's target look** (per-screen neon colors and warm photo heroes).
The concept's layouts stay; their material changed. Claude built it on
2026-10-15, across all 22 web pages, phone and desktop.

## What changed (all in `web/`)

- **`tokens.css` is the theme.** Near-black and graphite layers, one
  electric-cyan accent, cool white text, amber for attention, muted
  green for healthy, red for real errors, gold for celebration only.
  Colors also exist as `--rgb-*` triplets so faint lines and glows come
  from the same token. 6 px and 4 px radii, label style, motion timings.
  The old token names still work and point at the new values.
- **Hard-coded colors are gone** from `concept.css`, `components.css`,
  `shell.css` and `home.css` (mapped to tokens by meaning). Per-screen
  colors are gone; every app is cyan.
- **The Stark layer** (end of `concept.css`): panels, header plates
  (photo in monochrome with corner brackets and a scale), technical
  labels, buttons, tabs, chips, forms, dialogs, meters with a scale,
  navigation, the reactor brand mark, focus rings, motion.
- **`icons.js`**: a line-icon set for the frame (navigation, bottom
  bar, header badges, app tiles, quick actions, money tiles). Content
  emoji (missions, skills, stats) stay: they're the person's data.
- MIA's orb and the floating orb glow cyan (an arc reactor); the
  celebrate state stays gold.
- High contrast is black, white and full cyan.
- The glasses page and `glasses.css` are untouched (their own
  composition, DEC-0016).

The guide is `docs/design/STARK_INTERFACE.md`. It has the rules, type,
each piece, icons, motion, measured contrast and the note on wearables.

## For your review (the Look column)

- Does the header plate's monochrome photo work, or should it become a
  pure technical plate (grid, schematic lines) without photos? The
  photos in `web/img/` were made for the old warm look; new
  workshop-style images would suit this one (request them in
  `docs/design/IMAGE_REQUESTS.md` if you want them).
- The icon set is a first pass (36 icons). Redraw any you like; keep
  the 24-unit grid, 1.6 stroke and `currentColor`.
- Character art, the presence page (`presence.html`) and the dashboard
  saying card could each use a Stark treatment of their own.
- The glasses composition should take the same language when you get
  to it: cyan on black, mono labels, compact readouts.
