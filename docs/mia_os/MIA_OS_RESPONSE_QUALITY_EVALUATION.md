# MIA OS: response quality and behaviour (Prompt 09 §10; DEC-0223)

*Claude (Opus), 2026-11-17. Planning only. Evaluation sets: Prompt 07's framework.*

| Check | Where | Exists |
|---|---|---|
| Numbers in an answer trace to code | the worksheet; the facts-in-code rule | yes |
| Voice rules (plain words, no invented names, her character) | style tests, `personality.py` | partial |
| His "that's wrong", "no, I meant" | the Fix-It Log | yes |
| His thumbs | answer ratings | yes |
| His corrections to her changes | `core/corrections.py` | yes |
| Fixed evaluation sets | the golden set, the bench, conversation and recall sets (Prompt 07) | partial |
| Unsafe or out-of-character replies | the safety floor (in code), Claude's spot judging | partial |

**Behaviour problems** (nagging, repeating, over-asking) are measured by the gate's own records (dismissals, repeats)
and the loops; a rise becomes a finding, not a guess.

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-SLF-010 | A drop in any evaluation set or a rise in his corrections for a kind of answer shall open a finding with its evidence. | Should | R1 | All | Partial (loops) | T | DEC-0223 → 09 |
