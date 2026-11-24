---
id: K-0385
kind: security-finding
title: A web search after outside text must still be held
status: confirmed
by: claude
created: 2026-11-24T08:36:30+00:00
concerns: core/main_thread.py, core/grants.py, core/assistant_actions.py, core/tool_loop.py
from: commit:f982d0d4
---
A fourteenth fresh review of f982d0d4: counting observe tools as read-only made look_up_online a lookup, so after reading outside text the tool loop would run a fresh web search the model composed from it (words picked by injected text sent out to search engines) instead of holding it; and browser_read and look_up_online answers were cut to the loop's 1,500 characters (a page's controls come after its text). Both are in OUTWARD and keep a change's path. Also: direct_lookup answered questions naming another app's record without the model (what's running on the pickup truck); a lookup lost its named-tool nudge for commands (wrap up my day); _whole missed plurals (the ATVs); grants.tiers() re-read manifests on every call when none were found and filled unlocked; default_tool_tier now judges by name only.
