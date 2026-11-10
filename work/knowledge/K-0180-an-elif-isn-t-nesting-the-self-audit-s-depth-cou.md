---
id: K-0180
kind: lesson
title: An elif isn't nesting: the self-audit's depth count was wrong
status: confirmed
by: claude
created: 2026-11-09T10:26:09+00:00
concerns: core/self_audit.py, core/plan_import.py, tests/test_self_audit.py
from: file:core/self_audit.py, file:core/plan_import.py
---
2026-11-09. The audit's _depth counted every block in Python's syntax tree, and the tree keeps an elif inside the previous if's else. So a flat chain of N elifs read as nested N deep: plan_import.parse came out at 18, and 54 functions were flagged in all. Splitting the goals and meals chains into _goal_line and _meal_line (pure, returning False for a label MIA doesn't know) didn't lower the count, which is how the bug showed itself: the new helpers were flagged too. _depth now treats an If that is the whole else of an If as the same level. A test pins ten elifs at depth 1 and if-for-if at 3. That leaves 15 deep-nesting findings, the deepest at 6 (food_table.load, sync's file_manifest and _sync_files). Before refactoring code to satisfy a metric, check that the metric measures what it says.
