---
id: K-0144
kind: implementation
title: Disagreements over decisions and designs, resolved and never dropped
status: confirmed
by: claude
created: 2026-11-08T19:11:12+00:00
concerns: core/disagreements.py, core/work_dashboard.py, tools/work.py, tests/test_disagreements.py
from: task:T-0022, dec:DEC-0071
---
T-0022 (DEC-0071 point 3): core/disagreements.py lets an agent object to a decision (DEC-0071) or a design doc (docs/X.md), checked against the repository; the author answers; an objection raised again after an answer makes it Zac's, and only `tools.work settle` (Zac typing the subject back, like approve) closes it. Kept in work/activity.jsonl (actions object/answer/settle, the subject in the task field), so it's in the shared history. open_disagreements() lists those and the tasks whose review is still argued over, Zac's first; /api/dev serves it as `disagreements` (the screen is the design session's). What went wrong: activity.search() upper-cases the task id, so a doc path never matched; state() filters the events itself.
