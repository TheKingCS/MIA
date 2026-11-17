# MIA OS: discovery and the capability registry (Prompt 12 §7)

*Claude (Opus), 2026-11-18. Planning only. The per-machine registry is DEC-0203 (read from Linux's own sources).*

**Discovery:** by name and address he gives, or by Tailscale's device list (`tailscale status --json`, already read
for the phone's address); mDNS on the home network later, offered only, never auto-paired.

**Each device reports** when it pairs and on change: its kind, its runtime and version, its models (name, size,
speed measured), voice in and out, camera, screen (size, kind), battery, storage, sensors, and what it's allowed to do
(its key's scope). Kept on the hub as a **device record**, with `last_seen` and `reachable`.

**Used for:** routing thinking (DEC-0245), choosing where a screen shows, what the capability registry says is
possible ("Look needs a camera: the phone has one, the PC doesn't"), and Sign-ins.

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-DST-007 | Each paired device shall report its kind, version, models, voice, camera, screen, battery and storage, and the hub shall keep it with when it was last seen. | Should | R1 | All | New | T | DEC-0203, DEC-0242 → 12 |
| REQ-DST-008 | A device found on the network shall never be paired without the person. | Must | MVP | All | Exists (pairing needs his password) | T | DEC-0242 → 12, 13 |
