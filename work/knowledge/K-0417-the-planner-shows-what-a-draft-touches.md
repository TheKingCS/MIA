---
id: K-0417
kind: implementation
title: The Planner shows what a draft touches
status: confirmed
by: claude
created: 2026-11-24T14:07:28+00:00
concerns: core/project_ripple.py, web/planner.js, server/app.py
from: dec:DEC-0125
---
Step 5 of docs/future/UNIFIED_INTELLIGENCE.md: each draft on the Planner page has a What It Touches panel, read from /api/planner/touches only when opened (the picture runs a dozen lookups, too many for every page load). core/project_ripple.for_plan runs the same _picture the spoken question does, at the draft own size; a garden plan shows its beds and crops in place of a build, and its kind comes from its Library plan, else its title.
