# MIA OS: the performance observatory (Prompt 09 §9; DEC-0222)

*Claude (Opus), 2026-11-17. Planning only.*

| Measure | Source | Exists |
|---|---|---|
| Time to answer (per route, per model) | the turn trace | partial |
| Model tokens per second, load time | provider reply records (REQ-INT-004) | planned |
| Tool and action success rates | the action record, the Fix-It Log | yes |
| Each process's quality | `core/loops.py` (every store, action family, check and app has a loop or a reason) | yes |
| Test suite time | CI and local runs | yes |
| Resource use | systemd's cgroup accounting on MIA OS (DEC-0195) | planned |

**One place to look:** the loops page and the self-report already gather these; the observatory is their joined view
for Prompt 10 to show. **Optimization is a proposal:** a slow route found here becomes a Night School lesson or a lab
task, measured before and after.

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-SLF-009 | Each answer's time shall be recorded by route and model, and a slowdown beyond its usual range shall reach the Fix-It Log. | Should | R1 | All | Partial (slow turns logged) | T | DEC-0222 → 09 |
