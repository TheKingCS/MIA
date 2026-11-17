# MIA OS: the workflow engine (Prompt 08 §14)

*Claude (Opus), 2026-11-17. Planning only.*

**Exists** (`core/workflows.py`, DEC-0092): something done again and again, as a specification: a trigger (day, week,
month) and steps from a fixed vocabulary (`read`, `count`/`sum`/..., `when`, `tell` through the gate, `add` through
`records.add`). Publishing approves exactly the kinds it lists (a standing grant); a new kind needs a new version;
`dry_run()` shows what it would do; every run is logged and a run.

**Proposed:**

| Addition | Why | Rule |
|---|---|---|
| Triggers on events (a record changed, a reading crossed a line) as well as time | "when the tank drops below 20%..." | the event comes from `life_events`, never from outside text |
| Steps that are any granted action kind (not only `records.add`) | broader automation | each kind still within the workflow's published grant |
| A workflow from a repeated plan | the trust ladder for multi-step work | offered with the evidence; published only by him |

**Not adopted:** a general workflow engine (Temporal, n8n, Airflow): MIA's runs are small, local and per person; a
second engine would duplicate the run record and the grants (technology evaluation).

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-AGT-020 | A workflow shall run only the kinds its published version lists, and a change to them shall need a new version he publishes. | Must | MVP | All | Exists | T | DEC-0215 → 08 |
| REQ-AGT-021 | A workflow trigger shall come from a time or a record's change, never from text MIA read. | Must | R1 | All | Exists (time); New (events) | T | DEC-0217 → 08 |
