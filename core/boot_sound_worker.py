"""
core.boot_sound_worker
=========================

Plays the boot sound off the GUI thread — same reasoning as
core/tts_worker.py: `VoiceManager.play()`'s `sd.wait()` blocks for the
whole sound's duration, which would otherwise freeze
core/application.py's own `QTimer`-chained boot steps for that long.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QThread

from core.voice_manager import VoiceManager


class BootSoundWorker(QThread):
    """Plays a pre-generated boot sound .wav file; fire-and-forget (no result signal)."""

    def __init__(self, voice: VoiceManager, wav_path: Path) -> None:
        """Keeps the voice manager and the boot sound to play."""
        super().__init__()
        self._voice = voice
        self._wav_path = wav_path

    def run(self) -> None:
        """Plays the boot sound (on the worker's thread, so boot isn't held up)."""
        self._voice.play(self._wav_path)
