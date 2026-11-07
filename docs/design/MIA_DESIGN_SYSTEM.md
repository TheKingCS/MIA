# MIA's design system

*Claude, 2026-11-07, for H-0087. **Specification draft.** Each section says what's **built** today (with the token
or class), and what's **proposed**. Proposals wait for Zac's approval and round one of the visual concepts
(`docs/design/MIA_VISUAL_IDENTITY.md` §5); Muse owns the look and refines the values. `web/tokens.css` is the only
place values live; this document explains them. Identity and direction: `MIA_VISUAL_IDENTITY.md`.*

## 1. Color

**Built** (`web/tokens.css`, DEC-0023): field `--bg` #05070a; panels `--rgb-panel`, `-2`, `-3`; lines `--line`,
`--line-strong`; ink `--text` #e6eef6, `--text-dim`, `--text-faint`; MIA `--accent` #35d4ff (+ `-soft`, `-deep`,
`-glow`); meaning: `--ok` green (done, healthy), `--attention`/`--soon` amber (needs you), `--bad` red (real errors,
overdue, destructive), `--win` gold (earned celebration only); `--rarity-*` on missions and unlockables only; every
color also as an r,g,b triplet for faint versions (`rgba(var(--rgb-accent), 0.3)`).

**Proposed:**
- **Per-app atmosphere** (needs Zac's decision): give the existing `--mod-*` tokens their own values (today they all
  point at cyan): `--mod-workout` warm performance orange, `--mod-kitchen` amber-cream, `--mod-workshop` steel
  blue-gray, `--mod-homestead` leaf green. An app's atmosphere color is for **its own data and header motif only**;
  cyan still means MIA, active and selected everywhere; meaning colors keep their meaning.
- **Retire literal colors**: 141 lines in the CSS outside tokens (30 are harmless black shadows); replace the rest
  with tokens over time, starting with what flagship pages use.
- **Contrast**: every text color on every panel layer meets WCAG AA (4.5:1 body, 3:1 large and UI); a check in the
  tests reads the token values and computes it, so a change can't break it.

## 2. Typography

