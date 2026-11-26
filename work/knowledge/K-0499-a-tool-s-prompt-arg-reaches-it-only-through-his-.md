---
id: K-0499
kind: debugging
title: A tool's prompt_arg reaches it only through HIS_WORDS_TOOLS
status: confirmed
by: claude
created: 2026-11-26T00:51:42+00:00
concerns: core/tool_loop.py
from: commit:15a34f16
---
On 2026-11-25 three guards that read his words (add_grocery_item's, set_power_load's 0 watts, list_past_conversations' yesterday) were tested by passing 'question' by hand, and passed, but never ran in a real turn: core/tool_loop.his_words fills a tool's prompt_arg only for tools in HIS_WORDS_TOOLS (and only when the model's value is empty or its own description). A new guard on his words needs the tool in HIS_WORDS_TOOLS, the field in its schema, and a test through his_words, not only the handler.
