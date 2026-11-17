---
id: K-0283
kind: implementation
title: F1: the specialists' roster and the counts-as-added bar in code
status: confirmed
by: claude
created: 2026-11-17T09:42:07+00:00
concerns: core/specialist_roster.py, core/specialists.py, core/specialist_models.py, web/specialists.js, tests/test_specialist_roster.py
from: dec:DEC-0199, task:F1
---
What: core/specialist_roster.py. check(spec, role, disciplines, calculators, tasks) lists what a specialist lacks: charter, limits, words, at least 2 starter questions, a ROLES entry, the caveat when its department is in SAFETY_DEPARTMENTS, and for each worksheet discipline (specialist_work.DISCIPLINES) calculators and at least 3 bench tasks with one that leaves an input out. standing(): added; built, not passing (no model passed: specialist_models.choose); in progress. roster() reads the bench results; PLANNED names the teams handoff's specialists not built yet, in project order (IoT first). The Specialists page and specialist_roster by voice read it.

Why: the plan's rule 'a name with a paragraph is not a specialist' was only words; now a test fails if a real specialist misses the bar's first part, and the page shows what's missing.

Found on the way: Software and AI engineering had one starter question. And the bench results must cover a specialist's disciplines: one benched before its tasks existed shows as not passing, which is right; re-run the bench after adding tasks (tools.eng_bench has no discipline filter, so it's a full run per model).
