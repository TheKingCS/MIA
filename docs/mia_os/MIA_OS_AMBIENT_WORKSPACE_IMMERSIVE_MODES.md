# MIA OS: ambient, workspace and immersive (Prompt 10 §9; DEC-0231)

*Claude (Opus), 2026-11-17. Planning only.*

| Mode | Shows | Her behaviour | Entered by |
|---|---|---|---|
| **Ambient** | the day, what's due, music, her presence, background work; large type | messages through the gate at their usual pace | idle for a while, the second monitor, "ambient" |
| **Workspace** | sidebar, main area, Talk, windows | as now | any app or search, a key |
| **Immersive** | one experience full screen (Living Worlds, the Convergence, a lesson, a game) | non-urgent messages wait; urgent ones and alarms still come | opening an immersive app |

**One shell, three states** (`data-mode` on the shell, as `data-theme` is today): the same session, records and Talk
thread. Leaving a mode returns to the screen and scroll he left. Esc or a key leaves Immersive.

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-DSK-013 | Ambient, Workspace and Immersive shall be states of the one shell, each leaving him on the screen he left, and Immersive left with one key. | Should | R1 | PC | New | T | DEC-0231 → 10, 11 |
| REQ-DSK-014 | In Immersive mode, alarms and urgent messages shall still come; others wait until he leaves it. | Must | R1 | PC | New | T | DEC-0231, DEC-0217 → 10 |
