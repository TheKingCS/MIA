---
id: K-0203
kind: implementation
title: The store lock is let go while the model thinks
status: confirmed
by: claude
created: 2026-11-10T13:35:38+00:00
concerns: core/store_lock.py, core/llm_manager.py, server/app.py, core/application.py
from: commit:3a4076af, commit:bfc18243, file:core/store_lock.py
---
core/store_lock.py: StoreLock is a plain lock that records, per thread, that it's held; released() lets go of every StoreLock the thread holds for a block and takes them back in order. LLMManager._ask wraps every model call in it, so a turn holds the server's lock only while it reads or changes stores. A per-conversation lock (conversation_lock) keeps one conversation's turns in order. Not streamed: MIA's guards check the finished answer, so streaming raw words would show text they would change. The lock is context.store_lock, shared with the desktop's timers, which try it without waiting and skip a tick when it's taken (MIAApplication._while_stores_free).
