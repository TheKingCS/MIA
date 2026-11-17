# MIA OS: action contracts and deterministic execution (Prompt 08 §10; DEC-0213)

*Claude (Opus), 2026-11-17. Planning only.*

## 1. The contract (exists: `core/actions.py`)

| Part | Does | Deterministic |
|---|---|---|
| `ActionType(kind, label, params, describe, execute, child_ok, rejected)` | one kind of change | code |
| `describe(context, params)` | checks it can be done; the sentence he approves | code |
| `execute(context, params)` | does it through the store's own method | code |
| Undo | the store's file before and after (`undo_log`, `change_history`) | code |
| Effects | reach (records, device, system, outside) and reversibility (`action_effects`) | code |
| Tier | in the manifest; checked by `grants.require` | code |
| Proposal | who proposed (person or MIA), when, for whom; expires in a day | code |

**What a model contributes:** the kind and the parameters, as a proposal. Everything else is code. A model's text
never becomes a parameter that changes what `describe` showed: an approved card is pinned to the exact parameters it
showed (UI-7 review fix).

## 2. Rules for new kinds (MIA OS)

1. A new kind declares its effects; an outward, system or irreversible kind is at least `act_with_approval`
   (test_action_effects' sweep).
2. A kind that can't be undone says so on its card, and has a compensation where one exists (refund, a correcting
   entry).
3. Idempotent where possible: running an approved proposal twice changes nothing the second time.
4. A kind holding something open while it waits (a browser step) releases it on "no" (`rejected`).

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-AGT-013 | An approved card shall execute exactly the parameters it showed; any change makes a new card. | Must | MVP | All | Exists | T | DEC-0213 → 08 |
| REQ-AGT-014 | Running the same approved proposal twice shall change nothing the second time. | Should | R1 | All | Partial (proposals execute once) | T | DEC-0213 → 08 |
