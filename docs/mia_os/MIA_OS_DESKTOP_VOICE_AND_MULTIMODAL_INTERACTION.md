# MIA OS: voice and multimodal on the desktop (Prompt 10 §16)

*Claude (Opus), 2026-11-17. Planning only. The pipeline is Prompt 07's (DEC-0211).*

| Control | How | Exists |
|---|---|---|
| Push to talk | the orb, or a key held (Meta+Space) | yes (orb) |
| Continuous conversation | after her reply, listening again for a few seconds | partial |
| Wake word | later, measured (Q-81) | no |
| Interrupt her | speak or press while she talks | partial |
| Mute, end, disable sensors | the status strip's mic and camera icons | new |
| Choose devices | KDE's sound settings; a picker in Talk | partial |
| Camera, a photo | Look (`sight`), on his press | yes |
| Screen context | the screencast portal, his pick (§ conversational interface) | new |

**Sensor state is always visible:** the mic icon lit while listening, the camera icon while it's on, in her status
strip and in KDE's own indicators (PipeWire shows which app uses them). Off means off: the stream closed.

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-DSK-025 | Whenever the microphone or camera is in use by MIA, the shell shall show it, and one press shall close the stream. | Must | MVP | All | Partial | T | DEC-0211 → 10, 13 |
