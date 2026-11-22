---
id: K-0333
kind: implementation
title: The next local model, said; one model call at a time, the conversation first
status: confirmed
by: claude
created: 2026-11-22T14:29:50+00:00
concerns: core/llm_manager.py, core/model_queue.py, core/scheduler.py, tests/conftest.py
from: task:FW-12, dec:DEC-0204
---
FW-12 MVP (REQ-AI-013, REQ-HW-029, DEC-0204). LLMManager._ask_unlocked: the chosen model raising LLMUnavailableError (failed or timed out) and Ollama not waking goes to _fall_back: the first of llm.fallback_models (FALLBACK_MODELS) that OllamaBackend.installed() lists (asked at most every 5 minutes), made with with_model(); one extra try only; level becomes 'THIS COMPUTER · <model>, the smaller model' and fell_back names it. core/model_queue.slot() wraps every _ask (after the store lock is let go): one holder; the waiting call with the strongest kind (conversation, specialist, workroom, background), earliest first, goes next; a thread holding it passes through. The scheduler runs jobs under as_kind('background'). Lesson: the fallback asks the real Ollama what it has, so a test whose pretend backend failed reached Zac's real server and got a real answer; tests/conftest.py now makes OllamaBackend.installed report none.
