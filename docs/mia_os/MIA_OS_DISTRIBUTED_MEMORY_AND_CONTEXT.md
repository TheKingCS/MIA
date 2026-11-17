# MIA OS: memory and context across devices (Prompt 12 §9)

*Claude (Opus), 2026-11-18. Planning only. Memory: Prompt 07 (DEC-0210).*

| What | Where | Synced |
|---|---|---|
| His records (personal, household) | every full engine | yes, three-way merge (`core/sync.py`) |
| The history (`life_events.jsonl`) | every full engine | yes, merged by event id |
| What MIA remembers | every full engine | yes (a personal store) |
| The private journal | only devices holding its key | yes, sealed the whole way |
| The recall index (vectors) | the hub; rebuilt on each engine from its own records | **no**: derived, rebuilt where it's used |
| Turn traces, the Fix-It Log | each device's own | merged line by line (the Fix-It Log) |
| What he's working on (`activity.json`) | the PC only | **no** (`NEVER_SYNC` to add) |
| Device-level things (cameras, logs, the model) | that device | no (`NEVER_SYNC`) |

**Context for a turn** is assembled on the engine answering it, from its own copy; a phone turn sent to the PC's
model carries the context the phone assembled, not the PC's.

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-DST-011 | Derived data (the recall index) and device-only data (what he's working on, cameras, logs) shall never sync; each engine rebuilds what's derived from its own records. | Must | R1 | All | Partial (`NEVER_SYNC`) | T | DEC-0243 → 12, 13 |
