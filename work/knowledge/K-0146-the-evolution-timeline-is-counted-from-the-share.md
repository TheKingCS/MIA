---
id: K-0146
kind: implementation
title: The evolution timeline is counted from the shared history, and the history keeps two dates
status: confirmed
by: claude
created: 2026-11-08T20:34:26+00:00
concerns: core/dev_evolution.py, core/dev_history.py, core/work_dashboard.py, tests/test_dev_evolution.py
from: task:T-0023, task:T-0021, dec:DEC-0071
---
T-0023 (DEC-0071's future item): core/dev_evolution.py counts month by month from data/dev/history, the activity log and the benchmark runs: decisions approved, commits, parts added (core/server = capabilities, tools, web = screens), tasks done, Fix-It issues found and fixed, lab merges and undos, each month's latest benchmark per kind (answered = rank under 2, from code = rank 0), and approved decisions as milestones. Served as `evolution` in /api/dev; the screen is the design session's. What went wrong: (1) the first count called a file 'new' when the 400-commit window first saw it: 222 'capabilities' in November were files touched. The history now reads every commit (1677) with --name-status and counts only added files. (2) Storing an old event with its own date as `at` made DevStore close a segment at every month change (13 segments for 1836 records), because it closes on a new month. Records now keep `at` as when kept and `on` as when it happened (dev_history.when()), one segment. The day-old derived store and the index were rebuilt (the index's docs allow it).
