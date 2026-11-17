# MIA OS: security acceptance criteria (Prompt 13)

*Claude (Opus), 2026-11-18. Planning only.*

| The prompt's area | Met by |
|---|---|
| Existing posture audited | the architecture §2; gaps in general terms, specifics in `audit/` |
| Philosophy, threat model, boundaries | DEC-0248; threat model; trust boundaries |
| Identity, authorization, risk and approval, consent | DEC-0250; the four documents |
| AI and injection | DEC-0249 |
| Agents, Linux privilege, apps | DEC-0253; the three documents |
| Devices | distributed device security |
| Data classes, memory privacy | DEC-0251 |
| Encryption, secrets | DEC-0252 |
| Sensors, household, physical safety | the three documents |
| Audit, monitoring, incident response | DEC-0254 |
| Supply chain, backups, testing | the three documents |
| Technologies | technology evaluation |
| Diagrams, scenarios A to L | the two documents |
| Questions, risks | Q-91 to Q-94; the security risk register |

| REQ-SEC (011 to 039) | Verified by |
|---|---|
| 012, 014, 017, 018, 021, 023, 030, 031 | existing tests |
| 013, 022, 029 | MIA OS proofs of concept |
| the rest | new tests as each is built |
