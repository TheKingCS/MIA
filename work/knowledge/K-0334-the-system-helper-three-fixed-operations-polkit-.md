---
id: K-0334
kind: implementation
title: The system helper: three fixed operations, polkit, on demand
status: confirmed
by: claude
created: 2026-11-22T15:12:12+00:00
concerns: os/files/mia-system-helper, core/system_helper.py, os/Containerfile, os/files/mia-session
from: task:FW-06, dec:DEC-0194
---
FW-06 (DEC-0194, REQ-ARC-010/AGT-024/SEC-022). os/files/mia-system-helper is org.mia.System1 on the system bus (system python3 with GLib's Gio): ApplyUpdate (only with an update staged per bootc status --json), RestartUnit (ollama.service or mia-update-stage.service), Power (poweroff or reboot). check() refuses any other method or argument before polkit; then polkit CheckAuthorization for the caller's bus name with AllowUserInteraction, actions org.mia.system1.* at auth_self (never kept), no for inactive or any. D-Bus activation (org.mia.System1.service -> mia-system-helper.service, Type=dbus, never enabled) and a 60 s idle exit keep root off between calls. MIA's side, core/system_helper.py, runs gdbus with fixed argv (never a shell) after the same checks; the kinds system.restart_service, system.power, system.apply_update are act_with_approval on Settings and reach the system. mia-session now starts KDE's polkit agent as a KWin client, or the dialog could never show in her session. The VM step tests refusals, a call over SSH refused (no one at the desk), and success through a test-only polkit rule.
