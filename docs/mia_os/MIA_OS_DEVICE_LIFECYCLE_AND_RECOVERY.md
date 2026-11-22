# MIA OS: device lifecycle and recovery (Prompt 12 §22; DEC-0247)

*Claude (Opus), 2026-11-18. Planning only.*

| Event | What happens | Exists |
|---|---|---|
| A new phone | install the app, sign in, pair with the PC, sync fills it | yes |
| A phone is lost | Sign-ins on the PC (or another trusted device): unlink it; its key stops working at once; its MIA data stays sealed with its key | yes (unlink); sealed |
| The lost phone comes back online | **planned (Q-90):** told it's unlinked, it erases its MIA data | new |
| The PC is replaced | restore from a backup (`backup_manager`), or re-pair the phone and let it sync everything back | partial |
| A node is replaced | flash the image, pair it, it reports its capabilities | planned |
| A device is retired | unlink, then erase it on the device | yes / manual |

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-DST-030 | A device unlinked while away shall erase its MIA data when it next reaches the hub. | Should | R1 | Phone | Exists (WP-10: Lost on Sign-ins) | T | DEC-0247 (Q-90) → 12, 13 |
| REQ-DST-031 | A replaced hub shall be refilled from a backup or from a full engine's sync, losing nothing either holds. | Must | R1 | PC | Partial | D | DEC-0247 → 12, 14 |
