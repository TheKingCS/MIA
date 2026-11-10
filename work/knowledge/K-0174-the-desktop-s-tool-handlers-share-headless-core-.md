---
id: K-0174
kind: implementation
title: The desktop's tool handlers share headless Core's bodies
status: confirmed
by: claude
created: 2026-11-09T09:22:59+00:00
concerns: core/application.py, core/core_runtime.py
from: file:core/application.py, file:core/core_runtime.py
---
2026-11-09, from the self-audit's same_body findings. Eighteen Assistant tool handlers (add/delete alarm, notes, inventory, waypoint distance, recall activity, delete calendar event, power status, missions and objectives) were written twice: as MIAApplication staticmethods in core/application.py and as module functions in core/core_runtime.py, which exists so headless Core never imports the Qt app. A fix to one copy would have missed the other. The desktop copies now import core_runtime locally and return its function's result, keeping their docstrings. The rewrite was done from the AST, and it asserted that each pair's statements were identical before touching them, so no behavior changed. The dependency runs one way, application to core_runtime and never back. Full suite 6,099 passed.
