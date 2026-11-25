---
id: K-0475
kind: implementation
title: Follow-ups to a tool answer bring its tools, and the lookup gets the new words in code
status: confirmed
by: claude
created: 2026-11-25T03:53:23+00:00
concerns: core/conversation_state.py, core/assistant_chat.py, core/assistant_actions.py
from: file:core/conversation_state.py, file:core/assistant_actions.py
---
core/conversation_state.followed_question finds the persons last question (last 4 messages) that brought tools when a short follow-up leads (and/what about/what if) or leans (it/that); core/assistant_chat.build_chat_request routes on both, adds a system line, and notes the turn (set_turn_follow_up). core/assistant_actions._with_follow_up then gives a read-only lookup with a question field the follow-up words (new words first, then the earlier question) when the models question leaves them out. Tried first and dropped: telling the model in the system message (ignored) and rewriting each tools question description to the words (it then picked any tool with a question field, bleach_for_water for what about tomorrow). Tools that read the first food or weight read the new one; canning_times.food_in now prefers the earliest named food. Known gap: a tool with only a day field (work outside) still loses to get_weather on what about tomorrow.
