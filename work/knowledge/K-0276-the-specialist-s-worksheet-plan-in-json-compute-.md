---
id: K-0276
kind: implementation
title: The specialist's worksheet: plan in JSON, compute in code, trace every number
status: confirmed
by: claude
created: 2026-11-17T05:47:49+00:00
concerns: core/specialist_work.py, core/eng_calcs.py, core/specialists.py, apps/knowledge/manifest.json
from: dec:DEC-0197
---
What (DEC-0197, plan S1): core/specialist_work.work(context, question). It picks the specialist (of those with calculators, the one whose words the question uses most; ties go by DISCIPLINES' order, so an ESP32 question goes to embedded, not maker), shows the model only that specialist's calculators, takes back JSON naming calculators and inputs, runs them with eng_calcs.calculate, then asks the model for a short explanation and checks it.

The check (untraced): every number in the explanation must be within 1% of a number in the question, a calculation's sentence, inputs or values (shown unit, SI, and x100 for shares), or a note. Integers 0 to 10 are let through as counts. A failure is sent back once naming the stray numbers; a second failure drops the model's prose and returns the calculators' sentences. So the floor is a plain correct answer.

Rules that hold whatever the model says: a calculator it wasn't offered is skipped; a required input it left out makes the calculator refuse and the worksheet ask the person; no calculator that fits means no figure, said plainly; the caveat rides on any safety-critical calculation. The question is framed as the person's words and notes as reference, never instructions.

What went wrong: work() called specialists.answer() without a folder, which counts an unanswered question into the real work/specialists/<id>.json: a test wrote strategy.json into the repo. work() takes `folder` now. The new tool needed its line in apps/knowledge/manifest.json (tools and tiers; tier "suggest": it reads and computes, changes nothing), which tests/test_app_registry.py and test_grants.py enforce.

Limits to know: the 1% trace can pass a number that coincidentally equals an allowed one in another role (a 30 A breaker called "30 ft"); the second-model review (S5) is what catches wrong reasoning. Not run against a real model yet.
