---
id: K-0317
kind: implementation
title: The lockdown: a phrase in code, lifted only by his password
status: confirmed
by: claude
created: 2026-11-21T04:25:01+00:00
concerns: core/lockdown.py, core/stop.py, server/app.py
from: commit:ad6661f5, dec:DEC-0254
---
WP-01 (DEC-0254). core/lockdown.py: recognise() takes the whole message ('lockdown', 'lock everything down'...). engage() ends his sessions on the in-process server (phone_server._app.state.sessions, last_seen, session_started), unlinks his phones (linked_devices.unlink_all), locks passwords/private_journal/inbox_mail, puts stop_everything on with no end, and logs it. lift() needs profiles.verify_password; /api/login calls it, so signing in lifts it; stop.carry_on refuses while active. No model tool on purpose: a misheard call would sign his phone out. The server's own button also ends its app.state sessions directly.
