# MIA OS: health checks and readiness (Prompt 14)

*Claude (Opus), 2026-11-18. Planning only. Health in depth: Prompt 09 (DEC-0222).*

| Level | Means | Signalled by |
|---|---|---|
| started | the process is up | systemd |
| core ready | stores loaded (sealed data opened), actions and screens answer | `sd_notify READY=1`; `/api/runtime/health` |
| voice ready | speech in and out loaded | the health endpoint |
| models warm | the everyday model answers | the health endpoint; her orb leaves "unavailable" |
| all ready | jobs scheduled, devices linked | the health endpoint |

**Liveness:** a watchdog ping from the runtime's own loop (`WatchdogSec=`); a stuck runtime is restarted. **Checks
look, never change** (Prompt 09). **The shell** asks the health endpoint and shows what isn't ready.

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-REL-018 | The runtime shall tell systemd it's ready only once his stores are open, and ping a watchdog from its main loop so a hang is restarted. | Must | MVP | PC | Partial (the health endpoint) | T | DEC-0256, REQ-REL-004 → 14 |
