---
id: K-0125
kind: implementation
title: Don't bring that up: a quiet list for connections
status: confirmed
by: claude
created: 2026-11-08T16:02:34+00:00
concerns: core/connections.py, core/web_connections.py, core/assistant_connection_actions.py, web/connections.js
from: dec:DEC-0146
---
DEC-0146 left saying 'don't bring that up' for later. ConnectionBook gained a quiet list (refs, saved beside the connections) that _recent checks first, so a declined thing is never kept again even after the 30-day cooldown; decline() settles the connection as 'declined' (its own state, so the landed loop's mentioned/expired share isn't skewed) and allow() removes the ref. 'That' in the voice tool means the newest connection she brought up, else the newest waiting (web_connections.latest), since the phrase comes right after she raised it.
