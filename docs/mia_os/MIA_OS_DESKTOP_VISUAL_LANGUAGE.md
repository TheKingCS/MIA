# MIA OS: the desktop's visual language (Prompt 11 §12)

*Claude (Opus), 2026-11-17. Planning only. Structure: Prompt 10.*

| Element | Surface tier | Accent use | Notes |
|---|---|---|---|
| Sidebar | primary | the current area | icons with labels; collapses to icons |
| Dashboard cards | secondary | the app's atmosphere stripe | status word + time of data |
| Launcher | primary | — | category cards; A–Z list |
| Search | floating | the selected result | type of each result as a mark |
| Talk | floating | her replies' edge, the orb | chips for shared context |
| Window strip | primary | the active window | Linux apps' own icons |
| Status strip | none (on the field) | her presence | small, mono labels |
| Notifications | floating | by kind (meaning colours) | source shown |
| Approval card | floating, above all | primary action | always recognisable |
| Settings | primary | — | KDE's pages for system settings open in KDE's look |
| Missions | secondary | rewards in legendary orange | Real/Simulated/Game marks |
| Ambient | deep, large type | the orb | the clock in display size |

**Consistent, not identical:** every screen uses the same frame, tiers and tokens; each app keeps its atmosphere
colour and its own layout of data.

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-VIS-017 | The shell's regions shall each use their assigned surface tier, so the approval card always sits above everything. | Should | R1 | PC | Partial | T | DEC-0234 → 11 |
