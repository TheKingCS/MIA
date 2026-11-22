# MIA OS: device identity and registration (Prompt 12 §6; DEC-0242)

*Claude (Opus), 2026-11-18. Planning only. Identity in full: Prompt 13.*

## 1. The lifecycle

| Step | How (today for phones; the same for every device) |
|---|---|
| Discovered | he opens MIA on the new device and names the PC (its address on the home network or Tailscale) |
| Pairing | the device asks the PC with his own name and password (`/api/model/link`), never making an account |
| His authorisation | his password is the yes; a household display is paired by him as the household's (Q-82) |
| Identity | the PC gives a device key, keeps only its hash, with whose it is, the device's name and kind, when |
| Capabilities | the device reports what it has (§ capability registry) |
| Operational | its requests are signed with the key; `phone_link.seen` notes the last contact |
| Trust re-checked | a key unused for 90 days is shown as stale; a password change or "sign out everywhere" unlinks all |
| Retired | unlinked from Sign-ins on any trusted device; the key's hash is deleted |

## 2. Kinds of key

| Key | Can | Exists |
|---|---|---|
| A person's device key | everything that person can do | yes (phones) |
| A household device key | household stores only (the household display) | built (WP-10: `/api/live` until the display's view, WP-20) |
| A sensor key | log one number to one series | yes |
| A node key | post its snapshots; read what it's told to show | partial (exports pulled today) |

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-DST-005 | Every device shall be paired by the person, hold its own key whose hash alone the hub keeps, and be listed in Sign-ins with its kind and last contact. | Must | MVP | All | Exists (WP-10: each device's record, stale after 90 days) | T | DEC-0242 → 12, 13 |
| REQ-DST-006 | A key shall be scoped to its kind: a person's, a household's, a sensor's one series, a node's snapshots. | Must | R1 | All | Partial (person, household, sensor: WP-10; node to come) | T | DEC-0242 → 12, 13 |
