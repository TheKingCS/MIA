# MIA OS: shared and personal (Prompt 10 §19)

*Claude (Opus), 2026-11-17. Planning only. DEC-0119 says MIA is for Zac alone; Zac's answer to Q-82 makes the
household display the exception: it is for him and his wife.*

| Data | Kind | Where shown |
|---|---|---|
| Conversations, memories, journal, notes, workouts, notifications | personal (`PERSONAL_STORES`) | only his sessions |
| Calendar, kitchen, maintenance, inventory, budget | household (`HOUSEHOLD_STORES`) | his views; a shared display if he makes one |

**The household display** (Zac, Q-82: "the display is important and is for me and my wife to use") is planned
for real: a screen for the two of them (the kitchen idea: calendar, kitchen, workouts, music, photos) showing
household stores, signed in as the household rather than as either person. Each of them still has their own account
and personal data (`core/profile_manager.py`, `core/household_manager.py`); the display shows neither person's
conversations, memories, journal or notifications. Talking to it answers from household stores only; anything
personal is "ask on your own screen". It is a device in Prompt 12's family (a smart display, Q-66), running the
same web screens in the ambient layout.

**Rule:** a shared view never implies access to a personal store; the stores' split is already in code.

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-DSK-028 | The household display shall show only household stores and never a personal store or conversation of either person. | Must | R1 | All | Planned | T | DEC-0228 (Q-82) → 10, 12, 13 |
| REQ-DSK-034 | Asked something personal on the household display, MIA shall answer from household stores only and say the rest is on the person's own screen. | Must | R1 | All | New | T | DEC-0228 (Q-82) → 10, 13 |
