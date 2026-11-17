---
id: K-0292
kind: test-procedure
title: Flash attention and an 8-bit KV cache on Ollama: measured before and after
status: confirmed
by: claude
created: 2026-11-17T13:40:07+00:00
concerns: docs/HARDWARE.md, core/llm_manager.py, core/self_repair.py
from: dec:DEC-0204
---
What: a second ollama serve on port 11435 with OLLAMA_FLASH_ATTENTION=1 and OLLAMA_KV_CACHE_TYPE=q8_0 set only in its own environment, against the normal server, same model, num_ctx 32768, temperature 0, seed 7, three prompts (short, a 9,653-token context, a little arithmetic). Results on the RX 7900 XTX: qwen2.5:32b writing 13.3/9.0/13.1 to 29.3/19.8/28.8 tokens/s and reading up to 2.5x, identical answers (at 32k it had spilled out of the 24 GB; size_vram 24.36 GB); qwen2.5:14b memory 15.31 to 12.29 GB, writing 73.5/61.5/72.6 to 69.3/59.5/69.4, two answers identical, one reworded. Applied as his user variables and Ollama restarted (12.29 GB confirmed live).
Why this way: a second server measures without touching his settings, and only the bench decides. Note that MIA's own restart of Ollama (LLMManager._wake_local) inherits MIA's environment, so a MIA started before the variables were set would start Ollama without them; a fresh login has them.
