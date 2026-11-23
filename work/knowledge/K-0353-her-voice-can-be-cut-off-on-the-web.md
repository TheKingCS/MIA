---
id: K-0353
kind: implementation
title: Her voice can be cut off on the web
status: confirmed
by: claude
created: 2026-11-23T18:04:40+00:00
concerns: web/shell.js, web/assistant.js, web/welcome.js
from: commit:29396ed9
---
web/shell.js keeps one Audio per page (`speaking`); playReply stops the last one first and takes onPlay/onEnd hooks so a page's own orb follows; voiceRecorder.start, Talk's answer(), the Assistant's send() and Escape call stopSpeaking(). assistant.js and welcome.js's Hear It now play through it. The glasses page still has its own players (beatAudio): next.
