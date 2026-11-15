# MIA OS central risk register

*Central register. Each risk's detail and evidence are in the prompt
report that found it. Rated H, M or L.*

| ID | Risk | Sev | Like | Source | Must be dealt with before | Owner |
|---|---|---|---|---|---|---|
| R-01 | Runtime lives in the Qt process | H | H | Prompt 01 | any OS work | Claude (engine) |
| R-02 | No Linux or Android key backend for at-rest sealing | H | H | Prompt 01 | data on Linux | Claude |
| R-05 | No capability or grant model for system actions | H | H | Prompt 01 | any system action | Prompt 08/13 |
| R-07 | No Linux CI | H | H | Prompt 01 | OS work | Prompt 15 |
| R-06 | Test isolation: the at-rest key reset leaks between tests | M | H | Prompt 01 | Linux CI | Claude |
| R-04 | Unsandboxed modules and scripts | H | M | Prompt 01 | third-party apps | Prompt 03/13 |
| R-08 | Builds aren't reproducible | M | H | Prompt 01 | image builds | Prompt 15 |
| R-12 | Docs drift, and a conflict over who MIA is for | M | H | Prompt 01 | Prompt 04 | Zac (Q-01) |
| R-19 | A release-signing weakness | M | L | Prompt 01 | soon | **mitigated by DEC-0160 once Zac adds the secrets** |
| R-03, R-09–R-11, R-13–R-18, R-20 | see `MIA_OS_TECHNICAL_DEBT_AND_RISK_REGISTER.md` | | | Prompt 01 | | |
| R-03 | Two Android apps | — | — | Prompt 01 | — | **closed: Companion app retired (DEC-0160)** |
| R-22 | LEP background discovery goes online routinely; scraping is fragile; sources change | M | H | Prompt 02 | building LEP discovery | Zac (Q-08), then adapters with tests |
| R-23 | Speaker identification errors could expose one partner's data to the other | H | M | Prompt 02 | shared conversation | MU-4/MU-5: ask when unsure; no approvals on an unidentified voice |
| R-21 | Scope: 17 prompts asking for ~300 documents could bury the engineering | M | M | review of the library | throughout | Claude: keep documents small, and merge where the directive allows ("avoid duplicating") |
