# MIA OS: seeing every device's health (Prompt 12 §20)

*Claude (Opus), 2026-11-18. Planning only. One machine: Prompt 09 (DEC-0222).*

| Seen on the hub | From | Exists |
|---|---|---|
| Each device: last seen, version, reachable | device records, `phone_link` | partial |
| Last sync and its result | sync's own record | partial |
| The node's state and its freshness | `greenhouse_link` | yes |
| A sensor's last reading and whether it's late | `core/sensors.py` | partial |
| The phone's model and battery | the device's report | new |

**Diagnostics gains a Devices panel**: each device, its kind, last seen, version, sync, and anything wrong ("the
greenhouse hasn't sent anything for 2 hours"). The Fix-It Log merges each device's entries (already line-merged), so a
failure on the phone is seen on the PC.

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-DST-027 | Diagnostics shall show each paired device with its kind, version, last contact, last sync and anything late or failing. | Should | R1 | PC | Partial | T | DEC-0222, DEC-0242 → 12 |
