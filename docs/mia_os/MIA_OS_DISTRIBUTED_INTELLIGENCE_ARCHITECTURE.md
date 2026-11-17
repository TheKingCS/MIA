# MIA OS: distributed intelligence (Prompt 12 §8; DEC-0245)

*Claude (Opus), 2026-11-18. Planning only. Routing in one engine: DEC-0208; providers: DEC-0207.*

| Order | Where | When | Exists |
|---|---|---|---|
| 1 | the hub's GPU (qwen2.5:14b everyday; the specialists' 32B and 24B) | reachable | yes (level 2) |
| 2 | a model node (DEC-0202), when one exists | reachable, and the task's model lives there | planned |
| 3 | the device's own model (the phone's small one; the Pi's HAT) | always | yes |
| 4 | a cloud model | only on his yes for that request, never with his records unless he says so | DEC-0207 |

**Code before models everywhere:** question plans, lookups and calculators run on whichever engine he's using, with
no model at all (REQ-INT-036). **Speech** stays on the device that heard it (Vosk on the PC, the phone's own; the
glasses through the phone). **Heavy jobs** (Night School, benchmarks, recall embedding) run on the hub only.
**Said each time:** which machine answered (`level`, already shown).

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-DST-009 | A turn shall use the most capable reachable machine, fall back to the device's own model mid-conversation, and say which answered. | Must | MVP | All | Exists (DEC-0022) | T | DEC-0245 → 12, 07 |
| REQ-DST-010 | Speech shall be recognised on the device that heard it. | Must | MVP | All | Exists | T | DEC-0211, DEC-0245 → 12 |
