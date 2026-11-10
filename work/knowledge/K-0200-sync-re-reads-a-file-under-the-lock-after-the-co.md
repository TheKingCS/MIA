---
id: K-0200
kind: implementation
title: Sync re-reads a file under the lock after the computer answers
status: confirmed
by: claude
created: 2026-11-10T08:58:24+00:00
concerns: core/sync.py
from: commit:0b6e7750, file:core/sync.py
---
sync_now read a file, waited up to 30 seconds for the computer, then wrote the result without looking again, so an edit made meanwhile was lost. It now re-reads under the lock and, if the file changed, merges that edit with the computer's copy, preferring it on a conflict. The clock tie-break for both-changed records is still there (roadmap 1.6 remainder).
