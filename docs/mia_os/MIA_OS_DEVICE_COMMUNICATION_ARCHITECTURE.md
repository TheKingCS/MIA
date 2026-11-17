# MIA OS: how devices talk (Prompt 12 §10; DEC-0244)

*Claude (Opus), 2026-11-18. Planning only. Within one machine: DEC-0192.*

| Between | How | Exists |
|---|---|---|
| A screen and its engine | HTTP (`/api/*`) and server-sent events (`/api/live`) | yes |
| The phone and the PC | HTTPS-capable HTTP over the home network or Tailscale, signed with the device key: `/api/model/chat`, `/api/sync/*` | yes |
| The glasses and the phone | Meta's Device Access Toolkit (Bluetooth) inside the phone app | yes |
| The PC and the greenhouse node | the node's read-only export server, pulled on his network; later the node's own control API for approved actions | partial |
| Sensors to the PC | one HTTP POST per reading, the sensor key | yes |
| Within the OS | D-Bus | planned (MIA OS) |

**Events between devices are "re-read" signals, not data**: a device told something changed fetches it with its own
key (as `/api/live` does on one machine). **No broker** (MQTT is evaluated for controllers only, if a controller
needs it, inside the homestead node). **Every message** is from a paired device, signed, and refused otherwise.

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-DST-012 | Every request between devices shall be signed with a paired device's key and refused otherwise. | Must | MVP | All | Exists | T | DEC-0244 → 12, 13 |
| REQ-DST-013 | A change on one device shall reach another as a signal to re-read, never as pushed data it didn't ask for. | Should | R1 | All | Partial | T | DEC-0244 → 12 |
