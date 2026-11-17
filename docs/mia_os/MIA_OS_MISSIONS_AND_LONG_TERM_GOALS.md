# MIA OS: missions and long-term goals (Prompt 08 §15)

*Claude (Opus), 2026-11-17. Planning only.*

**Exists:** missions (`core/mission_manager.py`) with steps, recurring missions, projects with needs, learning paths
(`core/paths.py`: understand, plan stages, teach, practice, homework missions, verify by evidence), guided walkthroughs
as missions (never on Today, Zac 2026-11-09), the reward layer.

**Proposed: a goal sits on a project or a path** (`MIA_OS_INTENT_AND_GOAL_MODEL.md`), with:
- success criteria checked by code where possible;
- a plan that's re-made when the world changes (a need bought, a date moved), shown as "the plan changed because...";
- a weekly look back (the existing Sunday check-in): what moved, what's stuck, one next step;
- persistence across restarts and devices (the stores and the run record already give it).

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-AGT-022 | When a goal's plan is re-made, MIA shall say what changed and why, and never drop a step he started. | Should | R1 | All | New | T | DEC-0214 → 08 |
