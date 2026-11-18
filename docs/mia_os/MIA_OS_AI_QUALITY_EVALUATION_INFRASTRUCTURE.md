# MIA OS: AI quality evaluation (Prompt 15)

*Claude (Opus), 2026-11-18. Planning only. The framework: Prompt 07.*

| Set | Measures | Run | Exists |
|---|---|---|---|
| Intelligence Benchmark (112 questions, his records) | routes, flags, time | weekly (Night School), on a model change (`--model`) | yes |
| Golden conversation corpus (49 cases) | tone, honesty, safety, kind of message | weekly | yes |
| Engineering bench (57 problems) | specialists choosing calculators, asking for missing values | on a model change | yes |
| Claude's inspection | a specialist's model before use | nightly, one | yes |
| Routing audit | the right plan or tool | weekly | yes |
| Message kinds | `core/message_kind` against labels | with the suite | yes |

**Model changes are gated:** a new everyday or specialist model replaces the old only after its sets are no worse
(DEC-0208) and, for specialists, Claude's pass (DEC-0200). Measured 2026-11-18: qwen2.5:14b stays (Q-68).

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-DEV-018 | No model shall replace another for a role until its evaluation sets are no worse, measured on this PC. | Must | MVP | PC | Exists (practice; specialists by code) | T | DEC-0266, DEC-0208 → 15 |
