---
id: K-0414
kind: decision
title: The project picture: what a planned project touches
status: confirmed
by: claude
created: 2026-11-24T13:35:08+00:00
concerns: core/project_ripple.py, core/question_plans.py, core/assistant_project_plan_actions.py
from: dec:DEC-0052
---
Zac asked for a unified layer: a greenhouse he plans should be understood against his budget, materials, garden, water, power, time and research goals. Built as a question plan (project picture) plus the project_picture tool, because question plans already gather facts from many apps onto one marked sheet the model only words. core/project_ripple.py: KINDS say which areas a kind of project touches; each area is read through the tool or store that already answers it (a tool whose service isn't there is said as missing, never run into a failure); NEEDS adds one guidance line an area, marked as guidance. The build comes from the Library plan at its size against the workshop's stock; its known cost goes through question_plans.freedom_with (pulled out of the afford plan). Nothing is planned or changed. Next steps are in docs/future/UNIFIED_INTELLIGENCE.md.
