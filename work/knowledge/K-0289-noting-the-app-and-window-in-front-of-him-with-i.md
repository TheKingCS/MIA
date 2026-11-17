---
id: K-0289
kind: implementation
title: Noting the app and window in front of him, with its safeguards
status: confirmed
by: claude
created: 2026-11-17T13:13:18+00:00
concerns: core/activity_watch.py, core/background_jobs.py, core/web_surfaces.py, web/shell.js, web/settings.js
from: dec:DEC-0197
---
What: core/activity_watch.py (DEC-0197, Zac's yes to Q-44). Every 30 seconds (job activity_watch, held by stop everything) the foreground window's program and title are read on Windows (user32 GetForegroundWindow and GetWindowTextW, psutil for the program) and kept as spans in activity.json, a personal store (7 days, titles cut to 120 characters). Password managers, private windows, sign-in pages and MIA's own window are skipped. "What am I working on?" names the app and title with the most time in the last half hour and the project whose name the title mentions. The sidebar says "Noting your active app" while it's on (/api/shell noting); Settings has the switch (activity.on) and an Erase button (activity.erase, undoable).
Why that way: DEC-0197 keeps the review's safeguards (names and titles only, an indicator, an erase button). It is on by default because Zac asked for it; off is one press. Linux needs a KWin script instead (Prompt 10); foreground() returns None there.
