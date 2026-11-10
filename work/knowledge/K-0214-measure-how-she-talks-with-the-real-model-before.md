---
id: K-0214
kind: lesson
title: Measure how she talks with the real model before and after, on the same questions
status: confirmed
by: claude
created: 2026-11-10T23:38:37+00:00
concerns: core/assistant_chat.py, core/personality.py, core/response_composer.py, tests/test_turn_harness.py
from: file:docs/CONVERSATION_REVIEW.md, file:tests/test_turn_harness.py
---
The scripted-model harness (tests/test_turn_harness.py) proves what a turn is sent and what is done with the reply; it cannot show how the real model answers. For the conversational work a scratch script asked the specification's 23 questions of qwen2.5:14b through run_assistant_turn and wrote each answer with its route, time and length, once before any change and after each round. That is what showed the cause (the help pages), showed that a first fix made her answer in lists, and showed that a rule in the system prompt is weaker than the last line the model reads (ABOUT_HER_REMINDER goes last for that reason). What worked for natural length: say what length a simple question deserves, forbid a closing question unless she wants the answer, add one short worked exchange to the examples, and let response_composer.polish drop an invitation to keep talking while keeping an offer to act (a "yes" to that does something). What did not need changing: her character lines. Count, don't judge by eye: endings on a question and median words came from a script over the two transcripts. A run takes about a minute and starts no window; it stays out of the suite because it needs the model.
