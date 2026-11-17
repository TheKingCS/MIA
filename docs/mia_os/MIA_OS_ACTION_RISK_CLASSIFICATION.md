# MIA OS: action risk classification (Prompt 08 §12; DEC-0216)

*Claude (Opus), 2026-11-17. Planning only.*

## 1. Risk from facts, in code

| Factor | Values | Source |
|---|---|---|
| Reach | records, device, system, outside | `action_effects` (exists) |
| Reversibility | undoable, compensable, irreversible | `action_effects` (exists) |
| Money | none, records only, moves money | new field on the kind |
| Other people | none, someone sees it, someone acts on it | new field |
| Physical | none, a device's settings, something that moves or heats | new field |

**Least tier** = the strictest any factor demands:

| Any of | Least tier |
|---|---|
| moves money, sends to someone, irreversible outside | act_with_approval, never grantable |
| system reach | act_with_approval (and the OS's own dialog, DEC-0194) |
| physical, something that moves or heats | act_with_approval, inside the device's own hard limits (REQ-HW-017) |
| device settings within limits | act_within_grant |
| records, undoable | act_within_grant |
| reads only | observe |

**Unknown is highest:** a kind with no declared factors is treated as `act_with_approval` until declared. A test sweeps
every kind's tier against its factors (extends test_action_effects).

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-AGT-017 | Each action kind's least tier shall be computed in code from its reach, reversibility, money, people and physical effect, and a test shall fail on a kind tiered below it. | Must | R1 | All | Partial (reach and reversibility) | T | DEC-0216 → 08 |
