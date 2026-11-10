---
id: K-0181
kind: implementation
title: Two of the deepest functions flattened; sync's file reconciliation left alone
status: confirmed
by: claude
created: 2026-11-09T10:31:46+00:00
concerns: core/food_table.py, core/sync.py, tests/test_food_table.py
from: file:core/food_table.py, file:core/sync.py
---
2026-11-09. core/food_table.load parsed each row's portions inline. That is now portions_of(text), which is pure and tested, and leaves out a part with no grams, as before. core/sync.file_manifest walked each folder inline. That is now _folder_files(label, root), with early continues. Deliberately not refactored: sync._sync_files, the per-file push, pull and keep-both decision. A slip there loses someone's files, and untangling it buys nothing they can use. Change it only with a reason, with sync's 62 tests and a new test for the case at hand.
