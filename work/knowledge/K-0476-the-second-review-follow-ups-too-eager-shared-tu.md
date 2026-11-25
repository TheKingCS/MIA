---
id: K-0476
kind: lesson
title: The second review: follow-ups too eager, shared turn state, unsafe canning near misses
status: confirmed
by: claude
created: 2026-11-25T06:00:37+00:00
concerns: core/conversation_state.py, core/assistant_actions.py, core/tool_loop.py, core/canning_times.py, core/question_plans.py
from: file:core/conversation_state.py, file:core/canning_times.py
---
A fresh reviewer ran code against 37472798..c743aef0. Fixed: a pronoun alone (thanks, that is good) counted as a tool follow-up and replayed the answer (now _TOOL_LEADS or a bare get ready); the follow-up note was a module dict shared across turns, devices and tests (now a ContextVar per thread and turn, carried into ChatWorker with copy_context, cleared at turn end and between tests); the note rewrote every read-only question tool and the library search (now only the followed question tools); SAID_AS_IS dropped a two-part question other half and said failures as is (now failures go the usual way, repeats and sibling refusals drop, the model words without figures are kept); canning matched substrings, so sweet potatoes got potato times and corned beef corn (now whole words and a NOT_THESE near-miss list), and a bare number like 921 or 2015 overrode the town elevation (bare_feet only without one); solar follow-ups read the earlier figures first; the time plan lost its own example; rent, fish and pressure triggers caught other questions; may read as May. Live through the whole turn also found: plan answers starting with Dungeon (the protocol word) and a copied humor example line, both now stripped in code; a thank-you reaching a plan (THANKS); I burn 4 cords a winter now kept in code.
