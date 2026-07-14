"""
core.tts_worker
==================

Runs `VoiceManager.synthesize()` + `.play()` off the GUI thread —
docs/ROADMAP.md milestone 5.3. Same reasoning as `core/chat_worker.py`:
`play()`'s `sd.wait()` blocks for the full duration of the spoken
reply, which scales with reply length and would freeze the GUI thread
for that whole time otherwise.

Moved here from `modules/assistant/tts_worker.py` alongside
`core/chat_worker.py` (2026-07-14 aesthetic pass part 4) — see that
module's docstring for why both had to move out of `modules/assistant/`
once `gui/character_panel.py` needed them too.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QThread

from core.voice_manager import VoiceManager


class TTSWorker(QThread):
    """Synthesizes `text` to `output_path` and plays it back; fire-and-forget (no result signal)."""

    def __init__(self, voice: VoiceManager, text: str, output_path: Path) -> None:
        super().__init__()
        self._voice = voice
        self._text = text
        self._output_path = output_path

    def run(self) -> None:
        wav_path = self._voice.synthesize(self._text, self._output_path)
        if wav_path is not None:
            self._voice.play(wav_path)
