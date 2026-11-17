# MIA OS: agent orchestration (Prompt 08 §8)

*Claude (Opus), 2026-11-17. Planning only.*

| Concern | How |
|---|---|
| Who does what | the coordinator assigns a task to a role; the role's model is the specialist's chosen one (inspected) |
| Order | the plan's dependency graph (REQ-AGT-004) |
| Sharing | the project's workspace: entries, never long chats; a task's prompt holds only the entries it names (`teamwork.framed`) |
| Influence | a `constraint` entry re-opens the affected task once; a second re-open goes to the coordinator, a third to Zac |
| Conflict | kept as a `conflict` entry with both sides; settled by a rule (an accepted review) or by Zac |
| Budget | model calls per team, shown before it starts; enforced in code |
| Concurrency | one model job per GPU at a time (DEC-0204); tasks queue; the Workroom's browser agents read in parallel (W1 measures how many) |
| Stop | every team is a run; "stop" ends it at the current task |
| Report | from accepted entries only: done, not done, decisions, costs, risks, deliverables |

**No message bus, no broker** (DEC-0192): orchestration is the coordinator reading and writing the workspace and the
run record in the runtime, the one writer (DEC-0190).

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-AGT-009 | A team's model calls shall stop at the budget approved when it started. | Must | R1 | PC | New (T3) | T | DEC-0198 → 08 |
| REQ-AGT-010 | A task's prompt shall hold only the workspace entries it names. | Must | R1 | PC | Exists (`teamwork.framed`) | T | DEC-0198 → 08 |
