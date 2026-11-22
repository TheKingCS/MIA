# MIA OS: the launcher and discovering what she can do (Prompt 10 §6)

*Claude (Opus), 2026-11-17. Planning only.*

## 1. One directory, several views

| View | From | Exists |
|---|---|---|
| By area (cards) | the 19 areas and their dashboards | yes |
| All, A to Z, searchable | the Application Registry (57 manifests) | yes (`apps.html`, Modules) |
| Favourites and recent | per person | partial (focus apps) |
| Compact (the search box) | Ctrl+K | yes |
| What can she do? | the capability registry (Prompt 09), by area, planned said as planned | yes (capabilities) |

## 2. Kinds, kept distinct

| Kind | Example | Source | Opens |
|---|---|---|---|
| MIA app | Garage | `apps/*/manifest.json` | its web screen |
| Capability | "read a photo" | the capability registry | its app, or Talk |
| Agent / specialist | the construction specialist | `core/specialists.py` | its page or Talk |
| Background service | Night School | manifests' `runtime.background` | its status in Diagnostics |
| Linux app | Krita | the `.desktop` files (XDG, Flatpak exports) | a window, via the portal |
| Integration | email account | the service map | its settings |
| Setting | display scaling | MIA settings, or KDE's System Settings modules (`kcmshell`) | the setting itself |

**Linux apps** are listed from the system's own desktop entries, never added to MIA's registry, and launched through
`xdg-desktop-portal` / the launcher's own mechanism (REQ-ARC-013).

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-DSK-007 | The launcher shall list conventional Linux applications from the system's desktop entries, marked as such, without adding them to MIA's registry. | Must | MVP | PC | Exists (FW-11: `core/linux_apps.py`, the Apps page's Linux Apps; a VM check to come) | T | DEC-0233, REQ-ARC-013 → 10 |
| REQ-DSK-008 | The launcher shall say which kind each entry is (app, capability, agent, service, Linux app, integration, setting). | Should | R1 | PC | Partial | T | DEC-0228 → 10 |
