# MIA OS: intelligence observability (Prompt 07 §18)

*Claude (Opus), 2026-11-17. Planning only. System observability: DEC-0195.*

| Signal | Exists | Seen where |
|---|---|---|
| Per turn: route, tools offered and called, memories used, model | `core/turn_trace.py` | the Fix-It Log, "why did you say that?" |
| Per model call: device, tokens, seconds, cut off | partial | the trace (REQ-INT-004) |
| Model queue: what's waiting, whose, priority | new (DEC-0204) | "what's using the card?" |
| Quality over time | `core/loops.py`, ratings, corrections | the Loops page |
| Bench and inspections | `work/eng_bench/`, `work/inspections.json` | the Specialists page |
| What's loaded, how much memory | `core/model_registry.py` | "which model are you using?" |

**Rules:** traces hold what's needed to explain a turn, not private text from private modes; they stay on his
devices; he can ask why she said anything and get the route and the sources.

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-INT-035 | For any answer, MIA shall be able to say which route, model, tools and memories produced it. | Must | MVP | All | Exists (turn trace) | T | DEC-0206 → 07 |
