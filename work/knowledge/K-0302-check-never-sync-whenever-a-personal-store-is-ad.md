---
id: K-0302
kind: debugging
title: Check NEVER_SYNC whenever a personal store is added
status: confirmed
by: claude
created: 2026-11-18T13:41:39+00:00
concerns: core/sync.py, core/personal_data.py
from: file:core/sync.py, file:tests/test_sync.py, dec:DEC-0243
---
Prompt 21 (2026-11-18) found four device-only files syncing to the phone because core/sync.py syncs every personal .json/.jsonl file not named in NEVER_SYNC: activity.json (window titles noted on the PC), recall_index.json, runs.json (the phone start-up recovery then marked a PC run stopped) and turn_traces.jsonl. Until the retention registry (DEC-0286) decides what syncs, a new store that belongs to one device must be added to NEVER_SYNC with a test in tests/test_sync.py.
