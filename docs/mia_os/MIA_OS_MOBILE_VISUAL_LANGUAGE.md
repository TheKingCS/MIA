# MIA OS: the phone (Prompt 11 §13)

*Claude (Opus), 2026-11-17. Planning only. The mobile concept set (DEC-0018) and its layouts stay.*

| Concern | Phone | Exists |
|---|---|---|
| Navigation | bottom bar: Apps, Search, Home, MIA (the concept's four) | yes |
| Layout | one column; cards full width; the area dashboards stacked | yes |
| Talk | full screen from the MIA tab or the orb | yes |
| One-handed | primary actions in the lower half; bottom sheets for menus | partial |
| Gestures | back by edge swipe (Android); pull to refresh re-reads | partial |
| Effects | "auto" = light (no blur) to save power | yes |
| Notifications | Android's, from the phone app | yes |
| Widgets | an Android home-screen widget: the orb and what's due | new |
| Targets | ≥ 48 dp | partial |

**Not a shrunken desktop:** fewer things per screen, larger targets, sheets instead of panels, the same tokens.

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-VIS-018 | On the phone, primary actions shall sit in reach of the thumb and every target shall be at least 48 dp. | Should | R1 | Phone | Partial | T | DEC-0234 → 11, 12 |
