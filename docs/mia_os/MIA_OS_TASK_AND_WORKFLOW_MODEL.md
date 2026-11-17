# MIA OS: tasks and plans (Prompt 08 §5 to 6; DEC-0214)

*Claude (Opus), 2026-11-17. Planning only.*

## 1. One shape for work done in steps

Five engines run steps today: plans (`step_plans.py`), workflows, taught skills, browser routines, and (soon) teams.
All already write the run record (`runs.py`). The proposal is to converge on **one step model** while keeping each
engine's own vocabulary:

| Field | Meaning |
|---|---|
| `step_id`, `kind`, `params` | an action kind on the contract (or a read, or "his part": something only he can do) |
| `depends_on` | steps that must be done first (**new**) |
| `acceptance` | how code checks it worked (DEC-0218) |
| `tier`, `reach`, `reversibility` | from the contract |
| `status` | waiting, ready, running, done, dropped, failed, can't, his part |
| `retries` | allowed, used |

A plan is a graph of steps. A step is **ready** when its dependencies are done. Ready steps that need no approval and
are within a grant may run in order; anything else waits for him.

## 2. Planning

| Source of a plan | How | Exists |
|---|---|---|
| The week (W-2) | code, from today's list | yes |
| A project's needs | code, from requirements and prices | partial |
| A team's coordinator | a model drafts tasks; code checks every kind and parameter (`step_plans.make`) | T3 |
| A template from a past project | code, adapted | planned (DEC-0199 learning) |

**A model's plan is a proposal:** every step is checked by its action's own `describe` before it's shown, and a step
the model invented that isn't a real kind is listed as "can't" (exists).

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-AGT-004 | Steps shall have dependencies, and only a step whose dependencies are done may start. | Must | R1 | All | New | T: a graph with a cycle refused; order enforced | DEC-0214 → 08 |
| REQ-AGT-005 | Every engine that runs steps shall write the run record, so "what's running" and "stop" cover all of them. | Must | MVP | All | Exists (four engines) | T | DEC-0188 → 08 |
| REQ-AGT-006 | A plan drafted by a model shall have every step checked by its action before it's shown; an invented kind is listed as "can't". | Must | R1 | All | Exists (`step_plans.make`) | T | DEC-0214 → 08 |
