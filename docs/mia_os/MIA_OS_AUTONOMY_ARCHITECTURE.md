# MIA OS: autonomy architecture (Prompt 08)

*Claude (Opus), 2026-11-17, on Zac's go ("lets continue"). Planning only: no agent, permission, automation or grant
was changed. The prompt is kept verbatim in `prompts/08_AUTONOMY_AGENTS_INTELLIGENT_SYSTEM_MANAGEMENT.md`. Twenty-three
documents sit beside this one (section 9).*

## 1. The headline

1. **One deterministic execution boundary, and it exists:** every change MIA can make is an action kind on the action
   contract (`core/actions.py`: propose, approve, execute, record, undo), each with a tier (`core/grants.py`), a reach
   and a reversibility (`core/action_effects.py`). 482 kinds are registered today; a test fails on one without a tier.
   Models propose; code executes. MIA OS adds kinds (system, devices), never a second path (DEC-0213).
2. **One task model:** a goal becomes a plan of steps (`core/step_plans.py`), every plan a run (`core/runs.py`),
   stoppable (`core/stop.py`). Workflows, taught skills, browser routines and teams converge on it; dependencies between
   steps are the one big piece to add (DEC-0214).
3. **Autonomy is earned, never assumed:** the five tiers (DEC-0181) plus grants that are learned skills or published
   workflows; a grant is offered only with evidence and given only by Zac; nothing MIA reads can grant anything
   (DEC-0156, DEC-0215).
4. **Risk is computed in code** from reach, reversibility, money, other people and the physical world; it sets the
   least tier a kind may have, and an unknown is treated as the highest (DEC-0216).
5. **Proactive help goes through one gate** (`core/communication_gate.py`), paced by what he opens and dismisses,
   triggered by his records (DEC-0217).
6. **Done means verified:** after an action, code reads the effect back (the store, the page, the device's own
   report); a model saying "done" is never evidence (DEC-0218).
7. **Agents propose, the coordinator acts:** a specialist or team member writes entries and recommendations; only
   MIA's coordinator, in code, turns them into proposals on the contract (DEC-0198, DEC-0219).

## 2. The audit (verified in the code, 2026-11-17)

| Piece | Exists | Notes |
|---|---|---|
| Action contract | `core/actions.py` (735 lines), 482 kinds | propose, approve, execute, record, undo; `run_as_tool` for voice |
| Tiers and grants | `core/grants.py`; tiers in every app manifest (636 within a grant, 158 observe, 139 with approval, 10 suggest) | `require()` before anything MIA starts herself |
| Reach and reversibility | `core/action_effects.py` (UI-3) | irreversible kinds say so on the card |
| Undo and history | `core/undo_log.py`, `core/change_history.py` (30 days, by time and subject) | |
| Runs | `core/runs.py` (UI-1): browser routines, taught skills, workflows, plans | "what's running" |
| Stop | `core/stop.py` (UI-2): "stop", "stop everything", "carry on" | in code, first |
| Plans | `core/step_plans.py` (UI-7): steps across apps, one at a time; only records-reach, undoable kinds | no dependencies yet |
| Taught skills | `core/taught_skills.py`: practising until learned, then a grant | |
| Workflows | `core/workflows.py`: fixed vocabulary, standing approval by kind | |
| Browser | `core/browser_routines.py`, `core/browser_safety.py`: every step classified in code; commits only by him | |
| Proactive | `core/communication_gate.py` (pacing, merging, repeats), daily checks, insights, World Intelligence | |
| Background | `core/background_jobs.py`, `core/scheduler.py`, `core/homeostasis.py` (eases off when busy, on battery, offline) | |
| Missions and goals | `core/mission_manager.py`, recurring missions, learning paths (`core/paths.py`) | |
| Teams | `core/teamwork.py` (T2: workspace, a team starts only on his yes) | T3 coordination next |
| Self-modification | `core/dev_lab.py` (worktree, suite, merge, auto-revert) | Prompt 09's |
| Observability | `core/agent_activity.py`, the turn trace, loops, corrections | |

**Gaps:** dependencies between steps (T3); system and device action kinds (MIA OS, through the helper); verification
that reads effects back (partial: plans re-check before each step; nothing re-reads after); a trust ladder that offers
grants from evidence; one place showing every pending approval across devices (the action center lists them per person).

