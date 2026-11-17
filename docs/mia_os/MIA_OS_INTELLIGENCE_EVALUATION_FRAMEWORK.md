# MIA OS: intelligence evaluation (Prompt 07 §14)

*Claude (Opus), 2026-11-17. Planning only.*

## 1. Measures that exist (verified in the code)

| Measure | What it checks | Where |
|---|---|---|
| The golden set | right tool, right words, per model | `core/model_bench.py`, `tests/live_model_check.py` |
| The engineering bench | right figure, asked when missing, never guessed, per discipline | `core/eng_bench.py`, `work/eng_bench/` |
| Claude's inspection | a model's fitness for a specialist | `core/model_inspection.py` |
| Second-model review | a plan's soundness | `core/specialist_review.py` |
| Ratings | his thumbs on answers | `core/answer_ratings.py` |
| Corrections | his fixes to MIA's work | `core/corrections.py` |
| Loops | per-process quality over time | `core/loops.py` |
| Turn trace | what happened on each turn | `core/turn_trace.py` |

## 2. What's added

| Gap | Measure |
|---|---|
| Conversation quality | a set of his own past questions (anonymised in the repo, real on the PC) replayed per model, judged by rules (facts present, no invented numbers, voice rules) and spot-judged by Claude |
| Memory recall | known-item queries over his records: did the right record come back, did a private one never come back |
| Speech | word accuracy on his recorded phrases (REQ-INT-024) |
| Vision | a fixed set of his photos and questions |
| Regression | every change to a model, setting or prompt re-runs the relevant sets; a drop is a hold |

**Rules:** scores are counts with their sets, never adjectives; a model is judged on the tasks MIA gives it, not on
public leaderboards; what can't be measured is said as not measured.

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-INT-027 | Every model, setting or prompt change shall re-run the evaluation sets it can affect, and a lower score shall hold the change. | Must | R1 | All | Partial (bench, golden set) | T | DEC-0208, DEC-0212 → 07 |
| REQ-INT-028 | MIA shall keep evaluation sets for conversation, recall, speech and vision drawn from his own use. | Should | R1 | PC | New | M | DEC-0212 → 07 |
