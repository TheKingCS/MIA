---
id: K-0207
kind: debugging
title: A terminal window that flashes on the desktop is a child process without the no-window flag
status: confirmed
by: claude
created: 2026-11-10T14:27:59+00:00
concerns: core/doc_freshness.py, core/device_framework.py, tests/test_no_flashing_windows.py
from: commit:7b482ae4, file:tests/test_no_flashing_windows.py
---
Zac saw a window open and close on his PC over and over. The desktop runs under pythonw, which has no console, so on Windows every child process started without creationflags gets a terminal window of its own for as long as it lives. The culprit was her own daily documentation check (core/doc_freshness.py), which ran git once per file changed in the week: a hundred files, a hundred flashes. An earlier round of the same symptom came from test runs and detached jobs, so the first guess was wrong this time; what found it was listing every subprocess call in core/, server/, gui/ and modules/ and reading which ones a daily check reaches. Fixed by passing subprocess.CREATE_NO_WINDOW on those calls and on the thirteen others without it (OCR, camera snapshots, updates, the local model, scripts, volume, drives, Tailscale). tests/test_no_flashing_windows.py reads the code with ast (it starts nothing) and fails on any subprocess.run/Popen/check_output/call/check_call in those packages that doesn't pass creationflags; a job that must outlive her uses dev_lab.quiet_job_flags(). When writing a new call: creationflags is 0 off Windows, so getattr(subprocess, 'CREATE_NO_WINDOW', 0) keeps it portable.
