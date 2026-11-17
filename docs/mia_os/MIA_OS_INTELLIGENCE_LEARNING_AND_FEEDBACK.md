# MIA OS: learning and feedback (Prompt 07 §15; DEC-0212)

*Claude (Opus), 2026-11-17. Planning only.*

## 1. Three kinds of learning, kept apart

| Kind | What changes | How | Approval |
|---|---|---|---|
| **Remembering** | facts about him, his preferences | `user_memory_manager`, `life_notes` ("keep it"), answer style picks | his words; reviewable and deletable |
| **Adapting behaviour** | routing, study priority, message pacing, templates, the model chosen per specialist, bench re-runs | code from evidence (ratings, corrections, loops, bench) | none needed; undoable; logged (DEC-0199 Q-60) |
| **Changing weights** | a model of her own (the router, a discipline adapter) | `core/model_forge.py`: trained, benched against the one it replaces, inspected by Claude | Claude's pass (DEC-0200, code covered too) |

## 2. Rules

1. **No fine-tuning on his private data** (journal, conversations, health, money) without his explicit yes for that
   dataset (Q-72).
2. **Nothing learns its own permissions, identity or safety rules** (DEC-0156, DEC-0199).
3. **A learned change says why:** each comes with the evidence that triggered it, and can be undone.
4. **Derived until confirmed:** a model-written note stays *derived* until he confirms it (the specialists' rule).

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-INT-029 | Remembering, adapting behaviour and changing weights shall be separate mechanisms with their own approval rules. | Must | R1 | All | Partial | T | DEC-0212 → 07 |
| REQ-INT-030 | No model shall be trained on his private records without his yes for that dataset. | Must | MVP | All | Exists (no such training) | T: the forge refuses an unapproved dataset | DEC-0212 → 07, 13 |
