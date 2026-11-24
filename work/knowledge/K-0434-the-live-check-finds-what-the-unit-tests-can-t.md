---
id: K-0434
kind: debugging
title: The live check finds what the unit tests can't
status: confirmed
by: claude
created: 2026-11-24T16:29:17+00:00
concerns: core/self_knowledge.py, core/question_plans.py, tests/live_model_check.py
from: dec:DEC-0052
---
Running tests/live_model_check.py on the PC (qwen2.5:14b, the embedding model there) on 2026-11-24 found three things the suite missed: is anything overdue went to the new budget_left (its description now says it is not bills or what is due); what is due in the greenhouse was taken by the project picture by meaning (its NOT_FOR now has due, status, how is, readings) and, older, by self_knowledge.wants_described, which read any what-is question ending with an app or topic name as asking her to describe it (now the name must be the whole subject); and I harvested 5 pounds of tomatoes was borderline (passed on a second run). Add a golden case for every new tool and run the live check before calling routing done.
