# MIA OS: model routing and selection (Prompt 07 §6; DEC-0208)

*Claude (Opus), 2026-11-17. Planning only.*

## 1. Most turns need no routing

The cheapest correct path wins, in this order (all exist today): the stop and the safety floor (code); plain-word
commands (code); question plans matched by meaning (code plus an embedding); facts assembled in code and phrased by
the everyday model; tools chosen by the everyday model. Only the rest is routed.

## 2. Task classes

| Class | Example | Needs | Today's model |
|---|---|---|---|
| `chat` | conversation, phrasing facts | speed, voice, tools | everyday (`qwen2.5:14b`) |
| `tools` | choosing among her tools | tool-calling accuracy (golden set) | everyday |
| `figures` | a specialist's worksheet | picks calculators, never guesses (engineering bench) | per specialist (`specialist_models.py`) |
| `review` | checking a plan | a different family from the author | best other model on the bench |
| `vision` | Look, a document photo | images | `qwen2.5vl:7b` |
| `code` | the lab, Forge | coding (lab suite) | development tools; `qwen3-coder:30b` locally |
| `embed` | meaning, recall | vectors | `nomic-embed-text` |
| `long` | summarising a long document | context length | everyday (32k) |

## 3. The selection, in code

```
eligible = registry.models(task_class)                     # measured for this class, not retired
eligible = [m for m in eligible if m.fits(device_state)]    # memory free, path available (REQ-HW-011)
if request.personal: eligible = [m for m in eligible if m.local]
best = max(eligible, key=(passed, -guessed, score, -seconds))  # as specialist_models.choose does today
run(best); validate(reply)
on failure or a failed check: next eligible, then the computed-only answer, then "I can't right now" with why
record(model, class, outcome) → the registry's evidence
```

**What a model says about itself is never evidence.** Eligibility comes from the bench, the golden set, ratings and
inspection.

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-INT-007 | A model shall be chosen for a task class only from measured results for that class; an unmeasured model is never chosen. | Must | R1 | All | Partial (specialists) | T: an unmeasured model in the registry is skipped | DEC-0208 → 07 |
| REQ-INT-008 | Requests carrying his records shall go only to local models unless he said yes to that exact content. | Must | MVP | All | Exists (no cloud path in turns) | T | DEC-0207 → 07, 13 |
| REQ-INT-009 | Every routed request shall have a fallback chain ending in a computed answer or a plain "I can't, because…". | Must | R1 | All | Partial | T: each link failed in turn | DEC-0208 → 07 |
