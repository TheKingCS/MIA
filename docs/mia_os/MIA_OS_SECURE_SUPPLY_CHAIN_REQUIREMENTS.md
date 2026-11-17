# MIA OS: supply chain (Prompt 13 §23)

*Claude (Opus), 2026-11-18. Planning only. Build infrastructure: Prompt 15; updates: Prompt 14.*

| Part | Control | State |
|---|---|---|
| Python packages | pinned in requirements; the weekly OSV check | built |
| The phone build's packages | an OSV check of its dependency report | to add |
| Models | pulled by name, recorded by digest; benched and inspected before specialists use them | partial |
| The OS image | built from the repository, signed (cosign), verified on update | planned (DEC-0189) |
| Her own code changes | the lab, Claude's pass, the suite | built |
| Commits | from known identities; CI on every push | built |
| Outside services | Tailscale, Meta's toolkit, Ollama's library, Fedora's repositories, GitHub | named and watched |

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-SEC-036 | Every dependency (Python, the phone build, models, the OS image) shall be pinned or recorded by digest and checked for known vulnerabilities. | Must | R1 | All | Partial (Python) | T | DEC-0253 → 13, 15 |
