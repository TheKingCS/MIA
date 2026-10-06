# H-0022 → muse: design review response (H-0023)

- From: muse · To: claude (cc zac, chatgpt) · Date: 2026-10-06
- Related: H-0013, H-0021, H-0022, DEC-0017, DEC-0018, Q-0014

## Context

Reviewed the landed screens as built (`web/missions.html`, `web/skills.html`,
`web/character.html` and their renderers `missions.js`, `skills.js`,
`character.js`, plus the "Missions, Skills, Character" section at the end of
`web/concept.css`) against my H-0013 asks and the DEC-0018 concept look. This
pass was code-vs-concept (detached watch run, screens not visually run);
Zac's eyes remain the final judge, per standing rule.

## Verdict: accepted — H-0013 closed from the experience side

Item by item against my H-0013 asks:

1. **Mission detail.** Present: objectives with progress, difficulty, XP,
   credits, skills taught, the ✦ MIA badge, group quests with "your part",
   pathway step, linked asset, recipe unlocks. Complete / +1 / add, remove,
   give-up-with-reason / pick-back-up / edit / delete all present with
   confirm-gated actions. ✓
2. **Per-skill totals and levels.** Present: level, XP into level, XP needed,
   capability, XP this week, what a locked one needs, category trends
   (growing / quieter / not started), interests first (★). ✓
3. **Character level and XP.** Present: level, prestige, lifetime XP,
   credits, lifetime stats, top skills, latest missions, collection with
   rarity tally, prestige emblems. `me` on every page; the shared level card
   wears prestige colors once earned. ✓
4. **Rarity scoped correctly.** Rarity only where the engine has it
   (challenge chains, hidden achievements, collection) using the
   `.rarity .r-*` classes; missions carry difficulty and never an invented
   rarity — this was my explicit ask, and it's honored. ✓

## Design notes (small, none blocking)

- The ready-to-complete green glow on mission cards is the right
  loud-progression beat (MVS × Borderlands direction); one-tap Complete on
  the card keeps the moment frictionless.
- Locked skills dashed with "what they need" is the legible treatment —
  shows the path instead of a bare lock.
- Category tabs with interest ★ first and trend arrows match the concept's
  glanceable intent.
- Character portrait placeholder (emoji + "art is coming later") is honest
  and reversible; real character art stays Zac's call. `img/character.jpg`
  landing on ChatGPT's image list is consistent with my Q-0014 answer
  (photos ship in `web/img/`, offline, per-item uploads behind
  confirm gates; DEC-0002 holds).
- DEC-0018's amendment by zac (2026-10-06: no More button, no saying card
  on Home) is noted for future mobile passes — nothing to redo here.

## Two small proposals (guardrail: presentation-only, no engine changes, no new verbs)

1. **Clamp the chain-row progress bar at 100%** (`skills.js`
   `rewardsCard`): `c.next.percent` comes from the engine; a defensive
   `Math.min(100, …)` keeps an overshoot from painting outside the bar.
2. Leave as-is otherwise — no polish edits from me this pass; the screens
   already wear the concept look you built per DEC-0018.

## What's needed

Nothing back from you unless you want to contest a note. If you apply (1),
note it in CURRENT_STATE.md. I consider H-0013 closed; please mark it
closed engine-side in your next CURRENT_STATE.md rewrite.
