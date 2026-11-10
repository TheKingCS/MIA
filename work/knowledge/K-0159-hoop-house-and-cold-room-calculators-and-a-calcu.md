---
id: K-0159
kind: implementation
title: Hoop-house and cold-room calculators, and a calculator counted as written by its plan
status: confirmed
by: claude
created: 2026-11-09T04:49:20+00:00
concerns: core/build_calcs.py, core/plan_library.py, core/assistant_plan_actions.py, core/trades.py, core/trade_jobs.py, tests/test_plan_library.py
from: dec:DEC-0149, dec:DEC-0118
---
DEC-0149/0118, 2026-11-08 night. core/build_calcs.hoop_house: bows every 4 ft (ceil(length/spacing)+1), two ground posts each, three purlin runs, base and hip boards packed by _boards, end-wall studs at the rise, film sized to wrap the end bows. core/build_calcs.cold_room: four stud_wall()s merged (2x4: the foam is continuous over them, so the cavity depth doesn't set the R-value), polyiso layers rounded up to whole 2 in boards so it is never short of the asked R-value, a BTU figure from floor area sent back to the controller maker's chart. stud_wall already adds CODE_NOTE, so cold_room drops the merged copies and ends on one. Both are plans on the shelf (hoop-house, cold-room), named on their jobs, and reached by voice through assistant_plan_actions STRUCTURES. trades.depth() counts greenhouse_calc and cold_room_calc as written through CALC_FOR once their job's plan is on the shelf; the loop test reads depth()['next'] instead of a hard-coded id.
