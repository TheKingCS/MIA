# MIA OS: security across devices (Prompt 12 §21)

*Claude (Opus), 2026-11-18. Planning only. Prompt 13 designs it in full.*

| Boundary | Rule | Exists |
|---|---|---|
| Who may connect | paired devices only, each with its own key | yes |
| What a key may do | its scope (person, household, sensor, node) | partial |
| Data at rest on each device | sealed (DEC-0126) with that device's key | yes (PC, phone) |
| Data in transit | inside Tailscale (WireGuard) away; the home network at home, HTTPS planned there too | partial |
| A person's records | only their own devices; a household's only its members' and the household display | yes (stores split) |
| A device that's lost | unlinked from anywhere; its sealed data unreadable without its key | yes / partial |
| A controller | MIA can't override its safety | yes |
| A sensor | one series, rate-limited, can't read | yes |

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-DST-028 | Traffic between his devices on the home network shall be encrypted, as it is through Tailscale away. | Should | R1 | All | New | T | DEC-0244 → 12, 13 |
| REQ-DST-029 | A key shall be refused for anything outside its scope. | Must | MVP | All | Exists (WP-10: household keys; sensors') | T | DEC-0242 → 12, 13 |
