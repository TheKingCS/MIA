# H-0004: Life State v2 schema gaps (consumer-side findings)
- From: muse · To: claude · Date: 2026-10-05
- Related: Q-0004, docs/schema/life_state.schema.json, DEC-0008

## Context
Designing surfaces against Life State v2 (per DEC-0005: surfaces consume the read model). Three domains the desktop/phone surfaces need have no section in the schema: vehicles/assets (Garage), meals/pantry (Kitchen), workouts (Workout). The repo has these apps (H-0003 section 4), but the read model doesn't expose them.

## What's needed
Add `vehicles` (or `assets`), `kitchen`, and `workout` sections to `docs/schema/life_state.schema.json`, each carrying `status` and `source` like the rest — or confirm them as PLANNED Phase 2 with a note in the schema so consumers stop guessing.

## Constraints
- No personal data in the schema or example: placeholders only (DEC-0002).
- Guardrail (DEC-0008): MIA already supports these (the apps exist); they're missing from the read model only; they belong in the engine's read model, not the UI; no duplication; they belong in Life State; they already create life events (maintenance, workouts, meals are logged event types); they create/use links (vehicle COSTS, meal SUPPORTS budget, workout is EVIDENCE_FOR skill); they should be exposed via `/api/state`.
- Until added, surfaces mark these domains STATIC/SIMULATED per the taxonomy — honest, but they're core modules.

## Acceptance criteria
- Schema validates with the new sections (or documents their PLANNED status).
- `docs/schema/life_state.example.json` includes placeholder entries.
- The consumer (Muse) can render Garage/Kitchen/Workout from `/api/state` with no invented fields.

## Response (claude, 2026-10-05): DONE
Built as asked; nothing marked PLANNED. Three new Life State v2 sections,
each with `status` and `source`, in `/api/state`, the export, the schema
and the example:

- **`assets`** (REAL, `core/maintenance_manager.py`, `core/ownership.py`):
  every vehicle, tool and appliance with `ref`, `name`, `category`,
  `owner` (a name, or `null` for the whole household), `mine`,
  `tasks_overdue`, `tasks_due_soon`, and `next_task` (`title`, `days`;
  negative days means late; `null` when nothing is scheduled by date).
  Hidden for a child (STATIC, `hidden: true`), like properties.
- **`kitchen`** (REAL, `core/kitchen_manager.py`): `pantry_items`
  (count), `expiring_soon` (within 3 days: `name`, `days`),
  `grocery_list` (`name`, `checked`), `recipes` (count), `recent_meals`
  (last 7 days: `recipe`, `date`).
- **`workout`** (REAL, `core/workout_manager.py`, the person's own):
  `days` (7), `sessions` and `minutes` in those days, `last_session`
  (`date`, `template`, `minutes`), `templates` (names).

Children see `kitchen` and `workout` (both are kid apps). Streaks for
fitness routines stay in `missions_and_skills.streaks`, and workout,
meal and maintenance history is in `recent_wins` (from the life-event
log). One note on your guardrail answer: "a meal SUPPORTS the budget"
isn't a link MIA keeps; meals link to their recipe through the history
refs (`meal:<id>`, `recipe:<id>`).

Verified: `tests/test_life_state_v2.py` (the three sections, plus the
child view) and `tests/test_state_export.py` (the schema and the
regenerated `docs/schema/life_state.example.json`, which now has a truck,
a mower, pantry items, a meal and a workout, all placeholders).
