---
id: K-0237
kind: implementation
title: Homeostasis v1: deferrable work waits, failing jobs back off, she says so
status: confirmed
by: claude
created: 2026-11-15T16:15:33+00:00
concerns: core/homeostasis.py, core/scheduler.py, core/background_jobs.py, core/runtime.py, tests/test_living_system.py, core/world_intel.py
from: dec:DEC-0173, dec:DEC-0174
---
What: core/homeostasis.py (conditions, reason_for, backoff_seconds pure; Homeostasis reads psutil, the battery and the connection at most every 30 s) and core/scheduler.py (Scheduler.defer asked before each run: a job told to wait is due one interval on and counted as a deferral, never a failure; failures_in_a_row with backoff after three, up to six hours, on_backoff told once). BackgroundJobs.schedule wires both; the daily tick skips deferrable checks the same way. /api/runtime/health shows homeostasis.report().

Why this shape: the doctrine's homeostasis without a new service (DEC-0173). Only deferrable work waits: World Intelligence, Good News, Night School, the dependency audit, the system map, the Chronicle issue, photo captions, Seasons of Memory. Alarms, the battery, the inbox, backups and the daily tick never wait. Busy means three readings in a row at 85% or more, not one spike. Zac's condition ("make a notice about it"): one gate candidate (topic homeostasis) when an episode of easing off starts, and one when a job starts backing off; nothing again until things clear.

What to watch: under pytest the machine isn't read (a busy machine running the suite would make tests skip work at random); tests pass read=. psutil.cpu_percent(interval=None) returns 0.0 on its first call, which counts as clear.

Also L1: tests/test_living_system.py. The identity check is a ratchet over files saying "You are MIA" in their own words (Night School's "You are MIA's teacher" isn't one); the epistemic contract is a class attribute EPISTEMIC on a store (record, source, at, how, checked), with every older store on a baseline that may only shrink; continuity across models compares the assembled life state and the store files with llm.backend switched.
