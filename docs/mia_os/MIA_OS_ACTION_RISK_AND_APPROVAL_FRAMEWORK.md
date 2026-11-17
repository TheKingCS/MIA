# MIA OS: action risk and approval (Prompt 13 §7; DEC-0250)

*Claude (Opus), 2026-11-18. Planning only. Risk classes: DEC-0216; tiers: DEC-0156.*

| Tier | Example | Needs |
|---|---|---|
| observe | read his calendar | nothing |
| suggest | offer a note to keep | his yes when he wants it |
| act_within_grant | add an item to a list he asked for; a kind he approved From Now On | his request or a grant; undo |
| act_with_approval | pay a bill, delete a file, merge her code | a card each time |
| never | send money by herself, publish, send an email | not possible by her |

**Reach and reversibility** (`core/action_effects.py`) set the least tier: outside, irreversible, money, other people
or physical effect → approval every time; the never-grantable list (money, messages, publishing, deletion outside
undo, system changes).

**An approval is bound** (DEC-0250, against replay): to the proposal's id, its exact parameters (a hash of what the
card showed), the person who approved and a short life; executed once; a changed parameter needs a new card. Today a
proposal is approved by id, executed once and expires; the parameter hash is to add.

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-SEC-016 | An approval shall be bound to one proposal, the exact parameters its card showed and the person, used once and expiring; anything changed needs a new card. | Must | MVP | All | Partial (id, once, expiry) | T: replay tests | DEC-0250 → 13 |
| REQ-SEC-017 | Kinds that move money, send messages, publish, delete outside undo or change the system shall never be grantable. | Must | MVP | All | Exists | T | DEC-0215 → 13 |
