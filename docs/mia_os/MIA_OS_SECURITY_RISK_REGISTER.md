# MIA OS: security risk register (Prompt 13)

*Claude (Opus), 2026-11-18. In general terms; specifics in `audit/` (local). Also in `MIA_OS_RISK_REGISTER.md`.*

| ID | Risk | Impact | Likelihood | Response | Owner |
|---|---|---|---|---|---|
| R-69 | A new kind of outside content reaches the model unmarked | H | M | every entry point marked; the injection set grows with each source (REQ-SEC-020) | Prompt 13 |
| R-70 | A device's data readable before full-disk encryption is everywhere | H | M | sealed stores; drive encryption on MIA OS and his step on Windows | Prompt 13, Zac |
| R-71 | An approval used for something it wasn't shown | H | L | binding to the parameter hash (REQ-SEC-016) | Prompt 13 |
| R-72 | Security rules drift as MIA grows | M | M | protected list; boundary tests; yearly ASVS review | Prompt 13 |
| R-73 | A dependency with a known vulnerability on the phone build | M | M | the phone build's OSV check (REQ-SEC-036) | Prompt 15 |
