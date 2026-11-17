---
id: K-0275
kind: implementation
title: Engineering calculators, units and a bench that checks answers in code
status: confirmed
by: claude
created: 2026-11-17T05:38:11+00:00
concerns: core/quantities.py, core/eng_calcs.py, core/eng_bench.py, tools/eng_bench.py, core/specialists.py, core/stop.py
from: dec:DEC-0197, dec:DEC-0198
---
What (DEC-0197, the local specialists plan S0a and S2's start): core/quantities.py gives values a dimension vector (length, mass, time, current, temperature); + and - need the same dimension, * and / combine them, so V*A prints as W and m+V raises UnitError. core/eng_calcs.py is a registry of Calculator(id, discipline, inputs with units and defaults, basis, safety); calculate() parses inputs (a bare number takes the declared unit), names every missing required input, refuses negatives, and returns values, a sentence, the basis and the caveat for safety-critical ones. core/eng_bench.py holds tasks whose expected answer is computed by the calculator at scoring time, asked "alone" (ANSWER:/NEED: lines) and with "tools" (the model replies JSON naming a calculator and inputs; code runs it).

Why the bench counts "guessed" separately: five tasks omit an input that matters. Giving a number for one of those is the failure that hurts in electrical work, so it is not folded into "wrong". In tools mode a model that fills in an input the question never gave is judged guessed even though the calculator ran.

Tables used and where they bind: copper AWG resistance per 1000 ft at 20 degC; ampacity from the 60 degC column; 14/12/10 AWG capped at 15/20/30 A breakers; a continuous load sized at 125%; voltage drop out and back. The joist calculator wraps build_calcs.joist_for (a rule-of-thumb table, said so in its basis).

What went wrong: (1) the E12 rounding used the wrong decade (150 ohm came out as 1000): E12 runs 10 to 82, so the decade is one power lower. (2) Quantity printed 10000 ohm as 1e+04. (3) parse read "1,500 W" as 1.5 W: a comma group of three digits is thousands, a single comma with no point is a decimal. All three were found by printing every calculator's sentence and checking it by hand before writing tests, then pinned in tests.

Not done: nothing calls the calculators from conversation yet (S1's worksheet and a tool). No lye calculator on purpose: saponification values from memory would be dangerous; the crafts specialist's limits say so. The bench has not been run against a real model: that needs the PC.

Also fixed: tests/test_stop.py's restart test called for_shell() with the real clock against a hold ending 2026-11-16 17:00, so it failed from the next day on; for_shell takes `now`.
