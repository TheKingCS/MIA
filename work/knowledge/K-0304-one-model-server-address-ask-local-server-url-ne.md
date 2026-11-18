---
id: K-0304
kind: implementation
title: One model-server address: ask local_server_url, never write the port
status: confirmed
by: claude
created: 2026-11-18T15:38:59+00:00
concerns: core/llm_manager.py, core/meaning.py, core/recall_index.py, core/sight.py
from: commit:f9a270c3
---
LS-08: the Ollama address is written once, core/llm_manager.DEFAULT_SERVER, and every module and tool asks local_server_url(context), which reads llm.base_url and turns localhost into 127.0.0.1 (Windows tries IPv6 first and stalls). Embeddings and vision go through OllamaBackend.embed and see. Six background writers still post their own JSON-format requests to that address because the backend doesn't take their options yet. tests/test_model_server_address.py fails on 11434 written in core, tools, gui, server or modules; os/poc's benchmark stays standalone.
