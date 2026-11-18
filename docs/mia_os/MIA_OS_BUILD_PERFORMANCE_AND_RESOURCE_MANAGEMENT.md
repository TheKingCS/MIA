# MIA OS: build performance (Prompt 15)

*Claude (Opus), 2026-11-18. Planning only.*

| Concern | Today | Plan |
|---|---|---|
| The suite | about 5 minutes on his PC (one process) | pytest-xdist across 16 threads (the 9800X3D) once tests are checked for shared state |
| CI minutes | public repo: free | private (Q-99) would cap minutes; the heavy jobs (VM, image) only on their inputs |
| The image build | — | cached layers; only on changes to its inputs |
| The phone build | Gradle caches in CI | the same |
| Benches | on his GPU, at night | the GPU queue (DEC-0204) |
| Her lab | the full suite twice per change | the base suite cached for the night (built) |

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-DEV-028 | The full suite shall run in under 3 minutes on his PC once it runs in parallel. | Could | R1 | PC | New | M | DEC-0266 → 15 |
