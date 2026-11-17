# MIA OS: desktop failure and fallback (Prompt 10 §22)

*Claude (Opus), 2026-11-17. Planning only. Boot and recovery in full: Prompt 14.*

| Failure | What happens | He still has |
|---|---|---|
| Shell window crashes | systemd user unit restarts it (backoff); KWin and his windows stay | his apps; Plasma a logout away |
| Runtime down | the shell says so and offers "open Plasma"; records unreachable | Plasma, his apps, files |
| Model down | Talk says so; every screen works (no model needed); her self-repair starts Ollama (DEC-0222) | everything but answers in words |
| KWin fails | the session ends to SDDM | the Plasma session or a TTY |
| Network lost | offline; web results unavailable | everything local |
| GPU or display change | KWin re-lays out; the shell follows the new size | |
| Memory pressure | systemd-oomd ends lower-priority units first; models unloaded before the shell (DEC-0204) | the shell |
| Session interrupted | windows restored by KWin; her screens reopen where they were | |

**Safe mode:** a login entry starting the shell with no background jobs, no models and no themes beyond the default,
for when something of hers misbehaves.

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-DSK-031 | If MIA's shell crashes, it shall restart by itself without closing his other windows, and the conventional desktop shall stay reachable. | Must | MVP | PC | Planned | D: PoC 3 | DEC-0227, REQ-PER-002 → 10, 14 |
| REQ-DSK-032 | A safe-mode login shall start the shell with no background jobs or models. | Should | R1 | PC | New | D | DEC-0227 → 10, 14 |
