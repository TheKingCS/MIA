# MIA OS: reliability objectives (Prompt 14; DEC-0261)

*Claude (Opus), 2026-11-18. Planning only. Measured where possible; provisional until measured on his PC.*

| Objective | Target |
|---|---|
| Records lost to a crash or power cut | none (atomic writes) |
| Records lost if the PC is destroyed | at most one day (nightly backup off the PC); none if the phone synced since |
| Power on to login | under 30 s (REQ-PER-001) |
| Login to Home | under 10 s (REQ-REL-016) |
| The conventional desktop with MIA failed | under 10 s (REQ-PER-002) |
| A runtime crash to back | under 10 s (systemd) |
| A failed update to the previous one | one restart |
| A new PC to his MIA | about 2 hours |
| Answers in words available | when the PC is on; self-repair within 5 minutes of Ollama stopping |

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-REL-035 | Each reliability objective shall be measured on his PC before MIA OS is called ready, and shown in Diagnostics. | Should | R1 | PC | New | M | DEC-0261 → 14 |
