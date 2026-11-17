# MIA OS: agent security and isolation (Prompt 08 §19)

*Claude (Opus), 2026-11-17. Planning only. Prompt 13 designs security as a whole.*

| Threat | Control | Exists |
|---|---|---|
| A page, file or email tells an agent to act | outside text framed; a turn that read it can't change a record in the same breath; agents can't act at all | yes |
| An agent grants itself more | no action gives a grant; grants only from his yes | yes |
| A model invents a step or parameter | each step checked by its action's `describe`; invented kinds listed as "can't" | yes |
| A runaway loop | budgets, retry limits, the stop, homeostasis's backoff | yes |
| Agent code from outside | out of process and sandboxed (DEC-0176); Landlock for her sub-processes (PoC 6) | planned |
| An agent reads what it shouldn't | its tools are read-only and scoped to the task's entries; secrets never in prompts | yes |
| A compromised device approves | approvals run as the person; outward kinds need the phone or PC, not the glasses alone | partial |

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-AGT-028 | Text an agent read shall never change what an action does or whether it's approved. | Must | MVP | All | Exists | T: planted-instruction tests | DEC-0219, DEC-0156 → 08 |
| REQ-AGT-029 | Every loop that retries shall have a limit, and every run shall stop on "stop". | Must | MVP | All | Exists | T | DEC-0214 → 08 |
