---
id: K-0087
kind: implementation
title: A plan page with sizes and a shopping list
status: confirmed
by: claude
created: 2026-11-08T01:25:11+00:00
concerns: core/plan_library.py, core/plan_actions.py, web/knowledge.js, server/app.py
from: commit:3f8200f, dec:DEC-0118, dec:DEC-0125
---
core/plan_library.detail(context, id, sizes) reruns the plan calculator for the sizes on the page (size_fields lists them with labels from SIZE_LABELS; read_sizes refuses a non-number or zero and the page shows why, in amber, while keeping the plan own size). The shopping list is shopping_list() priced in core with region.money (MIA.money in mia.js is the Money screen fetch, not a formatter). plan.keep keeps the worked size with its calc and args so a kept plan can be resized too; plan.delete is only for kept plans. Sizes travel to /api/knowledge/plan as sizes=length_ft=10,width_ft=12.
