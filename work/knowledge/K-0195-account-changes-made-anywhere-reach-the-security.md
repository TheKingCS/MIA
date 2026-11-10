---
id: K-0195
kind: implementation
title: Account changes made anywhere reach the security log, without the web's double entry
status: confirmed
by: claude
created: 2026-11-09T07:14:22+00:00
concerns: core/security_log.py, core/application.py, core/core_runtime.py, server/app.py, tests/test_security_log.py, tests/test_server_app.py
from: file:docs/SECURITY.md, file:core/security_log.py
---
docs/SECURITY.md step 3, 2026-11-09, from the self-audit's unheard events. profile.password_changed and profile.email_changed were published and nothing listened, so a password changed at the desktop and any email change never reached the security log. security_log.on_account_change subscribes both (wired in core/application.py and core/core_runtime.py, which are separate paths), records the change as 'this computer', and for an email change alerts the owner at once (a changed sign-in email is how accounts are taken over). The web's password endpoint already logs with the device, and the event fires inside set_password before it does, so a dedup-after check couldn't work; instead the endpoint wraps its call in logged_by_caller() (a thread-local depth) and the listener skips inside it. Tested: the listener's entries and alert, and the web change logged exactly once with its device.
