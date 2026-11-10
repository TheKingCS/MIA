---
id: K-0199
kind: implementation
title: The tool gate: offered tools only, and no change straight after outside text
status: confirmed
by: claude
created: 2026-11-10T08:58:24+00:00
concerns: core/tool_loop.py, core/assistant_turn.py, web/shell.js
from: commit:79608661, file:core/tool_loop.py
---
A tool call the model makes that wasn't offered this turn is not run (assistant_turn and the tool loop). A change asked for after a lookup that returned untrusted() text or list_inbox's mail is said back instead (tool_loop.held_after_outside_text); browser steps are exempt, they have their own gate. A scan of every lookup-named tool's handler found only check_off_grocery_item writes; it is in main_thread.CHANGES_DESPITE_NAME. Talk's ?ask= sends only when MIAShell noted the question from one of MIA's own pages in this tab (sessionStorage), since the server sends no referrer; otherwise it fills the box.
