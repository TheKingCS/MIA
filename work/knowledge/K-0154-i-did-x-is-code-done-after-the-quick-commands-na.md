---
id: K-0154
kind: implementation
title: "I did X" is code-done after the quick commands; Natural Momentum reads only the history
status: confirmed
by: claude
created: 2026-11-09T01:28:36+00:00
concerns: core/did_it.py, core/momentum.py, core/communication_gate.py, core/assistant_turn.py, core/talk_it_out.py, tests/test_did_it.py, tests/test_momentum.py
from: dec:DEC-0148
---
DEC-0148, 2026-11-08. core/did_it.py answers a message that's only what he did before the model: activities split on commas, 'and' before a verb and 'then'; negatives, questions alone and vague or self-critical objects ('I did something stupid', 'made a mistake') never count. What went wrong first: (1) it ran before the quick commands and took 'finished my pull-ups' from the workout command; it now runs after them. (2) It took 'Finally paid the electric bill' from passing mentions (core/passing_mentions.py), whose offer about a kept record is better; it steps aside when detect_offer finds one. (3) 'fixed the gate' didn't meet the task 'Fix the gate' until both sides were stemmed. (4) a new gate topic needs a reason in core/message_reasons.py (a test holds it). Offers are actions done as the person (routine.log, task.done, objective.tick, routine.add), so 'undo that' works. core/momentum.py counts only real done types (never *_finished: book_finished was spam), and the gate's flow guard defers instead of dropping. pending_track and did_handled are transient Conversation fields, like pending_offer.
