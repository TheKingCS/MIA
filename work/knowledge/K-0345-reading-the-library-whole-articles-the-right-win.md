---
id: K-0345
kind: lesson
title: Reading the library: whole articles, the right window, and figures held to the text
status: confirmed
by: claude
created: 2026-11-23T00:17:38+00:00
concerns: core/reference_reader.py, core/tool_loop.py, core/offline_library.py, core/main_thread.py
from: task:T-0060
---
Zac (2026-11-22): her talk about the references must be natural but factual. Tried live on qwen2.5:14b with the water pack, four things went wrong, each fixed: (1) search_all_packs gave each article's first 500 characters, rarely where the answer is: core/reference_reader.py reads the best articles whole and keeps the window where the question's words gather. (2) The tool loop treated look_up_offline as a change (its name doesn't start like a lookup) and answered without it: it's in main_thread.READ_ONLY_DESPITE_NAME. (3) The model answered how-to questions from memory without calling the tool (5.25%, 2 drops per liter: close to real guidance, but not from the text): tool_loop._read_first runs the look-up in code when only the library's tools were offered. (4) Even reading, it added remembered figures ('15 minutes'): library results are held to their figures strictly (small numbers too, list numbers aside), the retry names them, and what still states one loses just those sentences (without_figures). Also: the loop cut results to 1,500 characters, so library results get 7,000; a ref holding ')' broke at a parenthesis, so refs go on their own line.
