---
id: K-0162
kind: implementation
title: What's Next's spring case solved: two urgencies added, not one multiplied
status: confirmed
by: claude
created: 2026-11-09T05:31:30+00:00
concerns: core/development_engine.py, tests/test_development_engine.py
from: dec:DEC-0144
---
Follows K-0153 (DEC-0144), 2026-11-09. _path_score now adds, after the seasonal discount, a window term: when every seasonal step on a path is in season, WINDOW_BONUS (60) times the months its season stays closed over 12 (a raised bed's March-May window gives 45), and the same term for a sale that can start now at three quarters of the bonus (goods already made are worth most while they're ready). Additive is what made it work: K-0153's multiplier scaled with the path's worth, so it either beat ready revenue or did nothing; a fixed term moves close calls only. Result: a fresh start gets the raised bed in March to May and the compost bin the rest of the year; jars in September still go to the cottage-food check before a cold frame. The spoken-plan test had pinned April's old answer (the compost bin) and now expects the bed.
