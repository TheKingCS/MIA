# MIA OS: capability evolution and discovery (Prompt 09 §16; DEC-0226)

*Claude (Opus), 2026-11-17. Planning only.*

| Path | From | To | Exists |
|---|---|---|---|
| A request no tool could do | `core/capability_gaps.py` (from the Fix-It Log) | a proposal: a taught skill, a workflow, or a lab build | yes |
| A selection she couldn't act on | the UAL's "Build A Skill For MIA" | a taught skill or a lab proposal | yes |
| A specialist that's missing | the Forge (DEC-0199) | a specialist built in the lab, benched, inspected | partial (F1, F6) |
| An app that's missing | Forge's scaffold (M7) | a registered app, then built in the lab | partial |
| A model that could do better | the forge (DEC-0106) | a model of her own, benched, inspected | partial |

**Every new capability arrives with:** its tier in a manifest, its tests, its parity decision, its loop or a reason,
documentation, and a registry record. Tests already fail on a tool or kind without a tier, a gap without a decision,
or a process without a loop.

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-SLF-018 | A new capability shall reach the running MIA only with its tier, tests, parity decision, loop or reason, documentation and registry record. | Must | MVP | All | Exists (the tests) | T | DEC-0226 → 09 |
