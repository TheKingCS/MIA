---
id: K-0141
kind: lesson
title: A rules check belongs with selling, and a payoff months away is worth less
status: confirmed
by: claude
created: 2026-11-08T18:34:14+00:00
concerns: core/development_engine.py, tests/test_development_engine.py
from: dec:DEC-0144
---
Two more ranking faults found by walking the year month by month (2026-11-08). (1) 'Check your state's cottage-food rules' became step 1 for most of the year, toward selling jams, before there was a canner, a harvest or a jar: a free one-hour first step on a valuable path made the whole path win. A legal check for selling belongs with selling, like the stand: it now requires something_to_sell (proof), and a test holds every provider of food_sale_ok to that. (2) In September with preserves put up and a stand, it still pointed at seed cups for spring starts: a payoff six months off was valued like one now. _path_score now divides by (1 + wait/6), the wait being the longest time until a path step's season opens. Result: summer says preserve the harvest, winter says build the seed shelf, a coop in May says get hens, jars in September say check the rules and sell them.
