# MIA OS: intent and goals (Prompt 08 §4)

*Claude (Opus), 2026-11-17. Planning only.*

## 1. From words to an intent (exists)

In order, in code first: the stop and the safety floor; plain-word commands; question plans matched by meaning
(`core/meaning.py`); the model choosing among tools only when those don't settle it. An intent is one of:

| Kind | Example | Becomes |
|---|---|---|
| question | "what's due this week?" | an answer from records (no change) |
| one action | "mark the electric bill paid" | one proposal on the contract |
| a goal | "get the greenhouse ready for winter" | a plan (steps across apps), or a project with needs |
| a standing wish | "every Friday, tidy the inbox" | a workflow (fixed vocabulary, standing approval by kind) |
| a skill to learn | "watch me do this" | a taught skill |
| brainstorming | "what if the hoodie had speakers?" | conversation; a team only on his yes (Q-54) |

**Ambiguity is asked about, not guessed:** a missing value is a question (the worksheet's rule); two readings get
both offered.

## 2. A goal

```json
{"goal_id": "g-12", "said": "get the greenhouse ready for winter", "project": "project:p1",
 "success": ["heater tested", "vents set to winter", "needs for winter covered"], "by": "2026-12-01",
 "plan": "step_plan:abc", "status": "active", "source": "said"}
```

A goal lives on its project (projects and missions exist); its success criteria are checkable records where
possible, his words where not.

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-AGT-001 | An intent shall be classified in code first (commands, question plans), and the model used only where code can't decide. | Must | MVP | All | Exists | T | DEC-0213 → 08 |
| REQ-AGT-002 | A goal shall carry checkable success criteria where they exist, and MIA shall say when one can't be checked. | Should | R1 | All | New | T | DEC-0218 → 08 |
| REQ-AGT-003 | A brainstorm shall never become a plan, a team or a purchase without his yes. | Must | MVP | All | Exists (DEC-0198) | T | DEC-0198 → 08 |
