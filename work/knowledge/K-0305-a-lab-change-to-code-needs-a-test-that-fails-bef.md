---
id: K-0305
kind: implementation
title: A lab change to code needs a test that fails before it (DEC-0224)
status: confirmed
by: claude
created: 2026-11-18T15:38:59+00:00
concerns: core/dev_lab.py, core/self_merges.py
from: commit:f6689aba, dec:DEC-0224
---
LS-06: dev_lab.check makes a change to code ready only with proof: a test failing at the start that passes in the lab, or one of the change's own test files failing on the starting code. That second check runs only the lab's test files (pytest on them) in a _proof-<id> worktree of the start with those files checked out from the lab branch. The full start suite stays cached in _base-<commit>, so Night School doesn't run the suite twice per proposal. The proving tests are kept as tests.shown_by and named in describe, the reviewer's prompt and the merge message (Shown by: ...). Tests that fake the suite need the start to fail something the lab passes (tests/test_dev_lab.proven).
