# H-0074: H-0073 look review — The Dungeon passes, two small tweaks

- From: muse
- To: claude (cc chat, zac)
- Date: 2026-10-26
- Related: H-0073, DEC-0046, DEC-0028, DEC-0038, DEC-0014

## Context

Look pass on H-0073, from the built files: `web/dungeon.html`,
`web/dungeon.js`, the `.dg-` rules in `web/concept.css`, and the demo
in `docs/schema/dungeon.example.json`.

Guardrail (DEC-0008): this builds on the approved game layer (DEC-0028)
and the Freedom plan (DEC-0038) — no new system, no duplication. It
reuses the existing chip, button and strip patterns. Loot is DERIVED
from hours and pay; banked loot is REAL from the bank sync; projected
loot is DERIVED. Runs are life events, per CURRENT_STATE. Nothing here
contradicts an approved decision, and DEC-0046 itself is already
approved by Zac, so this review needs no further approval — it is
design answers in my lane.

## Verdict

Accepted as built, with two small tweaks below. No redesign needed.
The hero ("Clear the run. Bank the loot."), the tab order
(Today / Loot / Record / Setup), and the "Did these happen?" wording
with nothing lost are all right — the last one matters, because it
keeps the non-punitive rule (DEC-0014) visible.

## 1. Hard-mode chips: show the game name only, and lift overtime out

As built, the Today row holds eight toggles, each labelled
"Name · real" (e.g. "Bare Shelves · came in unstocked"), so it wraps
long on a phone. Two changes:

- Chip label = game name only ("Bare Shelves"). Nothing is lost: once
  pressed, the `.dg-gm` line below already shows the name, the framing
  line and the XP, which is where the plain words belong.
- "⚔ Called-in overtime" gets its own line, out of the affix row.
  It is a property of the run, not a modifier, and sitting eighth in
  the row it reads as an eighth affix. Keep its pressed state amber,
  as now — pressed = amber already reads correctly against hard-mode
  amber.

## 2. Boss vs hard-mode: keep both signals when a run is both

The pairing is right: accent glow says "boss, the bigger event",
amber edge says "hard". But as written, `.dg-run.boss` (concept.css)
overrides `.dg-run.hard`'s amber left edge, so a boss run that was
also hard reads as boss only and the hard fact disappears at a
glance. `runLine` already adds both classes — the fix is CSS order /
specificity so a `.boss.hard` run keeps the amber left edge AND the
accent glow. Both facts stay visible; neither signal is demoted.

## 3. The strip: keep it as is

Four cells wrapping 2 × 2 at 390 px is the same as Insurance — an
established pattern, not a new one — and these are the right four
(This Week / Projected / Banked / Hard Mode). No change. The Hard
Mode cell's "soon" styling when the count is above zero is fine: it
reads as attention, which fits "the trouble is real" before the game
framing.

## Acceptance criteria

- Chips show game names only; the plain words live in the `.dg-gm`
  line on press.
- Called-in overtime sits on its own line, not in the affix row.
- A boss + hard run shows amber edge and accent glow together.
- Strip unchanged.

— muse
