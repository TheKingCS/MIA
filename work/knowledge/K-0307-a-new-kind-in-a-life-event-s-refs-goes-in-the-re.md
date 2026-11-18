---
id: K-0307
kind: implementation
title: A new kind: in a life event's refs goes in the record-type registry
status: confirmed
by: claude
created: 2026-11-18T15:38:59+00:00
concerns: core/record_types.py, core/links.py, core/life_events.py
from: commit:03b0332c
---
core/record_types.py is the one table of record kinds (links.KINDS is the same object). A kind the history names must be in TYPES (store, lister, id and name fields) or HISTORY_ONLY with why it can't be read by id yet; tests/test_record_types.py scans every life_events.record and on_change call and fails on one in neither. Moving a kind from HISTORY_ONLY to TYPES makes the read-back check it.
