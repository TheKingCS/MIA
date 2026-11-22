---
id: K-0332
kind: implementation
title: The migration manifest: stores, a file sample and his programs
status: confirmed
by: claude
created: 2026-11-22T14:21:04+00:00
concerns: core/migration.py, tools/migration_manifest.py
from: task:FW-07a
---
FW-07a (REQ-IMP-002/009, REQ-CMP-003). core/migration.stores() walks DATA_DIR (not .keys, lab or history) and for each .json/.jsonl reads it through at_rest.open_text, splits it into records (jsonl lines; a list's items; an object's lists' items tagged with their key, plus the rest), and hashes the sorted canonical JSON of the records: re-sealing under a new key or reordering changes nothing, a damaged record does. sample_files picks every k-th of the sorted files in his folders (path under home, size, sha256; size only over 2 GB). installed_programs reads Windows' Uninstall keys (not SystemComponent ones); answer_for matches LINUX_ANSWERS as whole words (so git isn't Digital). The vendor list is broad on purpose: a list fitted to his PC would describe his hardware in a public repository. compare() names changed, missing and unreadable stores and changed or missing files; a store new after the move isn't a mismatch. The tool writes beside the backups and exits 1 on a mismatch (MV-01 stops there).
