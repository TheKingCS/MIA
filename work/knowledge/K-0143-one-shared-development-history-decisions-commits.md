---
id: K-0143
kind: implementation
title: One shared development history: decisions, commits, failures, experiments
status: confirmed
by: claude
created: 2026-11-08T19:04:03+00:00
concerns: core/dev_history.py, core/council.py, core/dev_knowledge.py, core/night_school.py, tests/test_dev_history.py
from: task:T-0021, dec:DEC-0071
---
T-0021 (DEC-0071 point 2): core/dev_history.py keeps decisions (DECISIONS.md, again on a status change), commits (author name, subject, files, the task named), the Fix-It Log's issues (only the code's own title and the count, never what the person said: the history is device-level) and the lab's proposals in data/dev/history, a DevStore, each once by signature. council.index() now searches it and the benchmark runs beside the chat and the activity log, so mia_answers and `tools.work history <words>` find a decision by its words. dev_knowledge.briefing appends dev_history.briefing(task): the decisions the task cites, recent commits and experiments on its files, read from the kept record only (no git, no index). Night School syncs it each night. What went wrong: the first full suite failed one test only in order: a Night School test synced real commits into the shared temp history and an unrelated briefing picked them up. Night School now syncs into the history beside its own store, so a test night keeps to its temp folder. And git log's %b body is multi-line: every field ends with a separator, so the files are what follows the last one.
