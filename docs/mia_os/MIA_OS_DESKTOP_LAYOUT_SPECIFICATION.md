# MIA OS: the desktop layout (Prompt 10 §4)

*Claude (Opus), 2026-11-17. Planning only. The look is Prompt 11's.*

## 1. The regions

| Region | Holds | Visible | Exists |
|---|---|---|---|
| **Sidebar** (left) | Home, the areas, Search, Missions, Talk, Notifications, Settings; level and XP | always in Workspace; collapses to icons below 1280 px wide or by choice (`layout.sidebar`) | yes |
| **Main area** | the open screen: Home, an area's dashboard, an app | always | yes |
| **Talk** | her panel, sliding over the right side; full screen when asked | on demand (the orb, a key, a word) | yes (panel) |
| **Status strip** (top right) | time, weather, connectivity, sound, power, her presence, background work, unread count | always; compact | partial (presence, unread) |
| **Window strip** (bottom) | the ordinary Linux windows open in this workspace, the workspace switcher | when any are open (Q-79) | new |

## 2. Rules

- Nothing needs to be visible all the time except the way back (the sidebar's icon rail or a key).
- The main area never shrinks below 720 px; at less, Talk covers it rather than squeezing it.
- At 1600 px and wider, Home and dashboards use two columns (built 2026-11-17, `home-main`); at ultrawide (≥ 2560
  logical px) a third column or Talk docked beside.
- Linux windows are KWin's: they tile, snap and float as KWin does, beside or over MIA's shell window.

```
+-----------+--------------------------------------------------+-----------------+
| MIA       |  Garage                                 9:41 ☀ 🔊 ● 3 |
| Home      |  +-------------+  +-------------+  +-------------+ |  Talk (open)    |
| Garage    |  | Vehicles    |  | Maintenance |  | Projects    | |  chips: Garage  |
| Finances  |  +-------------+  +-------------+  +-------------+ |  ...            |
| ...       |                                                    |                 |
| Search ⌘K |                                                    |                 |
+-----------+--------------------------------------------------+-----------------+
| [Firefox: parts] [Konsole: ~/garage] [Krita]            workspace: Garage ▾  |
+--------------------------------------------------------------------------------+
```

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-DSK-003 | The shell's layout shall work from 1280×720 to ultrawide without horizontal scrolling, collapsing the sidebar and moving Talk over the main area below 1280 px. | Must | MVP | PC | Partial (two columns at 1600 px) | T: screenshots at set sizes | DEC-0228 → 10, 11 |
| REQ-DSK-004 | The status strip shall show time, connectivity, sound, power, her presence, background work and unread messages, each saying when it can't be read. | Should | R1 | PC | Partial | T | DEC-0228 → 10 |
