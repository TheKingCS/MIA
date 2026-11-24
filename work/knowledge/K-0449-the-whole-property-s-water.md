---
id: K-0449
kind: implementation
title: The whole property's water
status: confirmed
by: claude
created: 2026-11-24T18:40:32+00:00
concerns: core/water_budget.py, core/assistant_project_plan_actions.py
from: dec:DEC-0153
---
Phase A2 of docs/future/SMART_AG_PLAN.md. core/water_budget.py: uses from his records (people x 80 gal, confirmed garden beds at an inch a week, fruit trees at 10 gal a week, hens at a pint a day; the greenhouse said as not counted), tanks as data logger series water:<tank> at their latest level (log_water_level), the catchment roof (water.roof_sqft via set_preparedness) against his logged rain, and days the stored water carries the outdoor uses. Live: the model took the offline library for how long will my water last even with its description saying not to; ordering phrase-matched tools first was tried and made the live check worse (261 of 279), reverted; the fix was subjects=("water",) so direct_lookup answers it in code before any model.
