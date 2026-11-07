"""
tests.test_music_manager
===========================

Unit tests for core.music_manager. The CRUD/scan_library() section is
entirely Qt-free (matches this project's established convention — see
tests/test_avatar_manager.py monkeypatching QMediaDevices rather than
constructing a real QApplication). The playback section monkeypatches
MusicManager._ensure_player() to a lightweight fake player/audio-output
pair instead of a real QMediaPlayer/QAudioOutput — real end-to-end
playback against the actual QtMultimedia/FFmpeg backend is verified by
hand via tests/core_live_music_check.py instead (not run by pytest),
same split this codebase already uses for VoiceManager
(tests/core_live_voice_check.py).

scan_library() tests write real small audio files to tmp_path (a real
synthesized WAV with real mutagen-written ID3 tags, not a duck-typed
fake) — same "construct the real thing, don't fake the hard part"
discipline this session's Plaid SDK tests established.
"""

from __future__ import annotations

import struct
import time
import wave
from pathlib import Path

import pytest

import core.music_manager as music_manager_module
from core.app_context import AppContext
from core.config_manager import ConfigManager
from core.event_bus import EventBus
from core.music_manager import MusicManager, Playlist, Track


@pytest.fixture
def isolated_paths(tmp_path, monkeypatch):
    """Points the music store's files and its default library folder at a temporary folder, so no test reads or writes the real ones."""
    data_dir = tmp_path / "data"
    monkeypatch.setattr(music_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(music_manager_module, "_TRACKS_FILE", data_dir / "music_tracks.json")
    monkeypatch.setattr(music_manager_module, "_PLAYLISTS_FILE", data_dir / "music_playlists.json")
    # The default library folder too: on a PC with songs in music_library/ the scans read the real ones (2026-11-06).
    monkeypatch.setattr(music_manager_module, "_DEFAULT_ROOT", tmp_path / "music_library")
    return data_dir


def _make_context() -> AppContext:
    """A bare context: a config and an event bus."""
    return AppContext(config=ConfigManager(), events=EventBus())


def _make_manager(context: AppContext) -> MusicManager:
    """A music manager on the context, set as its music."""
    manager = MusicManager(context)
    context.music = manager
    return manager


def _write_wav(path: Path, seconds: float = 0.2, title: str = "", artist: str = "") -> None:
    """Writes a short mono WAV (a steady tone) at the path, with an ID3 title and artist when given."""
    path.parent.mkdir(parents=True, exist_ok=True)
    frame_count = int(44100 * seconds)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(44100)
        w.writeframes(struct.pack("<" + "h" * frame_count, *([1000] * frame_count)))

    if title or artist:
        from mutagen.id3 import TALB, TIT2, TPE1
        from mutagen.wave import WAVE

        audio = WAVE(str(path))
        audio.add_tags()
        if title:
            audio.tags.add(TIT2(encoding=3, text=[title]))
        if artist:
            audio.tags.add(TPE1(encoding=3, text=[artist]))
        audio.save()


# ------------------------------------------------------------------
# Track CRUD
# ------------------------------------------------------------------

def test_all_tracks_empty_initially(isolated_paths):
    manager = _make_manager(_make_context())
    assert manager.all_tracks() == []


def test_get_track_found_and_not_found(isolated_paths):
    manager = _make_manager(_make_context())
    manager._tracks.append(Track(track_id="t1", file_path="/x/a.mp3", title="A"))
    assert manager.get_track("t1") is not None
    assert manager.get_track("no-such-id") is None


def test_all_tracks_sorted_by_artist_album_track_title(isolated_paths):
    manager = _make_manager(_make_context())
    manager._tracks = [
        Track(track_id="t1", file_path="/a", title="Zed Song", artist="Zed"),
        Track(track_id="t2", file_path="/b", title="Alpha Song", artist="Aardvark"),
    ]
    titles = [t.title for t in manager.all_tracks()]
    assert titles == ["Alpha Song", "Zed Song"]


def test_search_tracks_matches_title_artist_or_album(isolated_paths):
    manager = _make_manager(_make_context())
    manager._tracks = [
        Track(track_id="t1", file_path="/a", title="Blue Skies", artist="Sam", album="Weather"),
        Track(track_id="t2", file_path="/b", title="Red Sun", artist="Alex", album="Colors"),
    ]
    assert [t.track_id for t in manager.search_tracks("blue")] == ["t1"]
    assert [t.track_id for t in manager.search_tracks("alex")] == ["t2"]
    assert [t.track_id for t in manager.search_tracks("colors")] == ["t2"]
    assert manager.search_tracks("") == manager.all_tracks()


def test_delete_track_removes_from_index_and_playlists_not_file(isolated_paths, tmp_path):
    manager = _make_manager(_make_context())
    real_file = tmp_path / "keep.mp3"
    real_file.write_bytes(b"not really mp3 data")
    manager._tracks.append(Track(track_id="t1", file_path=str(real_file), title="Keep Me"))
    playlist = manager.create_playlist("Favorites")
    manager.add_track_to_playlist(playlist.playlist_id, "t1")

    manager.delete_track("t1")

    assert manager.get_track("t1") is None
    assert real_file.exists()  # the real file itself is never touched
    assert manager.tracks_for_playlist(playlist.playlist_id) == []


# ------------------------------------------------------------------
# Playlist CRUD
# ------------------------------------------------------------------

def test_create_rename_delete_playlist(isolated_paths):
    manager = _make_manager(_make_context())
    playlist = manager.create_playlist("Road Trip")
    assert manager.get_playlist(playlist.playlist_id).name == "Road Trip"

    manager.rename_playlist(playlist.playlist_id, "Road Trip 2026")
    assert manager.get_playlist(playlist.playlist_id).name == "Road Trip 2026"

    manager.delete_playlist(playlist.playlist_id)
    assert manager.get_playlist(playlist.playlist_id) is None


def test_all_playlists_sorted_by_name(isolated_paths):
    manager = _make_manager(_make_context())
    manager.create_playlist("Zeta")
    manager.create_playlist("Alpha")
    assert [p.name for p in manager.all_playlists()] == ["Alpha", "Zeta"]


def test_add_and_remove_track_from_playlist(isolated_paths):
    manager = _make_manager(_make_context())
    manager._tracks.append(Track(track_id="t1", file_path="/a", title="A"))
    playlist = manager.create_playlist("Mix")

    assert manager.add_track_to_playlist(playlist.playlist_id, "t1") is True
    assert manager.add_track_to_playlist(playlist.playlist_id, "t1") is False  # already present
    assert [t.track_id for t in manager.tracks_for_playlist(playlist.playlist_id)] == ["t1"]

    assert manager.remove_track_from_playlist(playlist.playlist_id, "t1") is True
    assert manager.remove_track_from_playlist(playlist.playlist_id, "t1") is False
    assert manager.tracks_for_playlist(playlist.playlist_id) == []


def test_tracks_for_playlist_silently_skips_dangling_ids(isolated_paths):
    manager = _make_manager(_make_context())
    playlist = manager.create_playlist("Mix")
    playlist.track_ids.append("no-such-track")
    manager._save_playlists()
    assert manager.tracks_for_playlist(playlist.playlist_id) == []


def test_playlist_from_dict_backward_compatible_with_old_shape():
    playlist = Playlist.from_dict({"playlist_id": "p1", "name": "Old Shape"})
    assert playlist.track_ids == []


def test_track_from_dict_backward_compatible_with_old_shape():
    track = Track.from_dict({"track_id": "t1", "file_path": "/a", "title": "A"})
    assert track.artist == ""
    assert track.track_number is None


# ------------------------------------------------------------------
# scan_library() — real synthesized WAV files, real mutagen tags
# ------------------------------------------------------------------

def _configure_root(context: AppContext, root: Path) -> None:
    """Points the music library at a folder."""
    context.config.set("music.library_root_path", str(root))


def test_scan_library_missing_root_returns_root_missing_without_touching_index(isolated_paths, tmp_path):
    context = _make_context()
    manager = _make_manager(context)
    manager._tracks.append(Track(track_id="t1", file_path="/already/indexed.mp3", title="Existing"))
    _configure_root(context, tmp_path / "does_not_exist")

    result = manager.scan_library()

    assert result.root_missing is True
    assert result.added == result.updated == result.removed == 0
    assert manager.get_track("t1") is not None  # index untouched


def test_scan_library_indexes_new_file_with_real_tags(isolated_paths, tmp_path):
    context = _make_context()
    manager = _make_manager(context)
    root = tmp_path / "library"
    _write_wav(root / "song.wav", title="Test Tone", artist="MIA Test")
    _configure_root(context, root)
    # back-date the file so it's outside the "still mid-copy" quiet window
    old_time = time.time() - 60
    import os
    os.utime(root / "song.wav", (old_time, old_time))

    result = manager.scan_library()

    assert result.added == 1
    assert result.removed == 0
    tracks = manager.all_tracks()
    assert len(tracks) == 1
    assert tracks[0].title == "Test Tone"
    assert tracks[0].artist == "MIA Test"
    assert tracks[0].duration_seconds > 0


def test_scan_library_skips_hot_just_written_file(isolated_paths, tmp_path):
    context = _make_context()
    manager = _make_manager(context)
    root = tmp_path / "library"
    _write_wav(root / "song.wav", title="Fresh")
    _configure_root(context, root)
    # deliberately NOT back-dated — still "hot"

    result = manager.scan_library()

    assert result.added == 0
    assert manager.all_tracks() == []


def test_scan_library_unchanged_file_is_not_rescanned(isolated_paths, tmp_path):
    context = _make_context()
    manager = _make_manager(context)
    root = tmp_path / "library"
    path = root / "song.wav"
    _write_wav(path, title="Original")
    _configure_root(context, root)
    import os
    old_time = time.time() - 60
    os.utime(path, (old_time, old_time))

    first = manager.scan_library()
    assert first.added == 1
    first_scanned_at = manager.all_tracks()[0].last_scanned_at

    second = manager.scan_library()
    assert second.added == 0
    assert second.unchanged == 1
    assert manager.all_tracks()[0].last_scanned_at == first_scanned_at


def test_scan_library_modified_file_updates_but_keeps_track_id(isolated_paths, tmp_path):
    context = _make_context()
    manager = _make_manager(context)
    root = tmp_path / "library"
    path = root / "song.wav"
    _write_wav(path, title="Original")
    _configure_root(context, root)
    import os
    old_time = time.time() - 60
    os.utime(path, (old_time, old_time))
    manager.scan_library()
    original_id = manager.all_tracks()[0].track_id

    # Modify the file (longer duration -> different size/mtime) then re-scan
    _write_wav(path, seconds=0.5, title="Updated Title")
    os.utime(path, (old_time - 5, old_time - 5))  # still outside the quiet window, but genuinely different mtime

    result = manager.scan_library()

    assert result.updated == 1
    tracks = manager.all_tracks()
    assert len(tracks) == 1
    assert tracks[0].track_id == original_id
    assert tracks[0].title == "Updated Title"


def test_scan_library_prunes_deleted_file_and_orphans_playlist_entry(isolated_paths, tmp_path):
    context = _make_context()
    manager = _make_manager(context)
    root = tmp_path / "library"
    path = root / "song.wav"
    _write_wav(path, title="Gone Soon")
    _configure_root(context, root)
    import os
    old_time = time.time() - 60
    os.utime(path, (old_time, old_time))
    manager.scan_library()
    track_id = manager.all_tracks()[0].track_id
    playlist = manager.create_playlist("Mix")
    playlist.track_ids.append(track_id)
    manager._save_playlists()

    path.unlink()
    result = manager.scan_library()

    assert result.removed == 1
    assert manager.get_track(track_id) is None
    # track_ids itself is left alone (not mutated) — tracks_for_playlist resolves it away instead
    assert track_id in manager.get_playlist(playlist.playlist_id).track_ids
    assert manager.tracks_for_playlist(playlist.playlist_id) == []


# ------------------------------------------------------------------
# Playback — MusicManager._ensure_player() monkeypatched to a fake
# player/audio-output pair, no real QApplication needed
# ------------------------------------------------------------------

class _FakeAudioOutput:
    """Stands in for Qt's audio output: just a volume to set and read."""
    def __init__(self):
        """Starts at 0.7 volume."""
        self._volume = 0.7

    def setVolume(self, value: float) -> None:
        """Sets the volume."""
        self._volume = value

    def volume(self) -> float:
        """The volume set."""
        return self._volume


class _FakePlayer:
    """Stands in for Qt's media player: a source, a play state, a position and a 200-second duration, with no sound."""
    def __init__(self):
        """Stopped at 0 with nothing loaded."""
        self.source = None
        self._state = "stopped"
        self._position_ms = 0
        self._duration_ms = 200_000

    def setSource(self, url) -> None:
        """Loads a source."""
        self.source = url

    def play(self) -> None:
        """Playing."""
        self._state = "playing"

    def pause(self) -> None:
        """Paused."""
        self._state = "paused"

    def stop(self) -> None:
        """Stopped, back to 0."""
        self._state = "stopped"
        self._position_ms = 0

    def setPosition(self, ms: int) -> None:
        """Moves to a position (ms)."""
        self._position_ms = ms

    def position(self) -> int:
        """The position (ms)."""
        return self._position_ms

    def duration(self) -> int:
        """The duration (ms)."""
        return self._duration_ms

    def playbackState(self):
        """The state as Qt's own PlaybackState."""
        from PySide6.QtMultimedia import QMediaPlayer

        return {
            "playing": QMediaPlayer.PlaybackState.PlayingState,
            "paused": QMediaPlayer.PlaybackState.PausedState,
            "stopped": QMediaPlayer.PlaybackState.StoppedState,
        }[self._state]


def _install_fake_player(manager: MusicManager) -> _FakePlayer:
    """Gives the manager the fake player and audio output instead of Qt's. Returns the player."""
    fake_player = _FakePlayer()
    fake_audio = _FakeAudioOutput()
    manager._player = fake_player
    manager._audio_output = fake_audio
    manager._ensure_player = lambda: fake_player
    return fake_player


def _make_manager_with_fake_player(tmp_path) -> tuple[MusicManager, Path]:
    """A manager with one real (fake-content) track, t1, and the fake player. Returns it and the file."""
    manager = _make_manager(_make_context())
    real_file = tmp_path / "a.mp3"
    real_file.write_bytes(b"fake audio bytes")
    manager._tracks.append(Track(track_id="t1", file_path=str(real_file), title="Song A"))
    _install_fake_player(manager)
    return manager, real_file


def test_play_track_missing_file_returns_false(isolated_paths, tmp_path):
    manager = _make_manager(_make_context())
    manager._tracks.append(Track(track_id="t1", file_path=str(tmp_path / "missing.mp3"), title="Gone"))
    _install_fake_player(manager)
    assert manager.play_track("t1") is False


def test_play_track_unknown_id_returns_false(isolated_paths, tmp_path):
    manager, _ = _make_manager_with_fake_player(tmp_path)
    assert manager.play_track("no-such-id") is False


def test_play_track_starts_playback_and_now_playing_reflects_it(isolated_paths, tmp_path):
    manager, _ = _make_manager_with_fake_player(tmp_path)
    assert manager.play_track("t1") is True

    now_playing = manager.now_playing()
    assert now_playing.track_id == "t1"
    assert now_playing.title == "Song A"
    assert now_playing.is_playing is True
    assert now_playing.duration_seconds == 200.0


def test_pause_and_resume(isolated_paths, tmp_path):
    """Pausing stops playing and resuming plays again."""
    manager, _ = _make_manager_with_fake_player(tmp_path)
    manager.play_track("t1")
    manager.pause()
    assert manager.now_playing().is_playing is False
    manager.resume()
    assert manager.now_playing().is_playing is True


def test_stop_clears_queue(isolated_paths, tmp_path):
    """Stopping leaves nothing playing."""
    manager, _ = _make_manager_with_fake_player(tmp_path)
    manager.play_track("t1")
    manager.stop()
    assert manager.now_playing() is None


def test_seek_updates_position(isolated_paths, tmp_path):
    """Seeking moves what's playing to that second."""
    manager, _ = _make_manager_with_fake_player(tmp_path)
    manager.play_track("t1")
    manager.seek(42.0)
    assert manager.now_playing().position_seconds == 42.0


def test_set_volume_clamps_and_persists(isolated_paths, tmp_path):
    manager, _ = _make_manager_with_fake_player(tmp_path)
    manager.set_volume(150)
    assert manager.now_playing() is None  # nothing playing yet, but volume still applies
    manager.play_track("t1")
    assert manager.now_playing().volume_percent == 100
    assert manager.context.config.get("music.last_volume") == 100

    manager.set_volume(-10)
    assert manager.now_playing().volume_percent == 0


def test_next_and_previous_track_within_a_queue(isolated_paths, tmp_path):
    manager = _make_manager(_make_context())
    files = []
    for i in range(3):
        f = tmp_path / f"song{i}.mp3"
        f.write_bytes(b"fake")
        files.append(f)
        manager._tracks.append(Track(track_id=f"t{i}", file_path=str(f), title=f"Song {i}"))
    playlist = manager.create_playlist("Mix")
    for i in range(3):
        manager.add_track_to_playlist(playlist.playlist_id, f"t{i}")
    _install_fake_player(manager)

    assert manager.play_playlist(playlist.playlist_id) is True
    assert manager.now_playing().track_id == "t0"

    assert manager.next_track() is True
    assert manager.now_playing().track_id == "t1"
    assert manager.next_track() is True
    assert manager.now_playing().track_id == "t2"
    assert manager.next_track() is False  # already at the end, no wraparound

    assert manager.previous_track() is True
    assert manager.now_playing().track_id == "t1"


def test_play_playlist_empty_or_bad_start_index_returns_false(isolated_paths, tmp_path):
    manager = _make_manager(_make_context())
    playlist = manager.create_playlist("Empty")
    _install_fake_player(manager)
    assert manager.play_playlist(playlist.playlist_id) is False
    assert manager.play_playlist("no-such-playlist") is False


def test_a_phones_own_folders_are_read_too(isolated_paths, tmp_path):
    context = _make_context()
    context.config.set("music.library_root_path", str(tmp_path / "nowhere"))
    phone = tmp_path / "Music"
    _write_wav(phone / "song.wav", title="Phone Song")
    context.config.set("music.extra_folders", [str(phone)])
    manager = _make_manager(context)
    result = manager.scan_library(as_of=time.time() + 60)
    assert result.added == 1 and [t.title for t in manager.all_tracks()] == ["Phone Song"]


def test_a_folder_that_reads_empty_keeps_its_songs(isolated_paths, tmp_path):
    """Android shows an empty folder until it lets MIA read audio: nothing is lost."""
    context = _make_context()
    phone = tmp_path / "Music"
    _write_wav(phone / "song.wav", title="Phone Song")
    context.config.set("music.extra_folders", [str(phone)])
    manager = _make_manager(context)
    manager.scan_library(as_of=time.time() + 60)
    (phone / "song.wav").unlink()
    manager.scan_library(as_of=time.time() + 60)
    assert [t.title for t in manager.all_tracks()] == ["Phone Song"]