## 3. The layers

```
 intent ──▶ goal ──▶ plan (steps, dependencies) ──▶ for each ready step:
   (his words,     (a mission,    (step_plans, the     tier check (grants) ──▶ approval if needed ──▶
    a trigger)      a project)     team's tasks)       execute (the action's own code) ──▶ verify (read back)
                                                        ──▶ record (history, undo) ──▶ next step / report
   models help with: understanding, planning, choosing    ─────────────  code does: everything after "propose"
```

## 4. Decisions (records in `MIA_OS_AUTONOMY_TECHNOLOGY_EVALUATION.md` §3)

| DEC | Decision | Status |
|---|---|---|
| DEC-0213 | The action contract is the one execution boundary, for apps, the system and devices | PROPOSED |
| DEC-0214 | One task model: goals, plans of steps with dependencies, every plan a run | PROPOSED |
| DEC-0215 | Graduated autonomy: tiers plus grants earned with evidence and given by Zac; a trust ladder that offers, never takes | PROPOSED |
| DEC-0216 | Risk computed in code sets each kind's least tier; unknown is highest | PROPOSED |
| DEC-0217 | Proactive help only through the communication gate, triggered by records | PROPOSED |
| DEC-0218 | Verification by reading effects back; a model's "done" is never evidence | PROPOSED |
| DEC-0219 | Agents propose; the coordinator in code acts | PROPOSED |

## 5. Questions for Zac

`MIA_OS_AUTONOMY_OPEN_QUESTIONS.md`: Q-73 (the trust ladder), Q-74 (proactive help from what he's working on),
Q-75 (quiet hours).

## 6. Boundaries

Prompt 09 owns self-inspection and self-modification (the lab and the forge appear here only as action kinds and
runs). Prompt 12 distributes execution; Prompt 13 designs security as a whole; this sets autonomy's own controls.

## 7. Sources

The repository's code, read 2026-11-17 (each file named above); the decisions it rests on (DEC-0156, 0173, 0181,
0188, 0196 to 0200). Technology sources are in the technology evaluation.

## 8. What it means for him

Day to day, nothing changes: MIA still asks before anything outward or irreversible, does routine undoable work where
he's granted it, and says what she did with an Undo. What grows is how much she can carry for him across apps and
days, always as a plan he can see, stop and undo.

## 9. The documents

`MIA_OS_INTENT_AND_GOAL_MODEL.md`, `MIA_OS_TASK_AND_WORKFLOW_MODEL.md`, `MIA_OS_AGENT_FRAMEWORK.md`,
`MIA_OS_AGENT_ORCHESTRATION.md`, `MIA_OS_TOOL_AND_CAPABILITY_EXECUTION.md`, `MIA_OS_ACTION_CONTRACTS.md`,
`MIA_OS_AUTONOMY_LEVELS_AND_APPROVALS.md`, `MIA_OS_ACTION_RISK_CLASSIFICATION.md`, `MIA_OS_PROACTIVE_INTELLIGENCE.md`,
`MIA_OS_WORKFLOW_ENGINE.md`, `MIA_OS_MISSIONS_AND_LONG_TERM_GOALS.md`, `MIA_OS_APPLICATION_AND_SYSTEM_AUTOMATION.md`,
`MIA_OS_DISTRIBUTED_EXECUTION.md`, `MIA_OS_HUMAN_OVERSIGHT_AND_APPROVAL_INTERFACE.md`,
`MIA_OS_AGENT_SECURITY_AND_ISOLATION.md`, `MIA_OS_EXECUTION_VERIFICATION.md`, `MIA_OS_AUTONOMY_FAILURE_AND_RECOVERY.md`,
`MIA_OS_AUTONOMY_OBSERVABILITY_AND_AUDIT.md`, `MIA_OS_AUTONOMY_RESOURCE_MANAGEMENT.md`,
`MIA_OS_AUTONOMY_TECHNOLOGY_EVALUATION.md`, `MIA_OS_AUTONOMY_ARCHITECTURE_DIAGRAMS.md`,
`MIA_OS_AUTONOMY_ACCEPTANCE_CRITERIA.md`, `MIA_OS_AUTONOMY_OPEN_QUESTIONS.md`.
