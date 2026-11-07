---
id: K-0054
kind: implementation
title: The rest of a life in the life state, as areas
status: confirmed
by: claude
created: 2026-11-07T07:14:05+00:00
concerns: core/life_areas.py, core/context_assembler.py, docs/schema/life_state.schema.json
from: dec:DEC-0108, file:core/life_areas.py
---
What: the life state (assemble_life_state_v2, /api/state) had full sections for money, property, assets, kitchen, workouts, projects, goals and missions, and nothing for 50 other stores. core/life_areas.py adds one section, areas: for each of 30 stores, a few counts and what's next (calendar: events this week, the next one; materials: how many are low; trips: planned and active), read live from the store.
Why one uniform shape instead of a section each: the schema (docs/schema/life_state.schema.json) and every reader stay simple; an area is added by one line in AREAS, and the schema needn't change.
Rules kept: numbers only, plus a name where the full sections already show names; never a memory's or a journal entry's words; the money areas hidden from a child, as finances are; a store that isn't here is PLANNED, one that fails is logged and empty, never breaking the state.
Mistake avoided: rewriting the schema JSON with a different indent made a 2,000-line diff for a 60-line change; write a file back the way it was formatted.
