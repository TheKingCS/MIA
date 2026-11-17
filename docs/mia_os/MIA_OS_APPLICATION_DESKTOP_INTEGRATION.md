# MIA OS: apps on the desktop (Prompt 10 §21; DEC-0233)

*Claude (Opus), 2026-11-17. Planning only. The framework is Prompt 03's (`MIA_OS_APPLICATION_FRAMEWORK.md`).*

| Concern | MIA app | Linux app |
|---|---|---|
| Defined by | its manifest (`apps/<id>/manifest.json`) | its desktop entry |
| UI | a web page on the shared frame | its own toolkit (Qt, GTK) |
| Launch | a link in the shell; deep link `/web/<page>?...` | the launcher, by desktop entry |
| Windows | inside the shell; a second window when popped out | its own |
| Notifications | the gate / her notifications | freedesktop |
| Search | a search provider | Baloo, its desktop entry |
| Context | its records, through capabilities | shared by him (portals) |
| Files | `myfile.*` actions | the file chooser portal, file associations (`mimeapps.list`) |
| Permissions | tiers in its manifest | Flatpak permissions |
| Lifecycle | the runtime | the system |

**Frameworks compared** (the technology evaluation): MIA's apps stay on the web frame (one renderer, 109 screens
working, the phone shows the same pages); her host window is Qt WebEngine (KDE's own engine, AT-SPI); Linux apps are
left in their own toolkits. No app is rewritten into another framework without evidence it would be better.

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-DSK-030 | A MIA screen shall open in its own window on request, keeping the shared frame and the one change path. | Could | R1 | PC | New | T | DEC-0233 → 10 |
