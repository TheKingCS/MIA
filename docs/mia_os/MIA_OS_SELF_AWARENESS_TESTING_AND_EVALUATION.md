# MIA OS: testing and independent evaluation (Prompt 09 §18)

*Claude (Opus), 2026-11-17. Planning only.*

| What's checked | How | Independent of her | Exists |
|---|---|---|---|
| Her code | the full suite (about 6,700 tests), Linux CI | yes: tests are protected for the lab | yes |
| Her documentation | atlas, staleness, freshness tests | yes | yes |
| Her registry's honesty | a test that no capability is called working without a passing test or recent success | yes | new |
| Her self-statements | tests of `self_knowledge` answers against fixtures (planned stays planned) | yes | partial |
| Her models | the bench and Claude's inspection | yes (another model, another family) | yes |
| Her changes | Claude's inspection; Opus/Fable cross-review of development work (DEC-0174) | yes | yes |
| Her trustworthiness per area | the dev ledger | yes | yes |

**Rule:** what judges her is never something she can change (the protected list includes the judges).

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-SLF-020 | A test shall fail if the registry calls a capability working with no passing test or recent success behind it. | Must | R1 | All | New | T | DEC-0220 → 09 |
