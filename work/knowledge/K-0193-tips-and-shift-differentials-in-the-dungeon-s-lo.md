---
id: K-0193
kind: implementation
title: Tips and shift differentials in The Dungeon's loot, without changing how hours split
status: superseded
by: claude
created: 2026-11-09T07:02:53+00:00
concerns: core/work_dungeon.py, core/dungeon_actions.py, core/web_dungeon.py, core/assistant_dungeon_actions.py, web/dungeon.js, tests/test_work_dungeon.py
from: dec:DEC-0046
---
DEC-0046 partial finished, 2026-11-09. A Run carries differential (extra an hour) and tips. run_extra(d, run, regular, overtime) is differential x (regular + overtime x the overtime multiple), since US wage law counts a shift differential in the regular rate for overtime, plus tips as they are. Loot is linear, so every total adds each run's extra on top of loot(d, regular, overtime) rather than changing split_hours. In: dungeon.run's tips and differential params (approval says them), log_shift's voice arguments, a Tips field on the run card. Older runs load with 0 because DungeonBook keeps only known fields with their defaults.

Superseded 2026-11-09 at the merge: the design session built the same feature first (K-0161), and its version was kept.
