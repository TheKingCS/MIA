---
id: K-0064
kind: implementation
title: Plans shelf and material lists in code; humor levels
status: confirmed
by: claude
created: 2026-11-07T14:02:51+00:00
concerns: core/build_calcs.py, core/plan_library.py, core/assistant_plan_actions.py, core/personality.py, core/assistant_humor_actions.py
from: dec:DEC-0118
---
Built DEC-0118. core/build_calcs.py works out material and cut lists (stud wall, floor, deck, raised bed, fence, slab, gable shed); buy_boards packs cuts into stock lengths first-fit-decreasing with a kerf between pieces and a quarter inch of slack (two exact halves of a board must still fit, or a 10x12 slab wanted 17 rebar sticks instead of 13). MaterialList.add merges same-size lumber but joins the notes per part, so a shed's 2x6s still say joists and rafters. core/plan_library.py: built-in plans (calculators plus steps), kept plans (household store plans.json), and files in reference_library/plans/ served only from inside that folder.
What went wrong with the 3B model's tool calls: it fills unused size fields with 0, sends keep as the string "false", and drops one of two numbers. Fixes: 0 means not given, a _yes() parser, and a size string ("10 by 12") split in code as width, length, height. plan_shopping_list sat in the same domain as material_list and the model picked it for "what do I need to build"; it now has its own domain attached only by buying words. The words plans and buy attached tools to small talk ("my dinner plans", "buy a boat"): removed as domain keywords.
Humor: humor_for decides in code (light turn, chance per the person level, random flavor with an example); the 3B model copied the examples far better than a description.
