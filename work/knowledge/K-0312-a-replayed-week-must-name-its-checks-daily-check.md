---
id: K-0312
kind: lesson
title: A replayed week must name its checks: daily checks write outside a test
status: confirmed
by: claude
created: 2026-11-19T02:56:37+00:00
concerns: core/replay.py, core/background_jobs.py, core/auto_backup.py
from: commit:3335ea02, commit:084f20e4
---
LS-09: core/replay.replay(context, jobs, start, checks) holds core.clock on each day and runs only the named daily checks. The first version ran all of them: the loops check opened work/tasks/T-0055.md and logged to work/activity.jsonl in the checkout, and the nightly backup wrote zips dated on the held days into the real 'MIA Backups' folder (its rotation then counts them as newest). The daily checks and the gate read core.clock now, so any frozen test of them holds both.
