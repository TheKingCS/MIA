---
id: K-0338
kind: implementation
title: The move rehearsed on synthetic data
status: confirmed
by: claude
created: 2026-11-22T18:08:39+00:00
concerns: os/poc/vm/move_rehearsal.py, .github/workflows/mia-os-vm.yml
from: task:FW-07b
---
FW-07b. os/poc/vm/move_rehearsal.rehearse(scratch): synthetic stores as on Windows (a household list, a person's conversations, an appended log), migration.stores before, backup_manager.create_backup with _DATA_DIR and _CONFIG_FILE pointed at the scratch Windows folder, restore_backup into a fresh scratch folder, migration.compare must match all three; then a record changed by hand must be named. tests/test_move_rehearsal.py runs it on any machine; the VM step runs it inside the image with its own Python, after the suite step has copied the repository to /var/tmp/mia-suite.