**Built:** system sans (`--font`) and mono (`--font-mono`); scale `--text-xs` 12 · `-sm` 13.5 · `-md` 16 · `-lg` 20 ·
`-xl` 28 · `-2xl` 38 px, all times `--scale` (the person's text size); labels: mono 11 px, spaced capitals
(`--label-size`, `--label-track`); tabular figures everywhere.

**Proposed:** a **display size** for flagship moments (the rep count, a cooking step: `--text-3xl` 56 px, mono,
tabular), and named roles instead of sizes in components: *display, title, heading, body, caption, label, readout*.

## 3. Spacing and sizing

**Built:** `--gap` 16 px; `--touch` 44 px minimum targets; `--radius` 6, `--radius-sm` 4, `--radius-pill`.

**Proposed:** a 4 px base scale (`--space-1` 4 … `--space-8` 48) so pages stop mixing `--gap` fractions; touch
targets **56 px** in hands-busy modes (active workout, cooking), where a sweaty or floury finger is aiming.

## 4. Panels, cards and surfaces

**Built:** `.glass` panels with a graphite gradient and a top highlight; `.glass money-section` used as every
page's section; cards (`.card`, tiles) in `components.css` / `concept.css`.

**Proposed:** four named surfaces, one depth each: **base** (the page), **section** (a group), **card** (one thing),
**focus** (the one thing that matters now: brighter, larger, lit edge, the rest dims). Rename `money-section` to
`section` (with the old name kept as an alias while pages move).

## 5. Buttons and controls

**Built:** primary `.btn-green` (solid cyan), secondary `.btn-amber` (cyan outline), quiet `.btn-ghost`, danger;
tabs `.ptabs` (a rail, the current lit from below); chips; inputs; toggles.

**Proposed:** keep the four; rename by role (primary, secondary, quiet, danger) with aliases; add a **big action**
(full-width, 56 px) for hands-busy modes; every control gets visible focus (a cyan ring), not only hover.

## 6. Icons and symbols

**Built:** line icons from `web/icons.js` (one set, one stroke); the app icon drawn large as a schematic in the
header plate.

**Proposed:** an icon audit (every app and action has one; same stroke and grid); per-app motifs for the header
plates (§1 atmosphere).

## 7. Navigation

**Built:** a sidebar from `/api/shell` (apps by group; current page lit), the Apps page, the Talk panel everywhere,
tabs inside pages; phone: the same pages in the app's web view.

**Proposed:** flagship apps get a **home view and modes** instead of six or seven tabs: Workout = Today (with Start),
Active (full screen), Progress, Plan; Kitchen = Today, Cook (full screen), Week, Recipes, Pantry and Grocery. On a
phone, the sidebar becomes a bottom bar of the five most used, plus Apps.

## 8. Charts, meters and data

**Built:** thin meters (6 px, a 10 px scale; gold when a target is hit); the status strip (white value, colored index
bar); a weight line on Progress; condition bars on equipment.

**Proposed:** a small chart set drawn in SVG by one shared helper (line, bar, ring, sparkline), using tokens, with a
data table behind each for screen readers; rings for "how far through" (a set, a rest, a day's protein).

## 9. Motion

**Built:** `--ease`, `--dur-fast` 120 ms, `--dur` 200 ms; the orb's moods animate; `prefers-reduced-motion` honored
in 11 places.

**Proposed:** motion only for cause and effect (fill, drain, advance, arrive); `--dur-slow` 320 ms for a focus
change; one place (`components.css`) where every animation checks reduced motion.

## 10. The orb and her presence

**Built:** Home's orb (`web/home.css`: moods celebrate, needs-you, thinking), the glasses' orb (`web/glasses.js`:
listening, answered, idle), the shell's Talk button.

**Proposed:** **one orb component** (`web/orb.js` + its CSS) with one set of states, used everywhere at three sizes
(hero on Home, header in apps, corner in modes): **idle** (slow breath), **listening** (rings drawn in), **thinking**
(an orbit), **speaking** (the core pulses with her voice), **needs you** (amber), **celebrate** (gold, once),
**offline** (dim, still). States come from one place (the shell knows when she listens and speaks), so every
surface agrees.

## 11. Listening, thinking, speaking, attention

Covered by the orb (§10), plus the **caption** (what she heard, then what she says) under it; on the glasses the
caption is the main surface. Attention never interrupts a hands-busy mode except for safety (an alarm, a timer).

## 12. Notifications and feedback

**Built:** toasts and the notification center (desktop), the glasses' feed, the communication gate deciding what is
said unprompted (`core/communication_gate.py`, 5 a day).

**Proposed:** one feedback pattern for "done" (the item fills, a short line, undo for a few seconds), one for "needs
you" (amber, with its one next step), one for "earned" (gold, celebration, rare by design).

## 13. Accessibility

**Built:** text size (`--scale`), high contrast (`[data-contrast="high"]`), read the screen aloud, labels and roles
on most controls.

**Proposed:** contrast checked by a test (§1); focus visible everywhere (§5); every chart has a table; every
hands-busy mode works by voice alone; captions for everything she says.

## 14. Light and dark

**Proposed:** dark only, by identity; high contrast is the accessible alternative. (Zac to confirm.)

## 15. Devices

| Surface | Layout |
|---|---|
| Desktop (`modules/web_home`, 1280+) | sidebar, two or three columns, the orb in the header |
| Phone (the Android app's web view, 360–430) | one column, bottom bar, big targets, modes full screen |
| Tablet / counter (Kitchen's cooking mode) | one large step, landscape or portrait |
| Glasses (`web/glasses.html`) | their own composition: the orb, a caption, one panel at a time; never a page shrunk |

## 16. What's needed before building

1. Zac's decisions in `MIA_VISUAL_IDENTITY.md` §6.
2. Round one of concepts, shortlisted and approved (`docs/design/visual_library/`).
3. Muse's values for the proposed tokens and the orb's states.
4. Then, in order: the contrast test, the orb component, the named surfaces and buttons (with aliases, so no page
   breaks), then Workout.
