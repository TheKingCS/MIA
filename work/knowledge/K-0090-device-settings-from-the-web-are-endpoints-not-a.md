---
id: K-0090
kind: decision
title: Device settings from the web are endpoints, not actions
status: confirmed
by: claude
created: 2026-11-08T01:58:06+00:00
concerns: core/web_backups.py, core/web_voice.py, server/app.py, web/settings.js
from: commit:c812e18, dec:DEC-0125
---
Backups (core/web_backups.py) and MIA voice (core/web_voice.py) are changed through owner-only endpoints, not the action contract. A backup passphrase must never sit in a proposal, the history or the undo log (the same rule as passwords). The voice engine is swapped in memory by VoiceManager.set_voice, so an undo that only puts config.json back would leave MIA speaking in the new voice: the page shows the current voice so the person can pick the old one again. Both are the PC owner only (person_settings._is_first_account), because they act for the whole computer. Restoring a backup stays on the PC.
