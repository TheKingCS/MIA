# MIA OS: autonomy levels and approvals (Prompt 08 §11; DEC-0215)

*Claude (Opus), 2026-11-17. Planning only. Built on DEC-0181 (approved) and DEC-0156.*

## 1. The tiers (exist) and the handoffs' levels

| Tier (`core/grants.py`) | Meaning | Prompt 25's level |
|---|---|---|
| observe | read, answer | 1 Think |
| suggest | propose for him to press | 1 Think |
| act_within_grant | do it, if a grant covers it; else ask | 2 Create, 3 Modify (inside records) |
| act_with_approval | ask every time | 4 Act |
| never | only he does it | 5 High-impact (some) |

## 2. Grants: how autonomy grows

A grant exists only as **a learned taught skill** or **a published workflow** (`grants.standing`), listed in one place
and taken back with `grant.take_back`. Nothing MIA reads can create one.

**Approve Once or Approve From Now On (Zac, 2026-11-17, Q-73):** every card where a grant is allowed has both buttons; the second makes a standing grant for that kind, shown in his grants list and taken back there. Not on cards for money, messages, publishing, deletion outside undo, system changes or any kind tiered never.

**The trust ladder (the reminder):** when he has approved the same kind, with the same shape of parameters, several
times without changing it (say five), MIA *offers* to make it standing: "You've approved marking utility bills paid
five times as I proposed them. Want me to just do those, with an Undo?" He says yes or no. MIA never self-promotes,
and a grant lapses after 90 days unused (REQ-AUT-009).

**What can't be granted at all:** paying or buying, sending messages, publishing, deleting outside undo, system
changes, anything tiered `never`.

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-AGT-015 | A standing grant shall come only from his yes (Approve From Now On on a card, or accepting an offer made with the evidence), never created by MIA. | Must | R1 | All | Partial (Approve From Now On built 2026-11-17, `core/kind_grants.py`; the evidence offer New) | T | DEC-0215 → 08 |
| REQ-AGT-016 | Paying, buying, sending, publishing, deleting outside undo and system changes shall never be grantable. | Must | MVP | All | Exists (tiers) | T: the grants sweep | DEC-0215, DEC-0181 → 08 |
