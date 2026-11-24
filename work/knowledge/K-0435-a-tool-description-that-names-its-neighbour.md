---
id: K-0435
kind: lesson
title: A tool description that names its neighbour
status: confirmed
by: claude
created: 2026-11-24T16:46:23+00:00
concerns: core/assistant_tools.py, tests/live_model_check.py
from: dec:DEC-0052
---
The live check on qwen2.5:14b (2026-11-24) had nine cases where the model picked a neighbouring tool: list_inventory for what materials or products do I have, whats_in_the_workspace for what am I working on, log_lab_reading for show me the readings, add_grocery_item for a named recipe, get_pet for a person, get_trip_route for the next trip, list_expeditions to describe one. Each was fixed by a description saying what it is for and naming the other tool to use instead; every one passed twice, and the whole set went from 253 to 264 of 271. Five left (rental income, budget check-in, a mower make, business use, mission as an ordinary word) already have clear descriptions: the model still errs there.
