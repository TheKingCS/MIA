---
id: K-0423
kind: debugging
title: A harvest that made up history
status: confirmed
by: claude
created: 2026-11-24T14:52:41+00:00
concerns: core/harvest_log.py, core/assistant_project_plan_actions.py
from: commit:42aa05a6
---
Review of 42aa05a6: a crop not in the grow lab got a batch planted today (a false Planted event, zero days to harvest); now she asks roughly when it was planted and dates the batch by that. Also: strawberries/leaves plurals (singular), this year grouped by singular name so Tomato and tomatoes are one row, a named place none of the batches is in is a new batch there (passed as asset_id, not only notes), eggs/honey/milk/meat refused with where they go, units ending in s and dozen not pluralised, the value said beside the plantings cost and never called savings without it, and the bare harvest keyword, dug up and how much did I grow dropped (when should I harvest the garlic, how much did I grow my savings).
