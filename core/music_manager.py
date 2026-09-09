"""
core.music_manager
=====================

Local audio library + playlists + real playback for the Music module
(modules/music/module.py) — 2026-09-09. Replaces the pure-placeholder
Music stub, closing the last remaining "pure stub module" in this
project.

**The historical blocker on this is gone.** Music was previously
documented (docs/ROADMAP.md, docs/KNOWN_ISSUES.md) as blocked on a
missing `libpulse`/PortAudio system dependency with no sudo access.
Re-verified directly, in this exact dev sandbox, before writing any of
this: `PySide6.QtMultimedia` imports cleanly, `QMediaDevices
.audioOutputs()` returns a real device, and `QMediaPlayer`/
`QAudioOutput` construct with zero error on a real bundled FFmpeg 7.1.3
backend — `libpulse0`/`pulseaudio-utils`/`libasound2t64`/
`libportaudio2` are now all installed where they weren't before. The
one new dependency this adds, `mutagen` (audio tag reading), is pure
Python with no system library — confirmed installable in this sandbox.

**Files are referenced, never copied in** — deliberately unlike
core.trail_map_library.TrailMapLibrary (which copies each PDF into an
app-owned root it creates). A personal music library already lives
somewhere on disk, often many GB; `scan_library()` indexes files at
their real absolute path under a configured `music.library_root_path`
(same empty-string-default-to-a-repo-local-folder config pattern as
`maps.trail_map_root_path`) and never auto-creates that root — a
temporarily-unmounted drive must never look like "the whole library
just vanished" (see scan_library()'s own docstring).

**Playback owns a real, lazily-constructed `QMediaPlayer`/
`QAudioOutput` directly in core/**, matching core.voice_manager
.VoiceManager's own precedent of owning real (non-widget) audio
playback in core/ — not core.avatar_manager.AvatarManager's stricter
"core/ owns registry truth, gui/ owns actual rendering" split, which is
specifically about widget/video-surface rendering. QMediaPlayer has no
widget/paint surface at all, so it's a headless engine object like
sounddevice, not a rendering concern. Construction is lazy
(`_ensure_player()`, built on first real playback call) so
`scan_library()`/CRUD stay entirely Qt-free and testable without a
live QApplication — see tests/test_music_manager.py.

**Real, honest limitation, not glossed over**: `core/voice_loop.py`
(the headless MIA Core entry point) runs with no `QApplication`/
`QCoreApplication`/event loop at all — `VoiceManager` deliberately uses
`sounddevice` instead of Qt for exactly that reason. `QMediaPlayer`
needs a live, pumped Qt event loop to actually decode/play anything;
if this manager is ever constructed and driven from that headless
path, playback methods would return success but produce no real audio.
The normal GUI boot path, and the GUI's own Assistant chat path
(confirmed: the actual action-handler call happens on the main GUI
thread, not inside ChatWorker's QThread), are both safe.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime
from typing import TYPE_CHECKING, Optional

import json

from core.app_context import AppContext
from core.logger import get_logger

if TYPE_CHECKING:
    from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer

log = get_logger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_ROOT = _PROJECT_ROOT / "music_library"
_DATA_DIR = _PROJECT_ROOT / "data"
_TRACKS_FILE = _DATA_DIR / "music_tracks.json"
_PLAYLISTS_FILE = _DATA_DIR / "music_playlists.json"

_AUDIO_EXTENSIONS = {".mp3", ".flac", ".ogg", ".m4a", ".opus", ".wav"}
_MIN_QUIET_SECONDS = 5.0  # same "file might still be mid-copy" guard as ReferenceLibraryManager

# mutagen's easy=True interface remaps ID3/Vorbis/MP4 tags to friendly
# keys (title/artist/album/genre/tracknumber) for mp3/flac/ogg/m4a —
# but NOT for WAV, which has no "Easy" variant and falls back to raw
# ID3 frame ids. Confirmed directly: mutagen.File(wav_path,
# easy=True).tags comes back as {'TIT2': ..., 'TPE1': ...}, not
# {'title': ..., 'artist': ...}. Try the friendly key first, then the
# raw WAVE frame id, so one code path covers every supported format.
_TAG_KEYS = {
    "title": ("title", "TIT2"),
    "artist": ("artist", "TPE1"),
    "album": ("album", "TALB"),
    "genre": ("genre", "TCON"),
    "tracknumber": ("tracknumber", "TRCK"),
}


@dataclass
class Track:
    track_id: str
    file_path: str  # absolute path — the real, referenced file, never copied
    title: str
    artist: str = ""
    album: str = ""
    genre: str = ""
    track_number: Optional[int] = None
    duration_seconds: float = 0.0
    file_size: int = 0  # bytes, as of last scan — paired with file_mtime to skip re-reading tags on an unchanged file
    file_mtime: float = 0.0
    added_at: str = ""
    last_scanned_at: str = ""

    def to_dict(self) -> dict:
        return {
            "track_id": self.track_id, "file_path": self.file_path, "title": self.title,
            "artist": self.artist, "album": self.album, "genre": self.genre,
            "track_number": self.track_number, "duration_seconds": self.duration_seconds,
            "file_size": self.file_size, "file_mtime": self.file_mtime,
            "added_at": self.added_at, "last_scanned_at": self.last_scanned_at,
        }

    @staticmethod
    def from_dict(data: dict) -> "Track":
        return Track(
            track_id=data.get("track_id", uuid.uuid4().hex[:10]),
            file_path=data.get("file_path", ""),
            title=data.get("title", ""),
            artist=data.get("artist", ""),
            album=data.get("album", ""),
            genre=data.get("genre", ""),
            track_number=data.get("track_number"),
            duration_seconds=data.get("duration_seconds", 0.0),
            file_size=data.get("file_size", 0),
            file_mtime=data.get("file_mtime", 0.0),
            added_at=data.get("added_at", ""),
            last_scanned_at=data.get("last_scanned_at", ""),
        )


@dataclass
class Playlist:
    playlist_id: str
    name: str
    track_ids: list[str] = field(default_factory=list)
    created_at: str = ""

    def to_dict(self) -> dict:
        return {
            "playlist_id": self.playlist_id, "name": self.name,
            "track_ids": list(self.track_ids), "created_at": self.created_at,
        }

    @staticmethod
    def from_dict(data: dict) -> "Playlist":
        return Playlist(
            playlist_id=data.get("playlist_id", uuid.uuid4().hex[:10]),
            name=data.get("name", ""),
            track_ids=list(data.get("track_ids", [])),
            created_at=data.get("created_at", ""),
        )


@dataclass
class ScanResult:
    added: int = 0
    updated: int = 0
    unchanged: int = 0
    removed: int = 0
    root_missing: bool = False


@dataclass
class NowPlaying:
    track_id: str
    title: str
    artist: str
    album: str
    position_seconds: float
    duration_seconds: float
    is_playing: bool
    volume_percent: int
    playlist_id: Optional[str] = None
    queue_position: int = 0
    queue_length: int = 1


def _first_tag_value(tags, keys: tuple[str, ...]) -> str:
    for key in keys:
        try:
            value = tags[key]
        except (KeyError, TypeError):
            continue
        if not value:
            continue
        first = value[0] if isinstance(value, (list, tuple)) else value
        text = str(first).strip()
        if text:
            return text
    return ""


def _parse_track_number(raw: str) -> Optional[int]:
    """Handles both a bare "3" and the common "3/12" (track/total) tag shape."""
    if not raw:
        return None
    head = raw.split("/")[0].strip()
    try:
        return int(head)
    except ValueError:
        return None


def read_track_tags(path: Path) -> dict:
    """Pure-ish helper (only touches the filesystem/mutagen, no Qt) —
    real duration + title/artist/album/genre/track_number read via
    mutagen, defaulting every missing field to "" (title falls back to
    the filename stem, handled by the caller since this function
    doesn't know the file's identity beyond its tags). Never raises —
    an unreadable/corrupt file just yields all-default results, same
    graceful-degradation stance as every other library-scan manager in
    this codebase."""
    result = {
        "title": "", "artist": "", "album": "", "genre": "",
        "track_number": None, "duration_seconds": 0.0,
    }
    try:
        import mutagen
        audio = mutagen.File(str(path), easy=True)
    except Exception:
        log.warning("Could not read tags from '%s' — using defaults.", path, exc_info=True)
        return result

    if audio is None:
        return result
    if audio.info is not None and getattr(audio.info, "length", None):
        result["duration_seconds"] = float(audio.info.length)
    if audio.tags is None:
        return result

    result["title"] = _first_tag_value(audio.tags, _TAG_KEYS["title"])
    result["artist"] = _first_tag_value(audio.tags, _TAG_KEYS["artist"])
    result["album"] = _first_tag_value(audio.tags, _TAG_KEYS["album"])
    result["genre"] = _first_tag_value(audio.tags, _TAG_KEYS["genre"])
    result["track_number"] = _parse_track_number(_first_tag_value(audio.tags, _TAG_KEYS["tracknumber"]))
    return result


class MusicManager:
    def __init__(self, context: AppContext) -> None:
        self.context = context
        self._tracks: list[Track] = []
        self._playlists: list[Playlist] = []
        self._load()

        self._player: Optional["QMediaPlayer"] = None
        self._audio_output: Optional["QAudioOutput"] = None
        self._queue: list[str] = []  # track_ids
        self._queue_index: int = 0
        self._queue_playlist_id: Optional[str] = None

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load(self) -> None:
        self._tracks = self._load_file(_TRACKS_FILE, Track.from_dict)
        self._playlists = self._load_file(_PLAYLISTS_FILE, Playlist.from_dict)

    @staticmethod
    def _load_file(path: Path, from_dict) -> list:
        if not path.exists():
            return []
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            return [from_dict(d) for d in raw]
        except (json.JSONDecodeError, OSError):
            log.exception("Failed to load %s — starting with an empty list.", path.name)
            return []

    def _save_tracks(self) -> None:
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        _TRACKS_FILE.write_text(json.dumps([t.to_dict() for t in self._tracks], indent=2), encoding="utf-8")

    def _save_playlists(self) -> None:
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        _PLAYLISTS_FILE.write_text(json.dumps([p.to_dict() for p in self._playlists], indent=2), encoding="utf-8")

    def _resolve_root_path(self) -> Path:
        configured = self.context.config.get("music.library_root_path", "")
        if configured:
            return Path(configured).expanduser()
        return _DEFAULT_ROOT

    @property
    def root_path(self) -> Path:
        return self._resolve_root_path()

    # ------------------------------------------------------------------
    # Library scan
    # ------------------------------------------------------------------

    def scan_library(self) -> ScanResult:
        """Walks root_path for audio files, indexing new ones, skipping
        tag re-reads for files whose (size, mtime) haven't changed
        since the last scan, and pruning files no longer present.

        Never auto-creates root_path (unlike TrailMapLibrary's owned
        root) and never mutates the index at all if root_path doesn't
        currently exist — a temporarily-unmounted drive must never
        look like "the whole library vanished"; the caller sees
        ScanResult(root_missing=True) instead."""
        root = self._resolve_root_path()
        if not root.exists():
            log.warning("Music library root '%s' doesn't exist — scan skipped.", root)
            return ScanResult(root_missing=True)

        found: dict[str, Path] = {}
        for path in root.rglob("*"):
            if path.is_file() and path.suffix.lower() in _AUDIO_EXTENSIONS:
                found[str(path.resolve())] = path

        existing_by_path = {t.file_path: t for t in self._tracks}
        now = datetime.now().isoformat(timespec="seconds")
        added = updated = unchanged = 0

        for file_path, path in found.items():
            try:
                stat = path.stat()
            except OSError:
                continue
            if time.time() - stat.st_mtime < _MIN_QUIET_SECONDS:
                continue  # still mid-copy, likely — pick it up on a later scan

            existing = existing_by_path.get(file_path)
            if existing is not None and (existing.file_size, existing.file_mtime) == (stat.st_size, stat.st_mtime):
                unchanged += 1
                continue

            tags = read_track_tags(path)
            title = tags["title"] or path.stem
            if existing is not None:
                existing.title = title
                existing.artist = tags["artist"]
                existing.album = tags["album"]
                existing.genre = tags["genre"]
                existing.track_number = tags["track_number"]
                existing.duration_seconds = tags["duration_seconds"]
                existing.file_size = stat.st_size
                existing.file_mtime = stat.st_mtime
                existing.last_scanned_at = now
                updated += 1
            else:
                new_track = Track(
                    track_id=uuid.uuid4().hex[:10], file_path=file_path, title=title,
                    artist=tags["artist"], album=tags["album"], genre=tags["genre"],
                    track_number=tags["track_number"], duration_seconds=tags["duration_seconds"],
                    file_size=stat.st_size, file_mtime=stat.st_mtime,
                    added_at=now, last_scanned_at=now,
                )
                self._tracks.append(new_track)
                added += 1

        removed_ids = {t.track_id for t in self._tracks if t.file_path not in found}
        if removed_ids:
            self._tracks = [t for t in self._tracks if t.track_id not in removed_ids]

        self._save_tracks()
        log.info(
            "Music library scan: %d added, %d updated, %d unchanged, %d removed.",
            added, updated, unchanged, len(removed_ids),
        )
        return ScanResult(added=added, updated=updated, unchanged=unchanged, removed=len(removed_ids))

    # ------------------------------------------------------------------
    # Track CRUD
    # ------------------------------------------------------------------

    def get_track(self, track_id: str) -> Optional[Track]:
        for track in self._tracks:
            if track.track_id == track_id:
                return track
        return None

    def all_tracks(self) -> list[Track]:
        return sorted(
            self._tracks,
            key=lambda t: (t.artist.lower(), t.album.lower(), t.track_number or 0, t.title.lower()),
        )

    def search_tracks(self, query: str) -> list[Track]:
        needle = query.lower().strip()
        if not needle:
            return self.all_tracks()
        return [
            t for t in self.all_tracks()
            if needle in t.title.lower() or needle in t.artist.lower() or needle in t.album.lower()
        ]

    def delete_track(self, track_id: str) -> None:
        """Index-only removal — never touches the real file on disk.
        Also strips the id out of every playlist that referenced it,
        same non-destructive-to-real-data stance as every other
        "delete a parent record" path in this codebase."""
        self._tracks = [t for t in self._tracks if t.track_id != track_id]
        self._save_tracks()
        changed = False
        for playlist in self._playlists:
            if track_id in playlist.track_ids:
                playlist.track_ids = [tid for tid in playlist.track_ids if tid != track_id]
                changed = True
        if changed:
            self._save_playlists()

    # ------------------------------------------------------------------
    # Playlist CRUD
    # ------------------------------------------------------------------

    def create_playlist(self, name: str) -> Playlist:
        playlist = Playlist(
            playlist_id=uuid.uuid4().hex[:10], name=name,
            created_at=datetime.now().isoformat(timespec="seconds"),
        )
        self._playlists.append(playlist)
        self._save_playlists()
        return playlist

    def rename_playlist(self, playlist_id: str, name: str) -> Optional[Playlist]:
        playlist = self.get_playlist(playlist_id)
        if playlist is None:
            return None
        playlist.name = name
        self._save_playlists()
        return playlist

    def delete_playlist(self, playlist_id: str) -> None:
        self._playlists = [p for p in self._playlists if p.playlist_id != playlist_id]
        self._save_playlists()

    def get_playlist(self, playlist_id: str) -> Optional[Playlist]:
        for playlist in self._playlists:
            if playlist.playlist_id == playlist_id:
                return playlist
        return None

    def all_playlists(self) -> list[Playlist]:
        return sorted(self._playlists, key=lambda p: p.name.lower())

    def add_track_to_playlist(self, playlist_id: str, track_id: str) -> bool:
        playlist = self.get_playlist(playlist_id)
        if playlist is None or track_id in playlist.track_ids:
            return False
        playlist.track_ids.append(track_id)
        self._save_playlists()
        return True

    def remove_track_from_playlist(self, playlist_id: str, track_id: str) -> bool:
        playlist = self.get_playlist(playlist_id)
        if playlist is None or track_id not in playlist.track_ids:
            return False
        playlist.track_ids = [tid for tid in playlist.track_ids if tid != track_id]
        self._save_playlists()
        return True

    def tracks_for_playlist(self, playlist_id: str) -> list[Track]:
        """Resolves each id against the live track index, silently
        skipping any id that no longer resolves (a pruned/deleted
        track) — dangling ids are never treated as an error here, and
        scan_library() never rewrites track_ids to clean them up
        either, since a briefly-disconnected drive must not
        permanently edit a playlist."""
        playlist = self.get_playlist(playlist_id)
        if playlist is None:
            return []
        tracks = []
        for track_id in playlist.track_ids:
            track = self.get_track(track_id)
            if track is not None:
                tracks.append(track)
        return tracks

    # ------------------------------------------------------------------
    # Playback — lazy QMediaPlayer/QAudioOutput, see module docstring
    # ------------------------------------------------------------------

    def _ensure_player(self) -> "QMediaPlayer":
        if self._player is None:
            from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer

            self._player = QMediaPlayer()
            self._audio_output = QAudioOutput()
            self._player.setAudioOutput(self._audio_output)
            self._player.mediaStatusChanged.connect(self._on_media_status_changed)
            self._player.errorOccurred.connect(self._on_error)

            initial_volume = self.context.config.get("music.last_volume", 70)
            self._audio_output.setVolume(max(0, min(100, initial_volume)) / 100.0)
        return self._player

    def _on_media_status_changed(self, status) -> None:
        from PySide6.QtMultimedia import QMediaPlayer

        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            self.next_track()

    def _on_error(self, error, error_string: str) -> None:
        log.warning("Music playback error: %s", error_string)

    def _load_track_into_player(self, track: Track) -> bool:
        from PySide6.QtCore import QUrl

        path = Path(track.file_path)
        if not path.exists():
            log.warning("Track file no longer exists: '%s'", track.file_path)
            return False
        player = self._ensure_player()
        player.setSource(QUrl.fromLocalFile(str(path)))
        player.play()
        return True

    def play_track(self, track_id: str) -> bool:
        track = self.get_track(track_id)
        if track is None:
            return False
        self._queue = [track_id]
        self._queue_index = 0
        self._queue_playlist_id = None
        return self._load_track_into_player(track)

    def play_playlist(self, playlist_id: str, start_index: int = 0) -> bool:
        tracks = self.tracks_for_playlist(playlist_id)
        if not tracks or not (0 <= start_index < len(tracks)):
            return False
        self._queue = [t.track_id for t in tracks]
        self._queue_index = start_index
        self._queue_playlist_id = playlist_id
        return self._load_track_into_player(tracks[start_index])

    def pause(self) -> None:
        if self._player is not None:
            self._player.pause()

    def resume(self) -> None:
        if self._player is not None:
            self._player.play()

    def stop(self) -> None:
        if self._player is not None:
            self._player.stop()
        self._queue = []
        self._queue_index = 0
        self._queue_playlist_id = None

    def next_track(self) -> bool:
        if not self._queue or self._queue_index + 1 >= len(self._queue):
            return False
        self._queue_index += 1
        track = self.get_track(self._queue[self._queue_index])
        if track is None:
            return self.next_track()
        return self._load_track_into_player(track)

    def previous_track(self) -> bool:
        if not self._queue or self._queue_index <= 0:
            return False
        self._queue_index -= 1
        track = self.get_track(self._queue[self._queue_index])
        if track is None:
            return self.previous_track()
        return self._load_track_into_player(track)

    def seek(self, position_seconds: float) -> None:
        if self._player is not None:
            self._player.setPosition(int(position_seconds * 1000))

    def set_volume(self, percent: int) -> None:
        percent = max(0, min(100, percent))
        self._ensure_player()
        self._audio_output.setVolume(percent / 100.0)
        self.context.config.set("music.last_volume", percent)

    def now_playing(self) -> Optional[NowPlaying]:
        if self._player is None or not self._queue:
            return None
        from PySide6.QtMultimedia import QMediaPlayer

        track_id = self._queue[self._queue_index]
        track = self.get_track(track_id)
        if track is None:
            return None
        return NowPlaying(
            track_id=track.track_id, title=track.title, artist=track.artist, album=track.album,
            position_seconds=self._player.position() / 1000.0,
            duration_seconds=self._player.duration() / 1000.0,
            is_playing=self._player.playbackState() == QMediaPlayer.PlaybackState.PlayingState,
            volume_percent=round((self._audio_output.volume() if self._audio_output else 0.0) * 100),
            playlist_id=self._queue_playlist_id, queue_position=self._queue_index, queue_length=len(self._queue),
        )
