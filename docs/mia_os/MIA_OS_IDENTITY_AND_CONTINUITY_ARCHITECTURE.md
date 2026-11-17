# MIA OS: identity and continuity (Prompt 07 §8; DEC-0206)

*Claude (Opus), 2026-11-17. Planning only.*

## 1. Where MIA is

| Part of her | Lives in | Survives a model change |
|---|---|---|
| Who she is, how she speaks | `core/personality.py` (IDENTITY, CHARACTER), `docs/design/MIA_VOICE.md` | yes: every prompt takes it from there |
| What she knows about him | his stores (memories, records, history, links) | yes |
| What she decided and did | the action record, the run record, the change history, life events | yes |
| What she's learned how to do | taught skills, workflows, specialists' notes, templates | yes |
| Her judgement of facts | code (the Life State, calculators, the safety floor) | yes |
| Her phrasing on a given turn | the model of the moment | no, and it doesn't need to |

So swapping `qwen2.5:14b` for another model changes how a sentence is worded, not who answers, what she remembers or
what she decides. This is already true; DEC-0206 makes it a rule for everything new.

## 2. Rules

1. **No identity in weights.** No model is fine-tuned to "be MIA"; her character is given in the prompt from
   `personality.py`, so any capable model can carry it (the model forge trains task models, not her).
2. **No memory in a model's context alone.** Anything worth keeping is written to a store with its source, or it's
   forgotten at the end of the turn.
3. **She says which model answered** when asked ("which model are you using?" is answered from `model_registry.py`).
4. **One voice across devices:** the phone's small model, the PC's and a specialist's all take the same identity
   block; tests check a sample of replies for her voice rules (no hard-coded names, plain words).

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-INT-012 | Every prompt that speaks as MIA shall take her identity from one place, and swapping the model shall need no change to it. | Must | MVP | All | Exists (`personality.py`) | T: a sweep finds no identity text outside it | DEC-0206 → 07 |
| REQ-INT-013 | Nothing about him shall persist except through a store with its source; a model's context is never the memory of record. | Must | MVP | All | Exists | T | DEC-0206, DEC-0173 → 07 |
