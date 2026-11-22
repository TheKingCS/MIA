# MIA OS: settings and administration (Prompt 10 §14)

*Claude (Opus), 2026-11-17. Planning only.*

| Kind | Examples | Lives in | Reached from MIA |
|---|---|---|---|
| MIA preferences | appearance, voice, autonomy, her messages, models, memory | MIA's Settings (`settings.html`, `core/person_settings.py`) | directly |
| App settings | an app's own options | the app | from the app |
| Linux system settings | display, network, sound, users, updates, printers | KDE System Settings | opens the right module (`systemsettings <module>`) |
| Security policy | grants, the protected list, sign-in | MIA's Settings (grants), Prompt 13 | directly |
| Administration | packages, services, firmware | the OS, through the fixed-operation helper (DEC-0194) | as an action confirmed in the OS's own dialog |

**Nothing is hidden**: every Linux setting she shows a link to is KDE's own page, not a copy. Changes to the system
are actions confirmed in the OS's polkit dialog, never by her alone (DEC-0194, DEC-0215: system changes are never
grantable).

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-DSK-023 | MIA's Settings shall open the matching KDE System Settings page for each system setting, never a copy of it. | Must | MVP | PC | Exists (FW-11: thirteen pages, from Settings and by voice; a VM check to come) | T | DEC-0227, REQ-FUN-003 → 10 |
