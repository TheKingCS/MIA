# MIA OS: telling him what's wrong (Prompt 14)

*Claude (Opus), 2026-11-18. Planning only.*

| Situation | What he's told | Where |
|---|---|---|
| Still starting | "Starting up… voice in a moment" | the shell |
| Something didn't start | one line, what it means, how to fix | the status strip, Diagnostics |
| She restarted something | after, through the gate (DEC-0222) | a message |
| An update is ready | "An update is ready; restart tonight?" | a card |
| An update rolled back | "Last night's update didn't start properly, so I went back to the one before. Nothing was lost." | a message |
| A store recovered | what was kept aside and how to restore it | a message |
| The restore drill | passed or what failed | Diagnostics |

**Plain words always**; the detail (unit names, logs) one press deeper in Diagnostics.

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-REL-036 | Every recovery MIA or the OS makes (a restart, a rollback, a store kept aside) shall be told to him in plain words with what was lost, if anything. | Must | MVP | All | Partial | T | DEC-0261 → 14 |
