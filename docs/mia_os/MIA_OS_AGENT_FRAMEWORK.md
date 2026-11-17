# MIA OS: the agent framework (Prompt 08 §7; DEC-0219)

*Claude (Opus), 2026-11-17. Planning only. Built on DEC-0197 to 0199 and `MIA_OS_SPECIALIZED_AGENT_TEAMS.md`.*

## 1. What an agent is here

An agent is a **role** in `core/specialists.py` (`ROLES`, DEC-0198): a charter, limits, the task types it takes,
read-only tools, its model's needs, whom it reviews, and a caveat. It is not a process, not a model and never a
holder of grants. The roster is checked in code (`core/specialist_roster.py`), its models chosen from the bench and
inspected by Claude (DEC-0200).

| Kind | Example | Exists |
|---|---|---|
| Specialists | electrical, greenhouse, acoustics (23) | yes |
| The coordinator | MIA herself, in code plus one model call per decision | T3 |
| Engines that act | plans, workflows, taught skills, browser routines | yes |
| Development agents | Claude Code, Codex, Copilot in the lab | yes (Prompt 09) |

## 2. What an agent may do

- **Read:** its tools (all observe or suggest); the entries its task names.
- **Write:** entries in a project's workspace (`core/teamwork.py`), always *derived* until he confirms.
- **Propose:** recommendations. **Never** execute, never call an action kind, never hold a grant.
- **The coordinator** turns accepted recommendations into proposals on the contract, under the tier rules.

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-AGT-007 | An agent shall have only read-only tools; a test sweep shall fail on any agent tool that changes a record. | Must | MVP | All | Exists (T1 test) | T | DEC-0219 → 08 |
| REQ-AGT-008 | Only the coordinator, in code, may turn an agent's recommendation into a proposal, and only on the action contract. | Must | R1 | All | New (T3) | T | DEC-0219 → 08 |
