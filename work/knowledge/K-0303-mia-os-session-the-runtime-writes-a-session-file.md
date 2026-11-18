---
id: K-0303
kind: implementation
title: MIA OS session: the runtime writes a session file, the shell reads it
status: confirmed
by: claude
created: 2026-11-18T14:22:32+00:00
concerns: core/runtime.py, os/files/mia-runtime.service, .github/workflows/mia-os-vm.yml
from: task:FW-03, dec:DEC-0278, file:core/desktop_session.py, file:gui/os_shell.py
---
FW-03 (2026-11-18). On MIA OS the runtime is a systemd user service and the shell a separate window, so the in-process token the Windows app uses (phone_server.local_session in modules/web_home) is handed over through a file: core/desktop_session.write puts the local URL and a token in $XDG_RUNTIME_DIR/mia/desktop.json (the unit sets MIA_DESKTOP_SESSION_FILE=%t/mia/desktop.json), owner-only, replaced whole, removed on stop. gui/os_shell.py polls it once a second (never blocking Qt), opens /web/#token=..., or shows a recovery page after 30 s whose links use the mia-shell: scheme, handled in acceptNavigationRequest. Screenshots of a QWebEngineView via grab() come out blank with GPU drawing; use QTWEBENGINE_CHROMIUM_FLAGS=--disable-gpu for tests. KWin starts the session program without arguments, so test arguments go through MIA_SHELL_ARGS.
