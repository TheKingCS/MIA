---
id: K-0139
kind: lesson
title: A payoff jumped ahead of its infrastructure: plan the whole path, weigh it whole
status: confirmed
by: claude
created: 2026-11-08T17:05:00+00:00
concerns: core/development_engine.py, tests/test_development_engine.py
from: dec:DEC-0144
---
The first development engine let 'Sell seedlings and produce' come right after a raised bed, because its requires said only 'beds', and next_step picked the best doable leaf. Zac: going straight to selling plant starts without the infrastructure to manage it isn't a good idea. Two fixes. (1) The catalog says what each step really needs: selling starts requires grown_seedlings (proof, from a first batch) and sales_outlet; the stand that provides the outlet itself requires the proof; the first batch requires seed cups, seedling space and seed mix; each has a made option (toilet-roll cups, a scrap shelf) beside a bought one. A test holds the rules for every candidate. (2) next_step looks ahead: path_to resolves every goal's needs recursively (made first, then cheapest), each whole path is weighed, and the first step of the best one is recommended with the path and readiness checks. A second bug surfaced while checking scenarios by hand: with an unknown budget the $800 greenhouse won everything, because cost was a tiny subtraction (0.05 a dollar) against value x10. _worth now divides value by the money and hours it takes, so cheap foundations come first and a big build waits. Check recommendations against realistic scenarios, not only the tests.
