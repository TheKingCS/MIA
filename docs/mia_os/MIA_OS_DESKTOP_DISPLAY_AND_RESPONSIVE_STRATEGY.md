# MIA OS: displays and responsive behaviour (Prompt 10 §18)

*Claude (Opus), 2026-11-17. Planning only. His PC: a 4K 240 Hz monitor at 150 % and a 1080p one (DEC-0201).*

| Width (logical px) | Layout |
|---|---|
| < 720 | phone layout: bottom bar, Talk full screen (as the phone today) |
| 720–1279 | sidebar as icons; Talk over the main area |
| 1280–1599 | full sidebar; one column |
| 1600–2559 | two columns on Home and dashboards (built) |
| ≥ 2560 | Talk may dock beside; three columns |

**Minimum:** 1280×720 for the full desktop. **Multi-monitor:** the shell on the primary; the second holds the
ambient view (Q-80, approved) or ordinary windows. **Monitors come and go** (Zac, Q-80: "if I turn one off she
flows with just 1"): the shell listens for KWin's output changes; with one screen the ambient view becomes the
ambient state of the main shell (her Home's top card while he works, full screen when idle), and KWin moves any
windows from the lost screen; when the monitor returns, the ambient view goes back to it. Nothing is kept per
screen that a missing screen could lose. **High DPI:** Wayland fractional scaling; the web shell follows it.
**Cost:** the shell is one WebEngine window: about 300–500 MB and near zero GPU when idle; animations stop when
hidden; nothing renders continuously except the 3D room when open (`web/nexus3d.js`). A test measures the shell's
idle memory before release.

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-DSK-027 | The shell idle shall use under 600 MB of memory and no continuous GPU work. | Should | R1 | PC | New | T: measured | DEC-0227, DEC-0204 → 10 |
| REQ-DSK-033 | When a monitor is turned off or unplugged, MIA shall carry on on the screens that remain: the ambient view folds into the main screen's Home and returns when the monitor does, with nothing lost and no setting to change. | Must | MVP | PC | Partial (built on Windows 2026-11-17: gui/ambient_screens.py) | T: monitors added and removed while running | DEC-0231 (Q-80) → 10, 11 |
