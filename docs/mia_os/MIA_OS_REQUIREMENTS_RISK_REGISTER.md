# MIA OS: requirements risk register (Prompt 04, deliverable 15)

*Claude (Opus), 2026-11-15. Planning only. Risks to meeting the requirements. The central register
(`MIA_OS_RISK_REGISTER.md`) carries R-26 to R-33 from here. Severity and likelihood: H, M, L.*

| ID | Risk | Sev | Like | Area | Mitigation | Owner |
|---|---|---|---|---|---|---|
| R-26 | Scope: prompt 23 and the vision add more than one person and his agents can build and keep working | H | H | scope | MoSCoW plus tiers; the MVP excludes everything not needed for a MIA-first desktop; Won't is recorded so it isn't re-proposed | 16 |
| R-27 | GPU compute on the chosen Linux base is worse than on Windows, or breaks with an update | H | M | feasibility | REQ-HW-002 tested before the switch; the image pins a known-good driver; CPU fallback for the 3B model | 06, 14 |
| R-28 | Moving his data to Linux loses or corrupts something (sealed files under a new key) | H | M | migration | A rehearsal on a copy; backups first; REQ-CMP-002 as an acceptance gate | 16 |
| R-29 | The MIA session becomes the only practical way in, quietly eroding the conventional desktop | M | M | experience | REQ-ARC-002 and REQ-UX-011 tested every release with MIA masked | 10, 14 |
| R-30 | Performance targets set without the image prove wrong | M | H | performance | Marked provisional; re-set from measurements on the prototype | 14 |
| R-31 | The small everyday model's mistakes reach actions | H | M | reliability | Code decides facts and tiers; approvals in code-written words; outside text never steers a change; the bigger model where it matters | 07, 08 |
| R-32 | Requirements and code drift apart | M | H | governance | The matrix is generated and tested; each status names its evidence; reviewed at each prompt | 17 |
| R-33 | Accessibility is left to the end and becomes expensive | M | M | experience | REQ-ACC rows tiered R1, with an automated check in the suite before R1 | 10 |
