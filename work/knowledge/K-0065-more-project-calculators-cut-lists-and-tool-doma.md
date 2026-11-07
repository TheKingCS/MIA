---
id: K-0065
kind: implementation
title: More project calculators, cut lists, and tool domains that never save on a question
status: confirmed
by: claude
created: 2026-11-07T14:21:28+00:00
concerns: core/build_calcs.py, core/assistant_plan_actions.py, core/plan_library.py
from: dec:DEC-0118, dec:DEC-0119
---
Added chicken coop (4 sq ft a hen inside, 10 outside, 1/2 in hardware cloth with an apron), shelving, bookshelf (sag note past 34 1/2 in inside), lean-to, compost bin, cold frame, picnic table, firewood rack (cords held) and stairs (risers at most 7 3/4 in, treads at least 10 in, handrail note at 4+ risers) to core/build_calcs.py, each a built-in plan with steps. custom_cuts packs a person's own parts: boards by buy_boards, sheets by sheets_for (rows along a 4x8, biggest first, either way round). parse_parts in assistant_plan_actions reads parts said plainly.
What went wrong on the 3B model: it sent a stair rise as height_in (sizes_for now takes any height as the rise); it put a parts list into material_list where bench matched the workbench (a parts argument now always goes to cut_list); and once it answered how do I build stairs by calling start_plan_project, which would have made a project unasked. keep_plan and start_plan_project now live in their own domain (plan_saving) attached only by words like as a project or save this plan, as plan_shopping_list did with buying words. Keywords like garage shelves and a bare project pulled tools into small talk and were narrowed. A patch script written through a bash heredoc turned an escaped newline into a real one (memory: no backslashes through Bash): fixed with Edit.
