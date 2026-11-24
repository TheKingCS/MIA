---
id: K-0373
kind: test-procedure
title: A question plan can steal a tool question by its words
status: confirmed
by: claude
created: 2026-11-24T06:39:54+00:00
concerns: core/question_plans.py, tests/test_everyday_phrasing_routing.py
from: commit:ee9dc9ee
---
Plans run before tools in a turn, and on the phone they match by their own words: tonight took is it going to frost tonight, week review took what should I plant this week, coming up took the homestead this spring and will I be short next month. Each of those plans now has NOT_FOR words (weather, growing, the flock, and for coming up short or cash flow) that leave the question to its tool, checked both by meaning and by words, with tests that the plans still take their own questions. Thirteen more everyday phrasings were added to tests/test_everyday_phrasing_routing.py.
