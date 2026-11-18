# MIA OS: releases and versions (Prompt 15)

*Claude (Opus), 2026-11-18. Planning only.*

| Thing | Rule |
|---|---|
| Version | by date: `2026.11.1` (year, month, release in the month); the commit hash beside it |
| Channels | `stable` (what his machines follow) and `next` (every green build, for testing in the VM) |
| A release | a green `next` build promoted to `stable`; monthly with his approval (Q-101), sooner for a fix |
| Notes | written from the month's commits and decisions in plain words |
| The phone app | the same version name; installed by him |
| A bad release | rolled back on the machine (DEC-0257); `stable` moved back to the previous |

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-DEV-022 | Each release shall have a date-based version, plain-language notes, and be promoted to his machines only after it boots in the VM and he approves (or a fix he's allowed). | Should | R1 | All | New | D | DEC-0265 (Q-101) → 15 |
