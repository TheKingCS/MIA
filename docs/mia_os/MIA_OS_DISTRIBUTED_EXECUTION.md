# MIA OS: distributed execution (Prompt 08 §17)

*Claude (Opus), 2026-11-17. Planning only. Prompt 12 designs the distributed system; this sets execution's rules.*

| Rule | Why | Exists |
|---|---|---|
| **The PC's runtime is the one writer** of his records; other devices propose and sync | no split brain (DEC-0190) | yes |
| An approval runs as the person who approved it, wherever it was pressed | XP and rights follow him (`crediting`) | yes |
| A step that needs a device (the phone's camera, the homestead node) is sent to that device as a request and waits for its report | the device owns its hardware | partial |
| A device offline: its steps wait, others continue; the plan says which | REQ-HW-022 | partial |
| The model node runs inference only, never actions | DEC-0202 | proposed |
| A phone approval of a card the PC made shows the same card and executes on the PC | one contract | yes |

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-AGT-025 | A step that needs another device shall be a request to that device, and the plan shall wait for its report rather than assume. | Must | R1 | All | Partial | T | DEC-0218 → 08, 12 |
