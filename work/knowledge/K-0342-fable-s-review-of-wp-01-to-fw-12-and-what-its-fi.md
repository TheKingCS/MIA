---
id: K-0342
kind: lesson
title: Fable's review of WP-01 to FW-12, and what its findings teach
status: confirmed
by: claude
created: 2026-11-22T20:52:33+00:00
concerns: core/sync.py, core/home_link.py, core/restore_drill.py, core/auto_backup.py, core/linux_apps.py, core/lab_push.py, core/llm_manager.py, tests/conftest.py
from: commit:43f3f1cb, commit:905337bd
---
Three independent reviewers read the work from WP-01 to FW-12 (2026-11-22); each finding was checked against the code before fixing, and each fix has a test in tests/test_review_2026_11_22.py that fails on the old code. Patterns worth carrying forward: (1) a name reused inside a loop shadowed an earlier flag (sync's first-after-pairing), so one pulled file changed how every later file merged; name flags for what they mean. (2) An order that destroys data must prove who sent it: the lost-device erase now needs an HMAC of a fresh nonce under the device's own key. (3) A check that opens files must open them the way MIA does (a .jsonl may be sealed whole, not line by line), or a healthy backup reads as broken. (4) Rotation rules must be tested night by night over a long run, not on one hand-picked list: the monthly tier never filled. (5) Anything started from a background service on Linux needs the user's session (systemd-run --user plus the shell importing WAYLAND_DISPLAY). (6) A destructive function that reaches outside data/ (the erase's content folders and config) must be stubbed by conftest: the erase test removed the checkout's own folders until other_folders was split out. (7) A time-based signal needs both edges: needs-you counts cards from 3 seconds to 15 minutes old.
