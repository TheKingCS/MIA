# MIA OS: implementation risks (Prompt 16)

*Claude (Opus), 2026-11-18. Also in `MIA_OS_RISK_REGISTER.md`.*

| ID | Risk | Impact | Likelihood | Response |
|---|---|---|---|---|
| R-81 | The GPU runs worse under Linux (ROCm on the 7900 XTX) | H | L | PoC 1 first; Vulkan backend as a fallback; Ubuntu the base fallback (DEC-0189) |
| R-82 | KWin as MIA's session doesn't hold up (PoC 3) | M | M | cage for the MVP; Plasma with MIA full screen as a second fallback |
| R-83 | The move loses or garbles data | H | L | the migration report must match; Windows kept intact; the backup |
| R-84 | Stage 0's backlog grows faster than the OS work | M | M | the critical path first in each session; the backlog in parallel |
| R-85 | His hands-on steps wait (USB stick, drive) | M | H | WAITING_ON; everything else continues in the VM |
