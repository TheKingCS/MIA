---
id: K-0232
kind: implementation
title: Runtime extraction 1: the timers and daily checks left MIAApplication
status: confirmed
by: claude
created: 2026-11-15T12:33:54+00:00
concerns: core/background_jobs.py, core/scheduler.py, core/application.py, core/core_runtime.py, core/loop_coverage.py
from: dec:DEC-0155, dec:DEC-0168
---
What: the ten QTimers in MIAApplication.__init__ and their bodies (lines 685-1591 of core/application.py: every _check_* method, _offer, _while_stores_free, _capabilities_on_hand; 43 daily checks) moved unchanged into core/background_jobs.py as class BackgroundJobs, with two tables: JOBS (name, seconds, method) and DAILY_CHECKS (name, method). core/scheduler.py is a passive scheduler: run_due() runs what's due on the caller's thread, each job under the store lock non-blocking (busy: stays due, retried at the next tick, counted as a skip), exceptions logged and recorded, due again from when it finished (no catch-up after sleep). The desktop keeps one QTimer (5 s) calling scheduler.run_due on the Qt thread; a headless runtime will call run_forever() on a thread.

How it was done safely: MIAApplication now inherits BackgroundJobs, so the 36 test files that call MIAApplication._check_x(stub, ...) on __new__ stubs needed no change. The imports the moved block needs were found with ast (names used in the block that application.py binds by import): 34 names, none from Qt or gui. A crude ast pass checked for undefined globals. tests/test_background_jobs.py pins the ten intervals and the 43 checks in order, and checks in a fresh interpreter that importing the jobs loads no PySide6, gui or modules.

What broke on the way: core/loop_coverage._checks read the daily checks from application.py's source with a regex on self._check_x; it now reads DAILY_CHECKS' lines in background_jobs.py. docs/EVENTS.md's publisher column and the atlas needed regenerating.

One behaviour difference, deliberate: a job skipped because the stores were busy used to wait a whole interval (up to 10 minutes for mail); now it's retried at the next 5-second tick.

The bigger finding for step 4: the full MIA is only built inside MIAApplication.__init__. build_core_context (the phone, export_state) sets 63 context services where the desktop sets 91, and registers 41 tool registrars where the desktop has 62 (25 vs 111 inline AssistantAction). Missing headless: communication (the gate), conversations, insights, finance, homestead, workout, classroom, textbooks, plans, search, online_reminders, push_subscriptions, store_lock and more. The runtime needs one Qt-free builder of the full context.
