# MIA OS: device security (Prompt 13 §13)

> **Prompt 17 (2026-11-18):** a lost device's key is refused at once on the hub; erasing the device happens only when it reconnects, so it's best effort (Codex F-08).

*Claude (Opus), 2026-11-18. Planning only. Devices: Prompt 12 (DEC-0241 to 0247).*

| Control | State |
|---|---|
| Pairing with his password; a key per device, hash only on the hub | built |
| Keys scoped to their kind (person, household, sensor, node) | partial |
| Unlink from any trusted device; Sign Out Everywhere | built |
| A lost device erases its MIA data on reconnecting (Q-90) | approved, to build |
| Each device's data sealed with its own key | built (PC, phone) |
| Away from home only through Tailscale (Q-88) | built |
| His home network's own traffic in TLS | planned (REQ-DST-028) |
| Home devices (cameras, controllers) on their own network segment | recommended |

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-SEC-024 | A compromised home device shall reach nothing of MIA's beyond its own key's scope. | Must | MVP | All | Partial | T | DEC-0242 → 13, 12 |
