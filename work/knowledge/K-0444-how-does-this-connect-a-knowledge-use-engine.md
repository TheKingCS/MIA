---
id: K-0444
kind: implementation
title: How does this connect: a knowledge-use engine
status: confirmed
by: claude
created: 2026-11-24T17:54:30+00:00
concerns: core/ual.py, core/assistant_ual_actions.py
from: dec:DEC-0165
---
Zac asked for a tool that summarizes a file, list or paragraph and explains how it connects to what we have been talking about and how to use it. Built as the UAL read action connect (core/ual.py), so every front door (web palette, phone selection, voice via do_with_this, "how does this connect", "how should I use this") gets it. The connections are found in code: records sharing the selection's key terms (_find_known, what Ctrl+K finds) and his last six messages in the active conversation (talking_about); the model is told to word what it says, how it ties to only those listed, and two or three ways to use it, never inventing a record. Nothing is saved.
