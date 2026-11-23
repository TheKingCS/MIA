---
id: K-0344
kind: implementation
title: Plans made together become a project and a mission a stage (builds and gardens)
status: confirmed
by: claude
created: 2026-11-22T23:54:56+00:00
concerns: core/project_plans.py, core/garden_plans.py, core/mission_guide.py, core/assistant_project_plan_actions.py, web/planner.js
from: task:T-0060
---
T-0060 steps 1, 2 and 4. core/project_plans.py: a ProjectPlan draft (household store project_plans.json) of a build (a Library shelf plan at his size plus the Trade Master job whose Job.plan names it; stages: Get the materials from the shopping list, then the job's phases with why/watch/hold) or a garden (core/garden_plans.py: 33 crops with start method, weeks from the last frost, square-foot spacing, days to harvest, frost tolerance; his frost dates asked for, never assumed, and remembered in garden.last_frost/first_frost). projectplan.draft and change are within a grant (drafts only); projectplan.confirm is his yes and makes one project and one mission a stage, each step a tally objective, all one action so one Undo takes it back (tested). The plan guide in core/mission_guide.py shows the next step and the stage's passages from her offline library (offline_library.passages, looked up once per stage). What went wrong: built-in shelf plans are keyed 'builtin:raised-bed' while Job.plan says 'raised-bed' (_bare/_shelf_id match both); the card must work the plan out in describe, so a missing frost date is asked before the card, not a failure after his yes; MIAShell.form takes default, not value; replaceChildren(null) prints 'null'. Web: planner.html (beside Trade Master in the learning area), Knowledge's Plan It With MIA and Open The Planner.
