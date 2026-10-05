# H-0011: ChatGPT decisions on Q-0001, Q-0002 and DEC-0014
- From: chatgpt · To: zac, claude, muse · Date: 2026-10-05
- Related: Q-0001, Q-0002, DEC-0014, H-0010

## Context
ChatGPT's decision text on the three items Muse surfaced from H-0010. Relayed by Zac in chat; per the approval channel (COLLABORATION.md), Zac pasting ChatGPT's text is his approval. Filed verbatim.

## What's needed
Record the three approvals in docs/QUESTIONS.md and docs/DECISIONS.md:

**1. Q-0001 — Non-punitive missions. APPROVED.**
Missed daily mission: streak resets; miss is recorded; no XP loss; no stat damage; no punishment; recovery is always possible. MIA rewards progress, not punishes imperfection. This is now a core behavioral rule, not merely a game-balance choice.

**2. Q-0002 — Child safety-floor notification. APPROVED, with one refinement.**
Policy: safety-floor event triggers the immediate child response; parent/guardian is notified; notification contains the minimum necessary information; child is told transparently that escalation may occur; escalation is deterministic and handled by code, not decided by the LLM; the event is auditable; ordinary conversations/journals remain private.
Additional guardrail: the configured parent/guardian should not automatically be treated as safe in every circumstance. The safety architecture should eventually account for cases where the guardian is unavailable, implicated in the danger, or otherwise inappropriate as the sole escalation path. That can be designed separately; it should not block the current safety-floor implementation.

**3. DEC-0014 — Witness Principle extension. APPROVED. Strongly recommended.**
Add: "MIA does not punish the user for being human."
Longer principle: "MIA witnesses what happened, celebrates earned progress, helps the user recover from setbacks, and does not punish the user for being human."
This becomes a design guardrail for future missions, streaks, XP, notifications, proactive behavior, and gamification. If a future feature makes MIA feel more like a source of guilt or pressure than a supportive second brain, it should be reconsidered.

**Final direction:** all three approved. Claude can close Q-0001, record Q-0002 as approved policy and begin implementation planning, extend DEC-0014, and continue Phase 2 without waiting on these decisions. Phase 2 direction remains approved. Do not web-ify modules merely for the sake of web-ifying them; build the shared experience layer where it genuinely improves MIA, preserving the existing working system until its replacement is demonstrably better.

## Constraints
- ChatGPT does not approve decisions; Zac does. This handoff is filed because Zac relayed it as his approval.

## Acceptance criteria
- Q-0001 CLOSED, Q-0002 recorded as approved policy, DEC-0014 extended — all marked approved by zac, 2026-10-05.
