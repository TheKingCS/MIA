# MIA OS: household privacy (Prompt 13 §19)

*Claude (Opus), 2026-11-18. Planning only. MIA is for Zac, with the household display for him and his wife (Q-82).*

| Data | Zac | His wife (her own account) | The household display |
|---|---|---|---|
| Zac's personal and sensitive stores | yes | no | no |
| Her personal stores | no | yes | no |
| Household stores (calendar, kitchen, maintenance, budget if shared) | yes | yes, as a member | yes |
| Conversations | each their own | each their own | none |

**The display** signs in with a household key (DEC-0242): it can read household stores and nothing else; asked
something personal it says to ask on your own screen (REQ-DSK-034). **Joining a household** needs a member's approval
(`core/household_manager.py`).

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-SEC-032 | A household key shall read household stores only and never a person's store or conversation. | Must | R1 | All | New | T | DEC-0242, DEC-0228 → 13 |
