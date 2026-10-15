# MIA's interface: the Stark engineering look (DEC-0023)

*claude, 2026-10-15, from Zac's brief. Muse owns the look from here
(review and polish: H-0034). For anyone styling a MIA screen.*

**The idea:** an inventor's own operating system. Real technology, built
in a private workshop: precise, quiet, expensive. Not a gaming dashboard,
not cyberpunk, not a movie prop. It draws on Tony Stark's workshop
diagnostics, the Iron Man HUD and engineering software, and copies none
of them.

## The rules

1. **One accent.** Electric cyan (`--accent`) means active, selected,
   MIA's voice, and progress. Every app uses it; apps differ by icon
   and name, not color.
2. **Color carries meaning, sparingly.** Muted green (`--ok`) = healthy
   or done. Amber (`--attention`) = needs you, soon. Red (`--bad`) =
   real errors, overdue and destructive actions only. Gold (`--win`) =
   earned celebration only (a new best, a milestone, the celebrate
   orb). Rarity colors only on missions, achievements and unlockables.
3. **Values are white; color sits beside them.** A status strip's
   number is white with a colored index bar. Money figures are the
   exception: in green and out red are the meaning.
4. **Depth from layers, not borders.** `--bg` near-black, then
   `--rgb-panel`, `--rgb-panel-2`, `--rgb-panel-3`. Lines are fine and
   low-contrast (`--line`, `--line-strong`); a cyan edge means active
   or hovered.
5. **Precise shapes.** `--radius` (6 px) for panels, `--radius-sm` (4 px)
   for controls and tags. Circles only for the orb, the reactor marks,
   avatars and round tick buttons.
6. **Not everything glows.** Glow is for MIA's orb, the primary button,
   the current nav item and meters in progress. Cards don't glow; text
   doesn't glow.
7. **Never a hard-coded color.** Use the tokens, or
   `rgba(var(--rgb-accent), 0.3)` for a faint version of one.

## Type

- System sans (offline: no web fonts), comfortable body size.
- **Technical labels:** the mono face, 11 px, spaced capitals
  (`--font-mono`, `--label-size`, `--label-track`): status-strip labels,
  tile labels, meal slots, chart keys, the header's tagline, form labels.
- **Readouts:** tabular figures everywhere (`font-variant-numeric:
  tabular-nums` is on `body`); big numbers in the mono face.
- Section titles carry a short cyan index mark (`.sect h2::before`).

## The pieces

| Piece | Look |
|---|---|
| Header plate (`.hero`) | **Technical, no photos** (Zac via Muse, H-0036): graphite with a fine cyan grid (16 px, every 4th line stronger), a cool light toward the right, the app's line icon drawn large and faint as a schematic inside a dashed ring and crosshair (`.plate-motif`, added by `shell.js`), corner brackets, a fine scale along the bottom, the app's icon in a square badge, the mono tagline |
| Card titles and values | Wrap only between words; a long one-word title shrinks to fit its card, and money values never wrap (they shrink to fit their tile), so a large phone text size can't break "Athleticism" or "$40,000.00" mid-word |
| Panels (`.glass`, cards, rows) | Graphite gradient, 1 px line, 6 px corners, a faint top highlight; cyan edge on hover |
| Status strip | Neutral values; a 2 px colored index bar on the left (green ok, cyan info, red needs attention) |
| Buttons | Primary `.btn-green`: solid cyan, dark text. Secondary `.btn-amber`: cyan outline. Quiet `.btn-ghost`: fine line. Danger: red text and line. Pressing nudges 1 px |
| Tabs (`.ptabs`) | A rail; the selected tab is lit from below |
| Chips | Square-shouldered tags, small type |
| Meters | Thin (6 px) with a 10 px scale; cyan, gold when a target is hit |
| Navigation | Line icons; the current page gets a cyan inset bar, a faint gradient and a lit icon |
| Brand | `MIA` in spaced mono capitals; the arc-reactor mark (`.brand-reactor`) |
| Dialogs | A raised panel with a cyan top edge; a short rise-in |
| Focus | A 2 px cyan ring on every focusable thing |

**Icons** (`web/icons.js`): one 24-unit line set, 1.6 stroke, round
joins, `currentColor`. `MIAIcons.svg(appId)` for the frame. A
mission's, skill's or stat's own emoji is the person's content and
stays.

**Motion:** brief and purposeful (`--dur-fast` 120 ms, `--dur` 200 ms,
`--ease`): hover and selection, dialogs rising in, meters filling, MIA's
orb breathing. Nothing moves continuously except the orb, and
`prefers-reduced-motion` turns animation off.

## Accessibility (measured 2026-10-15)

Contrast (WCAG) on the panel layers: body text 14–16:1, dim text
7.5–9:1, faint text 5.3–5.7:1, cyan 9.5–11.5:1, amber 8.9–10.8:1, green
7.6–9.2:1, red 4.8–5.8:1, dark text on the cyan button 10.9:1. High
contrast (`[data-contrast="high"]`): black, white and full cyan.

## The glasses and small displays

The glasses page keeps its own layout and stylesheet (`glasses.css`):
a 600×600 additive display needs its own composition, not the phone's.
What carries over is the language: cyan on black, mono labels, compact
readouts, one accent. The high-contrast tokens are the closest thing to
that display today. MIA doesn't claim glasses or Neural Band features
it doesn't have (DEC-0016).
