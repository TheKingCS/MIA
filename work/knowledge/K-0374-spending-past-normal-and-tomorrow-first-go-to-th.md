---
id: K-0374
kind: test-procedure
title: Spending past normal and tomorrow first go to their tools
status: confirmed
by: claude
created: 2026-11-24T06:52:50+00:00
concerns: core/question_plans.py, core/assistant_today_actions.py
from: commit:cb6946c2
---
The last two everyday phrasings that a plan took: have I been spending more than normal (the month's money plan; now anything_unusual, which compares each category with its own normal month) and what's first tomorrow (the evening's plan; now evening_wrap, which names tomorrow's first thing). Both plans gained NOT_FOR words; both phrasings are in tests/test_everyday_phrasing_routing.py.
