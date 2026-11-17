# MIA OS: voice and continuous conversation (Prompt 07 §12; DEC-0211)

*Claude (Opus), 2026-11-17. Planning only. Conversation mode's own plan: `docs/CONVERSATION_MODE_PLAN.md`.*

## 1. What exists

`core/voice_manager.py`: `STTBackend` and `TTSBackend` interfaces; Vosk (offline, small, CPU) for speech in; Kokoro-82M
through kokoro-onnx (offline, 24 kHz) for her voice, with `core/voice_catalog.py`'s voices and an "AI voice" effect;
`core/voice_loop.py` (push-to-talk and the turn), the web's voice, the glasses through the phone. "Stop" and "hold on"
cut her speech in code (`core/stop.py`).

## 2. Proposed

| Piece | Now | Proposed | Evidence | Why |
|---|---|---|---|---|
| Speech in, PC | Vosk | measure **whisper.cpp** (Vulkan or ROCm 7.2) on his voice; switch if it's clearly more accurate at acceptable speed | whisper.cpp on AMD: ROCm 7.2 and Vulkan close; faster-whisper is mainly an Nvidia path (2026 write-ups) | accuracy on names and technical words |
| Speech in, phone and Pi | Vosk | Vosk (small, offline) | exists | runs on small hardware |
| Her voice | Kokoro (ONNX, CPU) | keep; on Linux, ONNX Runtime's MIGraphX provider replaces the deprecated ROCm one (ROCm 7.1+) if GPU speed is ever needed | AMD's notes | fast enough on CPU today |
| Turn-taking | push-to-talk; conversation mode planned | streaming partials to start thinking early; endpointing by silence | the conversation plan | quicker replies |
| Barge-in | "stop" cuts speech | any speech while she talks lowers her voice and listens (echo-cancelled through PipeWire on Linux) | — | natural conversation |
| Who's speaking | DEC-0163 | **not planned** (Zac, 2026-11-17: "not too concerned about MIA knowing who is talking"; MIA is for him alone, DEC-0119) | — | — |

**Rules:** audio never leaves his devices; a recording is kept only when he asks; the wake word stays local.

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-INT-022 | Speech recognition and synthesis shall run on his own devices, with an offline path on every device. | Must | MVP | All | Exists | T | DEC-0211 → 07 |
| REQ-INT-023 | Speaking while she talks shall lower her voice and let him be heard; "stop" cuts her off at once. | Should | R1 | PC | Partial (stop) | M | DEC-0211 → 07 |
| REQ-INT-024 | A change of speech engine shall be made only after measuring word accuracy on his own recorded phrases. | Must | R1 | PC | New | M | DEC-0211 → 07 |
