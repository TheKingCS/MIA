---
id: K-0051
kind: method
title: How the self-audit reads her code, and where it can be wrong
status: confirmed
by: claude
created: 2026-11-07T06:16:10+00:00
concerns: core/self_audit.py, core/practices.py
from: dec:DEC-0108, file:core/self_audit.py
---
What: core/self_audit.py's two weekly audits. The code audit parses every file of her own code with ast and measures (function length, parameters, nesting, identical bodies by a hash of their syntax tree, silent broad excepts, file size, TODOs). The interconnection audit asks, for each store, whether its class records life events, whether links can point at it, and whether the Assistant's tools, the life state and the web pages reach it by name.
Where it was wrong, and the fixes: reading only core/assistant_*.py missed the tools registered in core/application.py and the quick spoken commands, so the registry is built the way the app builds it and each handler's own code read. Web pages are assembled by any core function named *_page, not only web_*.py. And a surface often reaches a store through another core module (the web reaches the boss book through boss_battles.py), so one import is followed. Files that build every store (application.py, personal_data.py) are left out of that, or every store would look reached.
What's still true: it reads by name, so a store reached through a variable (getattr with a name from a list) can still look unreached. Every task it opens says to check first.
