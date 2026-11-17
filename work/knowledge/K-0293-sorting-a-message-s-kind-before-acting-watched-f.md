---
id: K-0293
kind: implementation
title: Sorting a message's kind before acting, watched first
status: confirmed
by: claude
created: 2026-11-17T13:43:55+00:00
concerns: core/message_kind.py, core/turn_trace.py
from: task:T-0009
---
What: core/message_kind.py (T-0009, the personality audit's P3). sort() is ordered rules over the words: follow-up (short, after her reply, or "why?"), hypothetical ("what if"), command (an opening verb, not a question), greeting as chat, feeling, frustration, humor, advice, plan, question, observation, chat. Phrases match as whole words (_has with lookarounds). The turn trace records it as `kind`; routing is unchanged.
What went wrong: a heredoc turned the regex's  into a backspace, so every phrase stopped matching and accuracy fell from 88% to 59%; the lookahead (?![a-z0-9]) replaced it, written with Python's own replace. Measured 48 of 49 on data/conversation_cases.json, a follow-up counting as a question, but the phrases were written against those cases: the traces are the real test.
