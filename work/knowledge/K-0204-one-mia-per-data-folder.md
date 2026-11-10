---
id: K-0204
kind: implementation
title: One MIA per data folder
status: confirmed
by: claude
created: 2026-11-10T13:35:38+00:00
concerns: core/instance_lock.py, core/application.py, core_main.py
from: commit:bfc18243, file:core/instance_lock.py
---
core/instance_lock.py takes an operating-system lock on data/.mia.lock (msvcrt.locking on Windows, flock elsewhere) and keeps the file open for the process's life, so a crash leaves nothing stale. A second desktop says MIA is already running and quits; MIA Core logs it and exits 1. Asking again in the same process is True (tests build the app many times); tests point PATH at their own folder.
