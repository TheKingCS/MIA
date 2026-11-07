# MIA's visual identity

*Claude, 2026-11-07, for H-0087. **Draft for Zac's approval.** It builds on the Stark engineering look (DEC-0023,
`docs/design/STARK_INTERFACE.md`), which is what's built today, and on the handoff's direction (JARVIS and EDITH,
holographic, spatial, a persistent presence). Concept rounds with ChatGPT (§5) are how this draft becomes final;
until then nothing in `web/` changes.*

## 1. Who she is, visually

MIA is **a presence, not a collection of apps**. Every screen is a place she's in. The interface should feel like
technology from a near future that someone careful built for themselves: precise, quiet, warm under the precision,
never a costume.

**Words for it:** intelligent, capable, confident, warm, calm, exact. **Not:** cyberpunk, neon, gaming dashboard,
movie prop, glassmorphism for its own sake, a wall of glowing widgets.

## 2. What stays (already true, and working)

- **Near-black and graphite depth**, layers instead of borders (`--bg`, `--rgb-panel` to `-3`).
- **One accent that means MIA**: electric cyan (`--accent`): active, selected, her voice, progress.
- **Meaning colors used sparingly**: green done, amber needs you, red real errors, gold earned celebration only.
- **Technical labels** in a mono face, tabular numbers, fine lines, 6 px corners.
- **Restraint with glow**: the orb, the primary action, the current place, progress in motion. Cards and text don't
  glow.
- **Offline**: system fonts, no web fonts, images shipped in the repo.

## 3. What this initiative adds (the proposal)

1. **Presence everywhere.** The orb is one component with one set of states (idle, listening, thinking, speaking,
   needs you, celebrate, offline) used by Home, the Talk panel, the glasses and every app's header, so it always
   feels like the same her. Her state is visible wherever you are.
2. **Spatial depth, lightly.** Panels sit at three depths (base, raised, focused). The focused thing in a flagship
   app (the current set, the current recipe step) comes forward: larger, lit from within, the rest dims a little.
   This is the "holographic" feeling without transparency soup: depth and light, not see-through everything.
3. **Atmosphere per app, on one identity** (needs Zac's decision, see §6). Each app keeps cyan for MIA and adds a
   **secondary atmosphere**: one color for its own data and a background motif in its header plate:
   - Workout: athletic and kinetic: a warm performance orange-red for effort and heart, motion lines.
   - Kitchen: welcoming: a warm amber-cream for food and warmth, soft grain.
   - Workshop: industrial: steel blue-gray and a blueprint grid.
   - Homestead (Greenhouse, Flock, Grow): organic: leaf green and contour lines.
   The token mechanism exists already (`--mod-*` in `web/tokens.css`); this formalizes it.
4. **Motion with a reason.** Things move to show cause and effect (a set done fills the bar, the rest ring drains,
   a step completes and the next comes forward). Short (150–300 ms), eased, and none at all with
   `prefers-reduced-motion`.
5. **Light mode: no.** MIA is dark by identity; high contrast stays the accessible alternative (already built,
   `[data-contrast="high"]`). (A decision for Zac: confirm.)

## 4. Three directions to explore first

So the concepts compare real alternatives, round one explores three, all inside §2:

| Direction | The idea | Feels like |
|---|---|---|
| **A. Workshop OS** (today's, refined) | Graphite panels, cyan instruments, blueprint grids, precise and dense | an engineer's own system |
| **B. Ambient presence** | Fewer panels; MIA's light shapes the space; content floats on depth; generous space; the orb leads | EDITH: calm, spatial, personal |
| **C. Heads-up instruments** | Thin rings, arcs and readouts around a focus; data as instruments, not cards | JARVIS's HUD, made livable |

The likely answer is a blend (B's presence and depth, A's precision for data, C's instruments for flagship moments
like the active workout), but the concepts should show it rather than assume it.

## 5. Round one: prompts for ChatGPT (ready to paste)

**Shared preamble (paste first):**
> I'm designing the visual identity for MIA, my personal AI companion (an app on my PC, phone and Meta glasses).
> Style anchors: near-black and graphite depth, one electric-cyan light (#35d4ff) that means MIA herself, small
> technical labels, fine lines, precise 6 px corners, soft glow only on what matters. Inspired by JARVIS and EDITH
> from Iron Man, but refined and believable, not cyberpunk, not neon, not a gaming dashboard. No real names, faces,
> logos or brand marks. Make each image 1600×1000, interface concept art, not a photo.

1. **The orb (identity)**: "MIA's presence orb: a small sphere of cyan light with a soft inner core and a faint orbit
   ring, shown in seven states side by side: idle, listening, thinking, speaking, needs attention (amber), celebrate
   (gold), offline (dim). One row, labelled, on near-black." (×3 variations, one per direction A, B, C)
2. **Home (interface concept)**: "MIA's home screen on a phone and on a desktop: the orb at the top, a short
   greeting, today's focus (three to five items to do), what's coming up, a few recent wins. Direction [A/B/C]."
3. **Active workout (application)**: "An active workout screen for MIA's Workout app on a phone held at arm's length:
   the current exercise large, set 2 of 4, a rep count in progress, a rest ring draining, the next exercise
   previewed small. Athletic atmosphere: a warm performance orange alongside MIA's cyan. Direction [A/B/C]."
4. **Cooking mode (application)**: "A cooking-mode screen for MIA's Kitchen app on a tablet propped on a counter: one
   recipe step in large type, a timer, the ingredients for this step, next and back as big targets, MIA's orb small
   in a corner listening. Welcoming atmosphere: a warm amber-cream alongside MIA's cyan. Direction [A/B/C]."
5. **Atmospheres (atmosphere)**: "Four header plates for MIA's apps, same layout, different atmosphere: Workout
   (athletic, orange, motion), Kitchen (warm amber, soft grain), Workshop (steel and blueprint grid), Homestead (leaf
   green, contour lines). Each keeps a small cyan MIA mark."

Save the good ones into `docs/design/visual_library/` with the prompt in `MANIFEST.md`.

## 6. Decisions for Zac

1. Per-app atmosphere (§3.3): allow a secondary color and motif per app? (Claude: yes.)
2. Dark only, with high contrast as the alternative (§3.5)? (Claude: yes.)
3. Run round one (§5) with ChatGPT before any visual change is built? (Claude: yes.)
