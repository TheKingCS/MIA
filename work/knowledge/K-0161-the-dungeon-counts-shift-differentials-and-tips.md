---
id: K-0161
kind: implementation
title: The Dungeon counts shift differentials and tips
status: confirmed
by: claude
created: 2026-11-09T08:19:38+00:00
concerns: core/work_dungeon.py, core/dungeon_actions.py, core/web_dungeon.py, web/dungeon.js
from: dec:DEC-0046, dec:DEC-0057
---
core/work_dungeon.py: a job has `differential` (extra an hour) and `differential_days` (parse_days takes 'weekends', 'sat, Sunday'...); a run has `tips` and its own `differential` (None: the job's for its day). run_differential, extras (differential on every hour, overtime hours at the overtime multiple because a differential is part of the regular rate, plus tips as they are) and run_loot (loot + extras). Every place that priced a run now uses run_loot or adds extras: web_dungeon (_run_row, the week/month/pace totals), weekly_checkin (_loot, _ahead), the_loop (_reminder, week), dungeon_actions (describe and execute). New action dungeon.tips {run_id, tips} for tips counted after the shift; dungeon.run takes tips. The Dungeon page: a Tips field beside Hours, Add Tips / Change Tips on cleared runs, the differential on Setup and on each run. LIMITS['dungeon'] no longer says 'yet', so the Dungeon is 'implemented' in capability_status; the partial-piece test now uses real_estate.
