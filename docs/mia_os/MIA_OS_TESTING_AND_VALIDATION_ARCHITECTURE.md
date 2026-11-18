# MIA OS: testing in layers (Prompt 15; DEC-0266)

*Claude (Opus), 2026-11-18. Planning only.*

| Layer | What | Exists |
|---|---|---|
| Unit | pure logic, stores, actions | yes (most of the ~6,800) |
| Contract | every screen's JSON against its example; the Life State schema; manifests against the code | yes |
| Integration | the server's routes with a test client; the turn end to end; sync | yes |
| Documentation | every definition documented; generated docs current; staleness | yes |
| Rules | tiers, parity, loop coverage, appearance (no literal colours), no secrets in logs, no control characters | yes |
| AI quality | the corpus, the benchmark, the engineering bench, inspections | yes (separate runs) |
| Security | boundaries, injection, replay | to add (Prompt 13) |
| OS | the VM boot, units, rollback | partial |
| Failure simulation | killed runtime, power cut, failed update | to add (Prompt 14) |
| On his devices | the scenarios of Prompt 12 | to add |

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-DEV-017 | Every change shall pass the full suite before it's pushed, and every new store, action, tool or screen shall arrive with its tests. | Must | MVP | All | Exists (practice, rule tests) | T | DEC-0266 → 15 |
