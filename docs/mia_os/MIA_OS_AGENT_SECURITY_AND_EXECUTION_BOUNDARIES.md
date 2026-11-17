# MIA OS: agent security (Prompt 13 §10)

*Claude (Opus), 2026-11-18. Planning only. Agents: DEC-0219.*

| Rule | Enforced by |
|---|---|
| Agents read; only the coordinator in code proposes changes | roles with read-only tools |
| An agent can't give another agent more than it has | delegation passes the caller's scope down, never up (the run's person and grants) |
| An agent's output is content, not instruction | the workspace marks entries as a specialist's until he confirms |
| A run carries its person | the run record; actions run as the approver (`crediting`) |
| The stop reaches every run | `core/stop.py`, the run record |
| Agents in the lab can't touch protected files | the protected list |

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-SEC-021 | A delegated task shall run with no more than its caller's scope; an agent can't raise its own or another's. | Must | MVP | All | Exists (read-only roles) | T | DEC-0219, DEC-0253 → 13 |
