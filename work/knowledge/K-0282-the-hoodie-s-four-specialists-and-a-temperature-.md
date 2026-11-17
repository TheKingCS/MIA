---
id: K-0282
kind: lesson
title: The hoodie's four specialists, and a temperature read as a difference
status: confirmed
by: claude
created: 2026-11-17T09:22:37+00:00
concerns: core/eng_calcs.py, core/quantities.py, core/specialists.py, core/eng_bench.py, core/specialist_work.py
from: commit:cff02dea, dec:DEC-0198, dec:DEC-0197
---
What: S4's second batch (DEC-0198): Acoustics and audio, Audio signal processing, Textiles and wearables, Portable power, each with charter, limits, caveat, starter questions, role, worksheet disciplines (core/specialist_work.DISCIPLINES), 19 calculators in core/eng_calcs.py checked against hand-worked examples, and 22 bench tasks (ids a, d, t, p) with one missing input each.

How: the same shape as the greenhouse specialist (K-0280's bench picks each one's model). Decibels are a plain number (unit dB) on a log scale: the calculators add and subtract levels and never multiply them. Data sizes (bit, B, MB) are dimensionless with a factor of 8 a byte; data rates share Hz's dimension.

Why that way: Q-57 lists electrical and battery work as safety-critical, so the conductive thread and every portable power calculator carry the caveat; hearing isn't on that list, so Safe Listening Time says plainly how long is safe instead.

What went wrong: _read converted an input on another temperature scale as a difference, so 7 degC into a degF input became 12.6 degF, not 44.6. Inputs in degC, degF or K are points now (_POINTS). The greenhouse test passed anyway because inside minus outside cancels the error; a single point (a regulator's ambient) didn't. Routing words are matched as substrings: "spl" is inside "display", "mah" inside "mahogany", "acoustic" took acoustic guitar questions from music; they were left out. A teamwork test used "acoustics" as its example of a specialist that doesn't exist.
