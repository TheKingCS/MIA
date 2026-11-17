# MIA OS: resources and power across devices (Prompt 12 §18)

*Claude (Opus), 2026-11-18. Planning only. One machine: homeostasis (DEC-0173), the GPU queue (DEC-0204).*

| Device | Spends | Saves by |
|---|---|---|
| The PC | the GPU for models, the CPU for jobs | the GPU queue (conversation first); heavy jobs at night; easing off when busy |
| The phone | battery, data | its own small model only when the PC can't answer; sync on Wi-Fi by default; listening only when held or tapped |
| The glasses | battery | blank until something happens; the phone does the work |
| The Pi | power, the HAT | readings and small models only |
| Zeta Astralis | battery | dark unless looked at; the phone or Pi does the work |

**Work goes to the device with power to spare:** a phone on battery hands a long job to the PC ("I'll do this at
home") instead of running it; the PC tells the phone when it's done.

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-DST-025 | A long job asked for on a battery device shall run on the hub when it's reachable, and the device shall be told when it's done. | Should | R1 | Phone | New | T | DEC-0245 → 12 |
