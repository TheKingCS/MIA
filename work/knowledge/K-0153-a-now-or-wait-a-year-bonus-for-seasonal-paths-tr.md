---
id: K-0153
kind: failed-experiment
title: A 'now or wait a year' bonus for seasonal paths: tried at two strengths, reverted
status: confirmed
by: claude
created: 2026-11-08T22:08:24+00:00
concerns: core/development_engine.py, tests/test_development_engine.py
from: dec:DEC-0144
---
DEC-0144, 2026-11-08 afternoon. Walking the year: a fresh start in March or May gets 'build a compost bin' rather than a raised bed, though a bed missed in spring costs a season and a bin can be built any month. Tried in _path_score: when every seasonal step on a path is in season now, multiply its worth by 1 + (months the season stays closed)/24. It picked the bed in spring, but also beat revenue ready now: jars on hand in September got 'build a cold frame' instead of 'check the rules and sell them', and two tests holding sales order failed. At /48 the tests passed but the spring case didn't change and jars in April went to seed cups. Reverted; nothing committed. What it needs instead: the urgency of a window as its own term weighed against the urgency of goods already made (they keep, but their value is ready now), or the compost bin's compounding not counting a seed-mix path the person can't use until next spring. Also tried the same afternoon: what's unlocked through a slow step counted at half in compounding_value. It didn't move the spring case, because the winning path's goal is the finished compost itself, whose own benefit and compounding carry it, not the bin's; it only changed a coop owner's January (feed bin first). Reverted too. Open for the next engine session.
