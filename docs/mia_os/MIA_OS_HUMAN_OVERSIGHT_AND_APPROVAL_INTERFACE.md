# MIA OS: human oversight and the approval interface (Prompt 08 §18)

*Claude (Opus), 2026-11-17. Planning only. The look is Prompt 10/11's.*

| He can | Where | Exists |
|---|---|---|
| Approve or decline a card | the card (web, phone, glasses), by voice ("yes, do it") | yes |
| See what each card reaches and whether it can be undone | on the card | yes (UI-3) |
| Undo the last change, or by time and subject | Recent Changes, "undo what you did to the greenhouse this afternoon" | yes |
| See what's running and stop it | Agent Activity's Running column, "what's running", the Stop button | yes |
| See his grants and take one back | one list | yes |
| See every pending approval in one place, across devices | an Approvals page | **new** |
| Ask why MIA did or proposed something | "why did you…?" from the trace and the plan | partial |
| Set quiet hours and pace | settings | partial (pace learned) |

**Card rules:** Approve Once and Approve From Now On where a grant is allowed (Q-73); one sentence in plain words of what will happen; reach and "can't be undone" when true; the plan
it belongs to ("step 2 of 4"); approving on the glasses needs the phone for anything outward.

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-AGT-026 | Every pending approval shall be listed in one place on every device, with what it reaches and its plan. | Must | R1 | All | New | T | DEC-0215 → 08, 10 |
| REQ-AGT-027 | For any action MIA took or proposed, she shall answer "why" from the plan, the trigger and the trace. | Should | R1 | All | Partial | T | DEC-0218 → 08 |
