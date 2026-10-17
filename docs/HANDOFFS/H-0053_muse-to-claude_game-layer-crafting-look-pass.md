# H-0053: Look pass — game layer, crafting, What I Used, MIA Remembers, buffs (H-0051, H-0052)

- From: muse → claude (cc zac, chatgpt)
- Date: 2026-10-17
- Status: look pass filed; two small CSS tweaks PROPOSED (below); voice-guide additions made in `docs/design/MIA_VOICE.md`
- Related: H-0051, H-0052, DEC-0028, DEC-0029, DEC-0030, DEC-0031, DEC-0014

## Context

Read the built CSS in `web/concept.css` for all eight pieces (shop,
gear-condition, boss, attr, buff, talk-used, craft, home-remember) and
the voice guide. No rebuild proposed: everything below is notes plus
two small, reversible CSS tweaks. Guardrail (DEC-0008) run on both
tweaks: UI-only, nothing duplicated, no Life State / life-event / link /
`/api/state` change, REAL.

## Verdict

The eight pieces land in the same language: mono uppercase eyebrow
labels, plate cards, status colors (green / amber / red) used the same
way everywhere, transitions on the bars. Approved as built, with the
notes and two tweaks below.

## H-0051 — game layer (DEC-0028)

**Reward Shop (`.shop-*`)** — Approved. The `.ready` glow + `.claimed`
dim read correctly. One check: a claimed card should carry a text
"Claimed" state, not opacity alone (opacity doesn't convey state to
everyone). Confirm the markup has it; if not, add the label.

**Gear condition bars (`.gear-condition`, `.gc-*`)** — Approved. The
Mint / Good / Worn / Needs Care label + bar + value triple is the right
shape, and `tone-soon` / `tone-bad` reuse the same amber / red as the
craft needs-list. No change.

**Boss battles (`.boss-*`)** — Approved with one PROPOSED tweak. Every
`.boss-card` carries a red border, but a mission boss (e.g. "Finish the
greenhouse") isn't danger — red says "bad". PROPOSED: keep red for debt
bosses only; mission bosses get the accent/gold border (defeated still
flips to green). The red HP fill stays for all bosses — HP is HP.

**Character stats (`.attr-*`)** — Approved. The two-part bar (blue
training + green last-30-days) matches the handoff, the 28px value with
glow reads as a stat, and the gold `.attr-buff` segment makes buffs
visible on the bars. The italic `.attr-watch` footnote is fine as an
aside. No change.

## H-0052 — expansion pieces (DEC-0029, DEC-0030)

**Crafting Recipes / Builds (`.craft-*`)** — Approved with one PROPOSED
tweak. The needs-list border-left colors (green have / amber short /
red missing) match the gear tones; the mono pre-wrap `.craft-list`
reads like a workshop spec sheet, which is the Stark-plate language.
`.craft-head p { text-transform: none }` is right — the card title
(`h3`) is Title Case, the typed details stay as typed.
PROPOSED: color-code the build-photo tags (`.craft-tag`) — dim for
Before, accent for Progress, green for After — so the three stages
read at a glance instead of by text alone.

**MIA Remembers (`.home-remember`)** — Approved with one check. The CSS
is one rule (accent border + margin); the card leans on generic card
styles, which is fine. Check: the card needs a mono uppercase eyebrow
("MIA REMEMBERS") so it reads as hers, not as another task card. If
the markup lacks it, add it. Voice: Remembers lines go through the
never-guilt check like everything else — a birthday reminder must
never read as a scolding for forgetting.

**What I Used (`.talk-used`)** — Approved. Collapsible `<details>` with
a mono uppercase summary keeps it out of the way until wanted; the
`.forgotten` strikethrough + dim + hidden buttons is the right
treatment. Check: Fix / Forget buttons Title Case, and the summary
keeps keyboard focus visible.

**Buff chips (`.buff`)** — Approved. Pill, gold border, hover +
`focus-visible` states, `.buff-left` (time left) hidden in compact.
Tap-for-why is the right interaction. No change.

## Voice guide — two additions made

H-0052 asked me to change `docs/design/MIA_VOICE.md` where I disagree.
I agree with the guide as written and added two rules (edit pushed
with this handoff):

1. **Title Case on labels.** Button labels, tab names and headers are
   Title Case; body copy is sentence case. (The Oct 16 Title Case call,
   now written down where the guide already covers button labels.)
2. **Never narrate feelings.** She describes events, not emotions:
   "You finished the build", never "You must feel proud" or "You're
   probably frustrated". She doesn't know how anyone feels, and she
   doesn't guess.

## DEC-0031 flag (show-off mode) — for the tour script

Credits in the Reward Shop are game currency, not money — confirm the
tour treats them as showable. But **Bosses shows debt balances**, and
the Chronicle / MIA Remembers surface memories and journal material:
those screens must stay out of the tour or be scrubbed, per DEC-0031's
"money, journal, memories, health and people's details hidden on
every screen it opens". Flagging now so the tour script (not the
screens) carries it.

## What's needed

- Claude: apply the two PROPOSED CSS tweaks (boss border by kind,
  craft-tag stage colors) or say no, and confirm the three checks
  (Claimed label, Remembers eyebrow, Fix/Forget Title Case + focus).
- Zac: nothing to approve here unless you disagree with a tweak — the
  look pass is notes, not a rebuild.
