# H-0026: Fitness + nutrition plans as daily missions (engine spec)
- From: muse · To: claude (cc zac, chatgpt) · Date: 2026-10-12
- Related: H-0020, H-0022, DEC-0002, DEC-0014, DEC-0017, DEC-0019

## Context

Zac asked MIA to plan his groceries, meal plans/recipes, and workouts — and turn the whole thing into daily missions. This is a new product direction: a structured fitness/nutrition plan becomes a mission generator inside the existing Missions module.

The user's frame — keep this in the design, it's the soul of the feature: calisthenics for capability, not show. "Muscles earned for service." Concrete goals: freestanding handstand, strict muscle-up. Method: body recomposition — high protein (~1g per lb bodyweight), eating near maintenance, progressive calisthenics training.

A complete concrete plan exists (built by muse, held outside the repo per DEC-0002). This handoff specifies what the engine needs so that plan — and plans like it — can live in MIA.

## The plan schema

A fitness plan object the engine consumes:

- `targets`: protein g/day, calorie approach, weigh-in cadence
- `training`: strength-day rotation (push / pull / legs-carry), sets × reps, progressions per movement
- `skill_tree`: handstand, muscle-up, L-sit — each an ordered progression with hold/rep milestones
- `milestones`: checklist items that want to become achievements (e.g. 60s wall handstand, 15 strict pull-ups, first muscle-up)
- `meals`: daily template, work-lunch rotation, grocery profile

All values are per-user and live on the device. The repo holds the schema and the mission logic — never the numbers (DEC-0002).

## Mission types to generate

From one plan object, the engine generates five recurring missions:

1. **Training** — today's strength day from the rotation (objectives: the exercises).
2. **Skill** — daily handstand practice, 10–15 min (objectives: wrist prep, wall work, frog pose, tuck attempts).
3. **Protein** — daily protein target (one objective: grams hit).
4. **Lunch** — packed lunch taken to work (binary daily habit).
5. **Prep** — weekly Sunday meal-prep session.

## Engine gaps

1. **Nutrition tracking.** Nothing in the engine tracks nutrition today. Need: a daily protein log (grams + date; per-meal breakdown optional, not required).
2. **Skill-session logging.** The workout module logs exercises as sets × reps × weight. Skill work (handstand holds in seconds, crow pose holds) needs a time-based shape.
3. **Bodyweight trend.** Weigh-ins 2–3×/week feeding a trend the plan's feedback loop reads: weight stable + strength going up = recomposition working.
4. **Plan → missions.** Given a plan object, generate the five mission types on the right cadence, wired into the existing Missions module (H-0022) — streaks, XP, one-tap complete, undo.

## Constraints

- **DEC-0002:** no real personal data in the repo. Schema + logic here; values stay on device.
- **DEC-0014 (non-punitive):** missed days are never punished. Streaks pause, they don't shame. Fitness is the domain where apps get preachy — MIA doesn't.
- **Less friction, not more notifications:** missions are glanceable, checkable in one tap. No nagging.
- **Phone-first (DEC-0019):** the check-in surface is the phone. Reuse the one-tap mission completion from H-0022.

## What's needed

Engine-side from Claude: the four gaps above. API shapes are your call — muse builds and polishes the web/phone screens once the engine exposes them.

## Acceptance criteria

- A plan object in the documented schema generates the five mission types on correct cadence.
- Protein loggable per day; skill sessions loggable by time; weigh-ins produce a visible trend.
- Everything flows through the existing mission complete / +1 / undo path.
- No personal data in the repo; no punitive streak behavior anywhere in the flow.
