# MIA OS: application and system automation (Prompt 08 §16)

*Claude (Opus), 2026-11-17. Planning only. The desktop is Prompt 10's; security Prompt 13's.*

| Target | How MIA acts | Exists | Gate |
|---|---|---|---|
| Her own apps | action kinds on the contract | yes | tiers |
| The web | her browser (DEC-0117/0196): every step classified in code; commits only by him; private sites read only when asked | yes | `browser_safety` |
| His conventional apps (on MIA OS) | portals and D-Bus where the app offers them; accessibility (AT-SPI) to read; input only in a session he's watching | planned | per app, with approval |
| The system (updates, firewall, services) | the fixed-operation helper; each confirmed in the OS's own dialog with his password (Q-50) | planned (PoC 5) | always his password at first |
| Devices | through their owner (the homestead node; Home Assistant later if used) | partial (greenhouse) | within the device's hard limits |
| Files | her own folders; his only through the portal's file chooser or a folder he shared | partial | records reach, undoable where possible |

**Never:** keystrokes into an app he isn't watching; reading a password field; acting on a screen she can't verify.

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-AGT-023 | Automation of his own desktop apps shall use the app's portals or D-Bus where offered, and input only in a session he's watching. | Must | R1 | PC | New | M | DEC-0213 → 08, 10, 13 |
| REQ-AGT-024 | System changes shall go only through the fixed-operation helper, each confirmed in the OS's own dialog. | Must | MVP | PC | Exists (FW-06, the helper; checked in the VM, run 45036996998: refusals, an approved restart, root only while called) | T | DEC-0194 → 08 |
