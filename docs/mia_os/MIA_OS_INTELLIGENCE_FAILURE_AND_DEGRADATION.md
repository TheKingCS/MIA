# MIA OS: intelligence failure and degraded operation (Prompt 07 §19)

*Claude (Opus), 2026-11-17. Planning only. Hardware failures: Prompt 06's failure document.*

| Failure | What MIA does | What still works |
|---|---|---|
| The everyday model won't load | a smaller model (llama3.2 3B), said so | everything, with plainer words |
| Ollama down | plain-word commands, question plans by words, facts in code; restarts the runner | records, actions, alarms, the safety floor |
| A specialist's model unavailable | the next eligible, marked "not inspected" or "not passing"; or the calculators' own sentences | figure answers from code |
| A model's reply unreadable (bad JSON, cut off) | one retry with a smaller ask, then the computed-only answer | — |
| A number that doesn't trace | sent back once, then the calculators' sentences replace it (exists) | — |
| Embedding model gone | word search, said so (exists in `meaning.py`) | recall by words |
| Vision model gone | "I can't look at pictures right now" | everything else |
| Speech engine gone | the screen and typing | everything |
| The model node gone | its classes fall back to the PC, smaller | everything |
| The phone with no PC | its own small model and records (exists) | the phone |
| A model that turns unreliable (scores drop) | removed from routing by the registry; Night School re-benches | — |

**Rule:** every degradation is said once, plainly, with what still works; nothing pretends a fallback is the full
answer.

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-INT-036 | With no model available at all, MIA shall still run plain-word commands, question plans by words, alarms, the stop and the safety floor. | Must | MVP | All | Exists | T: the suite runs with no model | DEC-0206 → 07 |
