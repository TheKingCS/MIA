---
id: K-0273
kind: implementation
title: UI-7, plans across apps: steps done one at a time
status: confirmed
by: claude
created: 2026-11-16T18:37:16+00:00
concerns: core/step_plans.py, core/step_plan_actions.py, core/assistant_taught_skill_actions.py, web/steps.js, tests/test_step_plans.py, core/runs.py
from: dec:DEC-0188, task:UI-7
---
What: core/step_plans.py. StepPlan and Step in a personal store (step_plans.json, sealed, atomic, inside undo). A step is an action kind with params plus the sentence its own describe gave, its app (registry owner), tier, reach and reversibility. make(context, title, [{kind, params, source}]) checks each now and keeps refused ones as status 'cant' with why, so everything considered is shown. do() re-runs describe, requires the grant as the person, executes; change() merges only keys the step already has and re-describes; drop(); drop_plan().

The safety rule (_allowed): only kinds whose effect (core/action_effects.py) is records and undoable, and whose tier isn't never, may be steps; a plan's own steps.* kinds can't nest. So steps.do never reaches further than the default effect it is declared with, and a plan can't be a way around an approval card. Checked at make and again at do.

Actions (core/step_plan_actions.py): steps.plan_week, steps.do (act_with_approval; its card is the step's own sentence plus where it sits in the plan), steps.change, steps.drop, steps.drop_plan; claimed by the taught_skills app with the store. Undoing steps.do restores the plan file and the store the step changed together (both are written inside the one action).

A plan is a run (source 'plans', ref step_plan:<id>): started waiting on the person at the first step, a step noted with its action, finished done or stopped. The run record is written outside undo, so after an undo the run still says the step happened: it's a log.

plan_week (W-2) is code: core/today.today_items, each item with a suggested action becomes a step; one open week plan at a time.

Not built: dependencies between steps (prompt 25's T3 needs them), a plan from a model or a team, steps for outward kinds.
