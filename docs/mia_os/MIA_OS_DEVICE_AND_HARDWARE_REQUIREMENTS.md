# MIA OS: device and hardware requirements (Prompt 04, deliverable 8, with §13 and §14)

*Claude (Opus), 2026-11-15. Planning only. Row format: [SYSTEM_REQUIREMENTS](MIA_OS_SYSTEM_REQUIREMENTS.md) §1.
Hardware and platform choices are Prompt 06's; the multi-device architecture Prompt 12's. This sets what they must
satisfy. Current, feasible-later and speculative are kept apart, as §13 asks.*

## 1. The device family (§13)

One MIA, many devices: each device runs what it can and reaches the PC for the rest (DEC-0022, `core/home_link.py`).
Not one identical OS everywhere: Linux image on the PC, Android on the phone, the glasses' own system, Raspberry Pi
OS on Pis.

| Device | Status | Runs | Shares | Device-specific |
|---|---|---|---|---|
| Desktop PC | current (Windows; Linux image planned) | the full runtime, the big models, the lab | the home of every store | the MIA session, KDE, the GPU |
| Laptop | not owned | as the PC, smaller models | same | battery-aware homeostasis |
| Android phone | current | the engine in the app (Chaquopy), a 1.5B to 3B local model | sync with the PC; uses the PC's model when reachable | camera, location, notifications, lock-screen ambient |
| Tablet | not owned | as the phone | same | — |
| Meta Display glasses | current | cards and voice, through the phone and a sealed relay | the phone's session | glance cards, the camera for Look |
| Wearables (watch) | not owned | — | — | later |
| Smart display | not owned | a browser on MIA's web front end, household items only | the PC's runtime | shared-screen rules (MU-10) |
| Raspberry Pi | homestead node current; MIA Runtime on a Pi planned (DEC-0015: later) | MIA Core headless; the homestead control loop | snapshots to the PC | GPIO, sensors, the AI HAT+ 2 |
| Embedded controllers | current in the homestead (safety MCU) | their own firmware; never MIA | readings; settings MIA adjusts through the node | they enforce the hard limits on anything MIA asks (DEC-0185) |
| His truck | wanted (Zac, 2026-11-15) | the phone, or a Pi with a screen and OBD-II | trips, fuel, engine codes | — |
| Dedicated MIA hardware | speculative | — | — | kept out of requirements |

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-DEV-001 | The same person shall be the same MIA on every device: one identity, one set of records (synced), one memory, one personality. | Must | MVP | All | Exists (sync, profiles) | T: `tests/test_sync.py` | P11 → 12 |
| REQ-DEV-002 | A device shall join only after the person pairs it on a device already trusted, and can be removed from either side. | Must | MVP | All | Partial (phone pairing; removal from the PC New) | T | P8 → 12, 13 |
| REQ-DEV-003 | Devices shall talk over an encrypted, authenticated channel: the home network or the person's own Tailscale; never a third party's relay that can read content. | Must | MVP | All | Partial (the glasses relay is sealed end to end; the link uses Tailscale) | I | P7 → 12, 13 |
| REQ-DEV-004 | A change made offline on one device shall reach the others at the next sync, and a concurrent edit is merged or flagged, never lost silently. | Must | MVP | All | Exists (FR-Y1, `core/sync.py`) | T | FR-Y1 → 12 |
| REQ-DEV-005 | Each device shall report its capabilities (screen, voice, camera, model size) and MIA shall offer only what that device can do, saying where the rest is. | Must | MVP | All | Partial (parity per device; capability report New) | T | DEC-0125 → 12 |
| REQ-DEV-006 | A task started on one device shall be continuable on another (handoff): a conversation, a waiting skill run, an open plan. | Should | R1 | All | Partial (conversations sync; skill runs persist) | D: S-15 | P4 → 12 |
| REQ-DEV-007 | The phone shall keep its own answers and records usable with no connection to the PC. | Must | MVP | Ph | Exists | M: S-12 | DEC-0022 → 12 |
| REQ-DEV-008 | Each device's health (battery, last seen, storage, model) shall be visible from the PC. | Should | R1 | All | Partial (the phone's link state) | D | P9 → 12, 14 |
| REQ-DEV-009 | The glasses shall show cards and take voice with every action reachable through the phone, and never hold data of their own beyond a session. | Must | MVP | Gl | Exists (glasses cards, relay) | T | DEC-0125 → 12 |

