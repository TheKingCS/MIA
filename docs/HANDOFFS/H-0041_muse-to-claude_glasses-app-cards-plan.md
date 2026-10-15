# H-0041: Glasses app-cards plan — APPROVED by Zac
- From: muse · To: claude (cc zac) · Date: 2026-10-15
- Related: DEC-0016, DEC-0019, DEC-0023, H-0008, H-0034, H-0035, H-0036

## Zac's approved plan

Glasses navigation: glance (MIA's face + one due item) stays as home. One swipe away: app cards. Swipe through the cards, select one, simple action menu per app.

First apps: Kitchen, Workout, Missions, Money (read-only).

## Phases

1. App-cards composition (muse): new glasses view, card carousel in Stark language (cyan on black, mono labels, compact readouts). Swipe = Neural Band scroll on-device, drag/arrow-keys in preview. Select/back only, no bottom input, one card at a time, additive display. Read-only navigation first.
2. Action menus per app (claude — the engine ask below).
3. Voice + gestures: "Open Kitchen", "log lunch" via Android companion voice; Neural Band select proposes, second gesture approves.
4. On-device test when Zac's Display arrives (order estimate Nov 16): Funnel URL, Developer Mode, revocable link, real Life State.

## Engine ask (Phase 2)

Per-app "glance actions": each app declares 2–4 glance actions, served with the Apps catalog (or a new endpoint). Draft menus: Kitchen → Ate it, Plan lunch. Workout → Start today's training, Log skill, Weigh in. Missions → Today's missions, Complete one. Money → Today's spending, What's due (readouts only — money-moving approvals stay on phone/desktop in v1, per the voice decisions). Destructive actions stay off glasses entirely.

Each glance action maps to an existing action kind through /api/actions (Propose → Approve → Execute → Record → Undo). No new action kinds expected unless a menu item needs one — say which.

## Constraints (already decided)

- One card at a time, 600×600, additive (black = see-through).
- No bottom chat input on glasses.
- Two-gesture approve (H-0012, H-0008).
- No camera on the web path; voice via the phone companion.
- DEC-0023 Stark language on the glasses composition (H-0035 §6); glasses.css keeps its own layout.
