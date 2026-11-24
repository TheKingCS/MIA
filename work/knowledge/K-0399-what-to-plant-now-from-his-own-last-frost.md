---
id: K-0399
kind: implementation
title: What to plant now from his own last frost
status: confirmed
by: claude
created: 2026-11-24T10:51:38+00:00
concerns: core/planting_now.py, core/garden_plans.py
from: commit:cb842196
---
core/planting_now.py dates the Planner's CROPS calendar (garden_plans.schedule) from garden.last_frost, the frost date he gave when planning; the season ahead is this year's until 90 days past it, then next year's. window says a crop's next step (start indoors, transplant or sow) with its date, LATE_DAYS of grace, or past; now lists what's due in DUE_DAYS. Without his frost date she asks. what_to_plant is read-only.
