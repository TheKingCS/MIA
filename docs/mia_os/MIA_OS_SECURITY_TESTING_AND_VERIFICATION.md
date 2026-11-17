# MIA OS: security testing (Prompt 13 §25)

*Claude (Opus), 2026-11-18. Planning only.*

| Test | What | State |
|---|---|---|
| Unit tests on sign-in, sessions, two-step, the wait, keys | the server's security paths | built |
| No secrets in logs | every log call read as code | built |
| No control characters in code | a mangled escape once disabled a check | built |
| Manifests claim exactly what exists; every kind tiered | the registry tests | built |
| Injection set | pages, emails and documents with embedded instructions; no change without a card | to build (REQ-SEC-020) |
| Approval replay | a reused approval or changed parameters refused | to build (REQ-SEC-016) |
| Boundary tests | one per trust boundary | to build (REQ-SEC-011) |
| Dependency audit | weekly | built |
| An independent review of each night's builds | a fresh agent reads the commits end to end | practice (2026-11-18) |
| A yearly review against OWASP ASVS | `docs/SECURITY.md` | planned |

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-SEC-038 | Each trust boundary, the approval binding and prompt injection shall have tests that run with the suite. | Must | R1 | All | Partial | T | DEC-0248 → 13 |
