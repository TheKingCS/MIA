---
id: K-0309
kind: implementation
title: A new data file goes in the retention registry, which decides what syncs
status: confirmed
by: claude
created: 2026-11-19T02:56:37+00:00
concerns: core/retention.py, core/sync.py
from: commit:8686ff0a, dec:DEC-0286
---
LS-03 (DEC-0286): core/retention.py lists every .json/.jsonl file named in core/ and modules/ with its class (record, log, derived, device, mia, config), how long it's kept, what happens at the end, and whether sync carries it. sync.NEVER_SYNC is derived from it and syncable() asks retention.syncs(); an unknown name syncs as before and is logged once. tests/test_retention.py fails on a file missing from it. Making the table moved the device's own files (phone_link, module_usage, page_usage, the test corpora in data/) and MIA's own records off the phone.
