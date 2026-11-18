---
id: K-0297
kind: lesson
title: Check a research claim about a package against the installed package first
status: confirmed
by: claude
created: 2026-11-18T10:19:04+00:00
concerns: requirements.txt, os/requirements.lock
from: task:FW-01, file:docs/mia_os/MIA_OS_FINAL_TECHNOLOGY_STACK.md
---
FW-01 (2026-11-18). Prompt 17's technology check said PySide6 6.12 split WebEngine into a wheel whose release was delayed, and recommended pinning PySide6 below 6.12. On Zac's PC, PySide6 6.12.0 was already installed with PySide6_WebEngine 6.12.0.140 as its own dependency, and QtWebEngineCore imported. The pin would have downgraded a working setup. Before acting on a claim about a dependency, run pip list and an import on the machine that has it.
