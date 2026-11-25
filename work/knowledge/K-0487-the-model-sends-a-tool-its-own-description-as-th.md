---
id: K-0487
kind: debugging
title: The model sends a tool its own description as the question
status: confirmed
by: claude
created: 2026-11-25T12:30:59+00:00
concerns: core/tool_loop.py, core/canning_times.py, core/assistant_actions.py
from: commit:2d9d8b77
---
Through the whole turn, qwen2.5:14b called canning_time with question set to the tool description instead of his words, so a food in the USDA table (green beans) was refused. A tool whose one detail is his question names it as prompt_arg; core/tool_loop.his_words now gives that field his own words (or this turn follow-up question from conversation_state.turn_follow_up) on the model path too, not only in direct_lookup. A new calculator that reads his question should set prompt_arg.
