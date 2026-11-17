# MIA OS: safe mode and the fallbacks (Prompt 14; DEC-0260)

*Claude (Opus), 2026-11-18. Planning only.*

| Fallback | For | How he gets there |
|---|---|---|
| **Plasma** | MIA's session misbehaving | the login screen's session menu |
| **MIA safe mode** (REQ-REL-008) | MIA herself misbehaving | a login entry "MIA (safe mode)": the runtime with no jobs, no models, no grants used, the default theme, Diagnostics open |
| **The previous deployment** | an update gone wrong | the boot menu (and automatic after a failed boot) |
| **A recovery USB** | the disk or the boot itself | Fedora's live image; the recovery key restores his data |
| **Windows today** | — | the classic Qt view (Ctrl+Shift+C); Windows itself |

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-REL-022 | Safe mode shall start with no jobs, models, grants or custom theme, open Diagnostics, and change nothing on its own. | Should | R1 | PC | New | D | DEC-0260, REQ-REL-008 → 14 |
