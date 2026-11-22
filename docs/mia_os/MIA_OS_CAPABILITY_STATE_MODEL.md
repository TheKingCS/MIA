# MIA OS: capability states (Prompt 09 §5)

*Claude (Opus), 2026-11-17. Planning only.*

| State | Means | Decided by | Exists |
|---|---|---|---|
| **working** | built, its tests pass, used successfully lately, everything it needs is here | code: tests, trace, services | as "implemented" |
| **partial** | works, but not everywhere or not every part (a device it isn't on yet) | parity, limits | yes |
| **degraded** | works with a fallback now (a smaller model, word search instead of meaning) | the fallback that answered | **new** |
| **unavailable here** | needs something this device doesn't have | hardware and service records | yes |
| **malfunctioning** | broke recently (inferred from the Fix-It Log) | the log | yes |
| **unverified** | built, but no test or use proves it lately | missing evidence | **new** |
| **planned** | decided, not built | parity todo, the plans | yes |
| **retired** | was there, removed | the registry | yes (apps) |

**Transitions are evidence:** a failure moves working → malfunctioning (with its count); a passing test and a success
move it back; a fallback that answered marks degraded for that period; age without evidence moves working → unverified.

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-SLF-005 | Capability states shall include degraded and unverified, and every state change shall cite the evidence that caused it. | Must | R1 | All | Exists | T | DEC-0220 → 09 |