## 2. Hardware profiles (§14)

Set from the workloads and the measurements in [NON-FUNCTIONAL](MIA_OS_NON_FUNCTIONAL_REQUIREMENTS.md) (PER), not from
marketing. The reference machine is Zac's PC. Model sizes assume 4-bit quantisation (Q4_K_M), as in Ollama's library.

| Workload | Minimum | Recommended | High (the reference PC) |
|---|---|---|---|
| Base OS plus MIA's session and runtime, no local model | 4-core x86-64, 8 GB RAM, 64 GB SSD | 8 GB, 256 GB SSD | — |
| Everyday local model (3B) | +4 GB RAM (runs on CPU, slowly) | a GPU with 6 GB VRAM | Measured: 0.3 s an answer, 220 tokens a second |
| Strong local model (14B) | a GPU with 12 GB VRAM | 16 GB VRAM | Measured: 0.9 s, 73 tokens a second |
| Heavy local model (30B class) | 24 GB VRAM | 24 GB VRAM | Measured: 3.4 s, 14 tokens a second (check on Linux) |
| Vision (qwen2.5vl 7B) and embeddings | 8 GB VRAM | 12 GB | present |
| Development (the lab, tests, image builds) | 16 GB RAM, 8 cores | 32 GB, 8 cores | Ryzen 7 9800X3D, 32 GB |
| Storage | 128 GB | 1 TB NVMe (models are 2 to 19 GB each; backups) | 1 TB NVMe (Crucial P3) |
| Pi endpoint (Core) | Raspberry Pi 5, 8 GB | plus the AI HAT+ 2 | `docs/HARDWARE.md` |
| Phone | Android with 8 GB RAM | 12 GB | `docs/PHONE_MODEL_TEST.md` |

**Graphics compute on the reference PC:** AMD's ROCm lists the Radeon RX 7900 XTX (RDNA 3, gfx1100) as supported on
Linux (the Ubuntu releases in its compatibility matrix); Fedora support is through the distribution's own ROCm
packages and needs checking in Prompt 06 (DEC-0157 proposes Fedora). This is the one hardware question that could
change the image's base.

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-HW-001 | MIA OS shall run its full MVP on the reference PC with the everyday and strong models on the GPU. | Must | MVP | PC | New (on Linux) | M: the PER table rerun on the image | §14 → 06 |
| REQ-HW-002 | The chosen Linux base shall have working GPU compute for the RX 7900 XTX with the model runner MIA uses, proven before the switch. | Must | MVP | PC | New | M: a 14B model on the GPU at no less than the Windows speed | §14 → 06 |
| REQ-HW-003 | MIA shall choose model sizes from the device's measured memory and VRAM, never offering a model the device can't load. | Must | R1 | All | Partial (the phone picks by its memory) | T | P17 → 07 |
| REQ-HW-004 | On hardware below a capability's needs, MIA shall say what's missing and offer the nearest working alternative (a smaller model, the PC's model, a screen instead of voice). | Must | MVP | All | Partial | T | P17 → 07, 12 |
| REQ-HW-005 | MIA OS shall install and run (without local models) on the minimum profile above. *(provisional)* | Could | Mature | PC | New | M: a VM with that profile | §14 → 06 |
| REQ-HW-006 | Microphone, speakers, camera and webcam shall work through the OS's standard stacks (PipeWire, V4L2), with MIA using them only through capabilities. | Must | R1 | PC | Planned | D | P8 → 05 |

## Sources

- ROCm system requirements (Linux), supported GPUs: https://rocm.docs.amd.com/projects/install-on-linux/en/latest/reference/system-requirements.html
- ROCm compatibility matrix: https://rocm.docs.amd.com/en/latest/release/gpu_os_support.html
- Raspberry Pi and the AI HAT+ 2, phone measurements: `docs/HARDWARE.md`, `docs/PHONE_MODEL_TEST.md`
