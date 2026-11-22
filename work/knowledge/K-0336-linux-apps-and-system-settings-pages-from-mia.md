---
id: K-0336
kind: implementation
title: Linux apps and System Settings pages, from MIA
status: confirmed
by: claude
created: 2026-11-22T15:16:10+00:00
concerns: core/linux_apps.py, core/assistant_desktop_actions.py, server/app.py
from: task:FW-11
---
FW-11 part (REQ-DSK-007/023, REQ-FUN-003, REQ-ARC-013, DEC-0233). core/linux_apps.entries() reads *.desktop from XDG_DATA_HOME, XDG_DATA_DIRS and Flatpak's exports (earlier folders hide later ids), leaving out non-Application, NoDisplay, Hidden, OnlyShowIn without KDE and NotShowIn KDE; [] off Linux; never in the app registry. launch() opens only a listed id with ['gio', 'launch', path]. SYSTEM_SETTINGS maps 13 words to KDE modules (kcm_kscreen...); open_setting starts ['systemsettings', kcm] detached with Popen (a run() with a timeout would kill the window). /api/desktop lists both; /api/desktop/open opens only when _on_this_pc (a phone can't open windows on the PC). Tools open_system_setting and open_linux_app on Settings, act_within_grant. Settings has This Computer's Settings; Apps lists Linux Apps after MIA's.
