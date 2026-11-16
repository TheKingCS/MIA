---
id: K-0269
kind: implementation
title: UI-2, the stop: "stop" and "stop everything" in code
status: confirmed
by: claude
created: 2026-11-16T13:20:59+00:00
concerns: core/stop.py, tests/test_stop.py, core/grants.py, core/communication_gate.py, core/background_jobs.py, core/assistant_turn.py, server/app.py, web/shell.js
from: dec:DEC-0181, dec:DEC-0185
---
What: core/stop.py is section 4 of MIA_OS_AUTONOMY_AND_TRUST_REQUIREMENTS.md as code (REQ-AUT-010, DEC-0181, DEC-0185). recognise() takes only whole messages ("stop", "stop everything [until tonight]", and "carry on" only while a hold is on), so "stop the timer" still reaches its own tool. The turn pipeline calls stop.handle() before pre_turn, so no model is involved.

How: "stop" calls existing ends (voice.stop_playback, taught_skills.stop, Browser.drop_pending plus rejecting its proposal, and finishing browser-routine runs as stopped on the run record). "Stop everything" writes the person's setting mia.stop_everything ({since, until}) and four places ask it: the scheduler and the daily checks (BackgroundJobs._defer_reason, by job name), the communication gate (GateState.stopped: DEFER, urgent still delivered), and grants.require (MIA-initiated capabilities above suggest are refused). The screen control is POST /api/stop (never an approval card: a stop that waits for a yes isn't a stop).

Why this way: one hold flag asked at the existing choke points, rather than each engine learning to stop. grants.require has no context, so stop keeps a process copy (held_now) refreshed whenever the setting is read or written; it lapses by itself at the named time.

What to keep: every job in JOBS must be in JOBS_THAT_WAIT or JOBS_THAT_RUN (a test fails otherwise); daily checks not named only offer messages, which the gate holds. Nothing in the module may reach the greenhouse or a device (a test reads the source).

What went wrong: the stopped banner pushed the full-height side panels off the bottom; they now sit below it using the banner's measured height (--stopped-h). The demo frame needs /schema/ served from docs/schema to draw its sidebar when screenshotting.

Left: a turn already in progress finishes its reply before the stop is handled (her speech is cut at once), a fetch in progress finishes rather than being dropped, and the glasses have no button yet.
