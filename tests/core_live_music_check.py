"""
tests.core_live_music_check
==============================

Real-hardware verification for core.music_manager.MusicManager's
playback path — NOT a pytest test (no `test_` prefix), same reason as
tests/core_live_voice_check.py: this needs a real, live Qt Multimedia
backend (QMediaPlayer/QAudioOutput actually decoding and advancing
real wall-clock playback position), which tests/test_music_manager.py
deliberately fakes out to stay Qt-free — see that file's own docstring
for why. Unlike core_live_voice_check.py, this needs no Ollama/LLM at
all — it's purely about the audio backend, not tool-calling.

Synthesizes a real short WAV with real mutagen-written ID3 tags,
scans it into a real MusicManager, then drives a full play -> pause ->
resume -> seek -> set_volume -> stop round trip against the real
QMediaPlayer/QAudioOutput pipeline, asserting real position advances
in real wall-clock time (not just that methods return without
raising). This is what actually proves the "libpulse/PortAudio no
longer blocked" finding (see core/music_manager.py's module docstring)
holds for real playback, not just device construction.

Run with: `python tests/core_live_music_check.py`
"""

from __future__ import annotations

import struct
import sys
import tempfile
import time
import wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

_TEMP_DATA_DIR = Path(tempfile.mkdtemp(prefix="mia_core_music_check_"))
_LIBRARY_DIR = _TEMP_DATA_DIR / "library"

import core.music_manager as music_manager_module

# Same isolation rule as every other scratch/verification script in
# this project: never let a manual check touch the developer's real
# data/*.json.
music_manager_module._DATA_DIR = _TEMP_DATA_DIR
music_manager_module._TRACKS_FILE = _TEMP_DATA_DIR / "music_tracks.json"
music_manager_module._PLAYLISTS_FILE = _TEMP_DATA_DIR / "music_playlists.json"

from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QApplication

from core.app_context import AppContext
from core.config_manager import ConfigManager
from core.event_bus import EventBus
from core.music_manager import MusicManager


def _write_tagged_wav(path: Path, seconds: float, title: str, artist: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame_count = int(44100 * seconds)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(44100)
        w.writeframes(struct.pack("<" + "h" * frame_count, *([1000] * frame_count)))

    from mutagen.id3 import TIT2, TPE1
    from mutagen.wave import WAVE

    audio = WAVE(str(path))
    audio.add_tags()
    audio.tags.add(TIT2(encoding=3, text=[title]))
    audio.tags.add(TPE1(encoding=3, text=[artist]))
    audio.save()

    old_time = time.time() - 60  # outside scan_library()'s quiet-seconds window
    os.utime(path, (old_time, old_time))


def _pump(seconds: float) -> None:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        QCoreApplication.processEvents()
        time.sleep(0.05)


def main() -> int:
    app = QApplication.instance() or QApplication([])

    context = AppContext(config=ConfigManager(), events=EventBus())
    context.music = MusicManager(context)
    context.config.set("music.library_root_path", str(_LIBRARY_DIR))

    wav_path = _LIBRARY_DIR / "tone.wav"
    _write_tagged_wav(wav_path, seconds=3.0, title="Live Check Tone", artist="MIA Check")

    print("=== Scanning library ===")
    result = context.music.scan_library()
    print(result)
    if result.added != 1:
        print("FAIL: expected exactly 1 track to be indexed.")
        return 1

    track = context.music.all_tracks()[0]
    print(f"Indexed: {track.title} — {track.artist} ({track.duration_seconds:.1f}s)")

    print("\n=== Playing ===")
    if not context.music.play_track(track.track_id):
        print("FAIL: play_track() returned False.")
        return 1
    _pump(0.6)
    playing = context.music.now_playing()
    print(playing)
    if not (playing and playing.is_playing and playing.position_seconds > 0):
        print("FAIL: expected real playback with advancing position.")
        return 1

    print("\n=== Pausing ===")
    context.music.pause()
    _pump(0.2)
    paused_position = context.music.now_playing().position_seconds
    _pump(0.4)
    still_paused = context.music.now_playing()
    print(still_paused)
    if still_paused.is_playing or still_paused.position_seconds != paused_position:
        print("FAIL: expected position to hold steady while paused.")
        return 1

    print("\n=== Resuming ===")
    context.music.resume()
    _pump(0.4)
    resumed = context.music.now_playing()
    print(resumed)
    if not (resumed.is_playing and resumed.position_seconds > paused_position):
        print("FAIL: expected position to advance again after resume.")
        return 1

    print("\n=== Seeking ===")
    context.music.seek(2.5)
    _pump(0.1)
    sought = context.music.now_playing()
    print(sought)
    if abs(sought.position_seconds - 2.5) > 0.3:
        print("FAIL: expected position near 2.5s after seek.")
        return 1

    print("\n=== Volume ===")
    context.music.set_volume(42)
    volume_now = context.music.now_playing().volume_percent
    print(f"volume_percent = {volume_now}")
    if volume_now != 42:
        print("FAIL: expected volume_percent == 42.")
        return 1

    print("\n=== Stopping ===")
    context.music.stop()
    if context.music.now_playing() is not None:
        print("FAIL: expected now_playing() to be None after stop().")
        return 1

    print("\nALL CHECKS PASSED — real QtMultimedia playback confirmed working in this environment.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
