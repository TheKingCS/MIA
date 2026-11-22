---
id: K-0339
kind: implementation
title: The microphone in use, shown, with one Stop
status: confirmed
by: claude
created: 2026-11-22T18:16:54+00:00
concerns: web/shell.js, web/guitar.js
from: task:FW-11
---
REQ-DSK-025 (FW-11). web/shell.js capture(kind, stop) registers an open microphone or camera and returns its release; drawCapture shows a fixed status pill (amber: attention, never the red of an error) with Stop, which calls every capture's own stop and clears them. voiceRecorder(onCancel) registers on start, releases on stop or cancel, and its cancel ends the recording without sending it (Talk resets its mic button). guitar.js's few-second take registers too, and Stop ends it early. The glasses page runs without the frame and shows listening on its own orb.
