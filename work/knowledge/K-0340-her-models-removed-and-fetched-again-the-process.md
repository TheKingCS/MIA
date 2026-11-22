---
id: K-0340
kind: implementation
title: Her models removed and fetched again; the processor said
status: confirmed
by: claude
created: 2026-11-22T18:25:28+00:00
concerns: core/model_store.py, core/llm_manager.py, web/settings.js
from: task:FW-12
---
REQ-HW-014, REQ-HW-012 (FW-12). core/model_store.py talks only to the model server's API by name: installed (/api/tags), remove (DELETE /api/delete; refused for llm.model and anything not installed or not a name; the name kept in models.removed), fetch (POST /api/pull, stream false, in a thread, only a known name: llm.model, the fallbacks, a removed one; told when done). Kinds model.remove and model.fetch are act_with_approval and reach the device, compensable; the voice tools remove_ai_model and fetch_ai_model only put up a card. Settings has MIA's Models. OllamaBackend.on_gpu reads /api/ps; a fallback with 0 on the card adds 'on the processor' to the level. tests/conftest.py stubs on_gpu like installed, so no test asks the real server.
