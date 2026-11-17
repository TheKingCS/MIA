# MIA OS: monitoring and incident response (Prompt 13 §22)

*Claude (Opus), 2026-11-18. Planning only.*

| Step | How |
|---|---|
| Detection | security-log alerts (new device, repeated wrong passwords), the dependency audit, odd sensor readings, the Fix-It Log, his own "that wasn't me" |
| Classification | account, device, data, dependency, physical |
| Containment | **Lockdown** (Q-93): one phrase or press signs out every device, stops everything, locks the vaults, pauses outreach and her lab |
| Investigation | the security log, the action record, traces |
| Recovery | undo, restore a backup, re-pair devices |
| Credential rotation | his MIA password (ends sessions), the vault's master password, device keys, cloud API keys |
| Validation | the suite, a sign-in from each device |
| Review | a knowledge entry and, where it's a weakness, a fix before it's described publicly |

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-SEC-035 | One phrase or press shall sign out every device, stop everything, lock the vaults and pause her outreach and lab, until he unlocks with his password. | Should | R1 | All | New | T | DEC-0254 (Q-93) → 13 |
