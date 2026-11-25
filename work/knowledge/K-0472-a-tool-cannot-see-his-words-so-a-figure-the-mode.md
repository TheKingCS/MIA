---
id: K-0472
kind: lesson
title: A tool cannot see his words, so a figure the model passes is never called his
status: confirmed
by: claude
created: 2026-11-25T02:03:27+00:00
concerns: core/tax_setaside.py, tests/test_living_system.py
from: file:core/tax_setaside.py, file:docs/future/JARVIS_BRAINSTORM.md
---
tax_set_aside took a bracket parameter described as only if he said; on qwen2.5:14b the plain question How much should I set aside for taxes on the shop? came with bracket 12% all three times, and the answer said your 12%. Tools see only the arguments, never the turn, so core/tax_setaside.py now always gives 12% and 22% with any passed rate beside them and never says yours. The same check (run the plain question, read the arguments) belongs on any optional parameter that changes the answer. Also: test_living_system switching-the-model failed once in a full run and passed alone and with the new test, likely timing.
