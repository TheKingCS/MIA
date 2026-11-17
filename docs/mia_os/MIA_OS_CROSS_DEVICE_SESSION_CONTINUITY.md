# MIA OS: one conversation across devices (Prompt 12 §14)

*Claude (Opus), 2026-11-18. Planning only.*

| Moving | How | Exists |
|---|---|---|
| A conversation from the PC to the phone | conversations sync, merged by conversation, messages by time; the phone opens the latest | yes (after a sync) |
| "Where were we?" | from his records and the conversation, on whichever device | yes |
| What he's working on | stays on the PC (not synced); the phone can ask the PC ("what was I doing at home?") | new |
| A screen half-done | each page keeps its place on its own device; not carried between devices | by design |
| The glasses mid-answer | the phone's turn; the glasses show its cards | yes |

**Faster handover (planned):** a phone that's linked asks the PC for any conversation updated in the last few minutes
before showing Talk, so a conversation started at the desk continues on the phone without waiting for the next full
sync. Private-mode conversations never travel (REQ-INT-016).

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-DST-018 | Opening Talk on a linked phone shall show a conversation continued from the PC within seconds when the PC is reachable. | Should | R1 | Phone | Partial (sync) | T | DEC-0243 → 12 |
