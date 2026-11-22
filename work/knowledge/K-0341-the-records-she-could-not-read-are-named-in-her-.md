---
id: K-0341
kind: implementation
title: The records she could not read are named in her answers
status: confirmed
by: claude
created: 2026-11-22T18:43:44+00:00
concerns: core/data_recovery.py, core/assistant_chat.py
from: task:FW-12
---
REQ-FUN-221 (FW-12). core/data_recovery.notify_data_corruption, which every store calls when its file won't load (it is reset to empty and set aside), now also keeps the file name for the run (unreadable()). core/assistant_chat.build_user_context_block adds a note naming them in words (your_data.label) with the rule to say she couldn't read them and never answer as if they were empty. tests/conftest.py clears the list around every test.
