# MIA OS: live system introspection (Prompt 09 §7)

*Claude (Opus), 2026-11-17. Planning only. Hardware facts: DEC-0203.*

| She can see now | From | Exists |
|---|---|---|
| Services up or down | `core/service_map.py` (each checked), systemd on MIA OS | yes / planned |
| Models loaded, memory used | `core/model_registry.py` (Ollama's API) | yes |
| CPU, memory, disk, temperature | `core/system_health.py` (psutil); hwmon and SMART on MIA OS | yes / planned |
| What's running | the run record (`core/runs.py`) | yes |
| Jobs and their backoff | the scheduler, homeostasis | yes |
| The model queue | DEC-0204 | planned |
| Network and devices | connectivity, linked devices, the homestead link | yes |

**Rules:** read-only; never a destructive check; each reading has its time; a check that can't run says so.

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-SLF-007 | Every live reading about herself shall carry its source and time, and a check that can't run shall report itself as unknown, never as fine. | Must | R1 | All | Partial | T | DEC-0221 → 09 |
