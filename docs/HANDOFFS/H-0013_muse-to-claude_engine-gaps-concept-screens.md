# H-0013: Engine data gaps found while building the concept screens
- From: muse · To: claude (cc zac, chatgpt) · Date: 2026-10-05
- Related: H-0009, DEC-0012, DEC-0014, Q-0004

## Context
The concept-styled web/ frontend shipped (tokens/components, Home reskin, Missions, Skills — 9 commits, signed muse). Everything on screen reads the real engine; nothing is invented. Building against the real read model surfaced four gaps: the engine has this data (the Qt side renders it), but Life State v2 doesn't expose it to web/.

## What's needed
Extend the read model (extend `missions_and_skills`, or a new section — your call) with:

1. **Mission detail:** the mission list with campaigns, objectives, `reward_xp`, difficulty/rarity. The web Missions screen currently shows the engine's due items (Active) and recent wins (Completed); the full concept screen — campaigns on top, objectives behind the click, rarity colors — needs the real mission objects the Qt modules already read.
2. **Per-skill XP totals/levels/thresholds:** `skill_manager` has `total_xp`, but it's not in the read model. The web Skills screen currently derives XP only from `skill_evidence` win events; real totals/levels would make it whole.
3. **Character level/XP:** the concept's "lvl 12" — the engine's character progression isn't exposed.
4. **Rarity tiers:** the CSS for Common→Legendary (Borderlands logic) is built but deliberately unapplied — per the design guardrail I will not invent rarity. If the engine ever tiers missions/achievements, the frontend is ready.

## Constraints
- Placeholders only in the repo (DEC-0002); schema changes must keep the status taxonomy (DEC-0007).
- Rarity is for achievements/missions, never for emergencies or bills (design addendum §5 guardrail).

## Acceptance criteria
- `GET /api/state` (or `/web/?demo`) exposes 1–4 above with REAL status tags; the web screens pick them up with no invented data.
