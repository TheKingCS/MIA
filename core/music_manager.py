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

**The web pages ask this player too (2026-11-10).** A song used to play
in the Music page's own audio element and stopped when another page
opened. In the desktop window the pages now ask this manager instead
(core/web_more.music_play / music_control, `play_queue()` for the
page's list of songs), so the song belongs to MIA and not to a page.
Those calls arrive on the server's thread, and a QMediaPlayer only
plays on the window's: every playback method is wrapped in
`_on_gui_thread`, which hands the work to `context.main_thread_call`
and waits a few seconds for the answer (None when the window was too
busy to give one; the work still runs when it gets there).
"""

from __future__ import annotations

import functools
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime
from typing import TYPE_CHECKING, Optional

import json

from core.app_context import AppContext
from core.logger import get_logger
from core.atomic_write import atomic_write_text
from core.data_recovery import notify_data_corruption

if TYPE_CHECKING:
    from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer

log = get_logger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_ROOT = _PROJECT_ROOT / "music_library"
_DATA_DIR = _PROJECT_ROOT / "data"
_TRACKS_FILE = _DATA_DIR / "music_tracks.json"
_PLAYLISTS_FILE = _DATA_DIR / "music_playlists.json"

_AUDIO_EXTENSIONS = {".mp3", ".flac", ".ogg", ".m4a", ".opus", ".wav"}
MAX_UPLOAD_BYTES = 200 * 1024 * 1024
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
    """One song in the library: the real file it points at (never copied), its tags (title, artist, album, genre,
    track number), duration, and the file's size and modified time at the last scan (so an unchanged file's tags
    aren't read again).
    """
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
        """The record as the plain dict saved in its JSON file."""
        return {
            "track_id": self.track_id, "file_path": self.file_path, "title": self.title,
            "artist": self.artist, "album": self.album, "genre": self.genre,
            "track_number": self.track_number, "duration_seconds": self.duration_seconds,
            "file_size": self.file_size, "file_mtime": self.file_mtime,
            "added_at": self.added_at, "last_scanned_at": self.last_scanned_at,
        }

    @staticmethod
    def from_dict(data: dict) -> "Track":
        """A record from its saved dict; a missing field takes its default, so older files load."""
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
    """A named playlist: the songs on it by track id, in order."""
    playlist_id: str
    name: str
    track_ids: list[str] = field(default_factory=list)
    created_at: str = ""

    def to_dict(self) -> dict:
        """The record as the plain dict saved in its JSON file."""
        return {
            "playlist_id": self.playlist_id, "name": self.name,
            "track_ids": list(self.track_ids), "created_at": self.created_at,
        }

    @staticmethod
    def from_dict(data: dict) -> "Playlist":
        """A record from its saved dict; a missing field takes its default, so older files load."""
        return Playlist(
            playlist_id=data.get("playlist_id", uuid.uuid4().hex[:10]),
            name=data.get("name", ""),
            track_ids=list(data.get("track_ids", [])),
            created_at=data.get("created_at", ""),
        )


@dataclass
class ScanResult:
    """What a library scan did: songs added, updated, unchanged and removed, and whether the music folder was missing."""
    added: int = 0
    updated: int = 0
    unchanged: int = 0
    removed: int = 0
    root_missing: bool = False


@dataclass
class NowPlaying:
    """What's playing right now: the song, position and length, playing or paused, the volume, and where it is in the
    queue (and the playlist it came from).
    """
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
    """The first non-empty value among a file's tags under any of these keys (tag names differ by format), or ""."""
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


# How long a caller on another thread waits for the GUI thread to do what it asked of the player.
_GUI_WAIT_SECONDS = 4.0


def _on_gui_thread(method):
    """Makes a playback method run on the GUI thread, whoever calls it (2026-11-10): QMediaPlayer only plays on the
    thread with the window's event loop, and a song asked for from a web page or from Talk arrives on the server's
    thread. Called there, the method is handed over through context.main_thread_call and its answer waited for (None
    when the window is too busy to answer in time; the method still runs when it is free). On the GUI thread, or with
    no hand-off (tests, no window), it runs directly."""
    @functools.wraps(method)
    def run(self, *args, **kwargs):
        """Runs the method here or on the GUI thread, and gives back what it returned."""
        call = getattr(self.context, "main_thread_call", None)
        if call is None or threading.current_thread() is threading.main_thread():
            return method(self, *args, **kwargs)
        done, answer = threading.Event(), {}

        def work():
            """The method, run on the GUI thread; its answer is left for the waiting caller."""
            try:
                answer["value"] = method(self, *args, **kwargs)
            finally:
                done.set()

        call(work)
        done.wait(_GUI_WAIT_SECONDS)
        return answer.get("value")
    return run


class MusicManager:
    """The music library and player: songs scanned from the music folder (music.library_root_path), playlists, and a
    QMediaPlayer made only when something first plays. Tracks and playlists are saved as JSON through
    atomic_write_text; the queue and position live only in memory. The playback methods may be called from any
    thread (_on_gui_thread): the player itself only ever runs on the GUI thread.
    """
    def __init__(self, context: AppContext) -> None:
        """Loads the library and playlists. The player isn't made here (cheap boot): _ensure_player makes it on first use."""
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
        """Reads the tracks and playlists (undo calls this to reload)."""
        self._tracks = self._load_file(_TRACKS_FILE, Track.from_dict)
        self._playlists = self._load_file(_PLAYLISTS_FILE, Playlist.from_dict)

    def _load_file(self, path: Path, from_dict) -> list:
        """One file's records; missing is empty, a damaged file is logged, reported (notify_data_corruption) and starts
        empty.
        """
        if not path.exists():
            return []
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            return [from_dict(d) for d in raw]
        except (json.JSONDecodeError, OSError):
            log.exception("Failed to load %s — starting with an empty list.", path.name)
            notify_data_corruption(self.context, path.name)
            return []

    def _save_tracks(self) -> None:
        """Saves the library atomically."""
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        atomic_write_text(_TRACKS_FILE, json.dumps([t.to_dict() for t in self._tracks], indent=2), encoding="utf-8")

    def _save_playlists(self) -> None:
        """Saves the playlists atomically."""
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        atomic_write_text(_PLAYLISTS_FILE, json.dumps([p.to_dict() for p in self._playlists], indent=2), encoding="utf-8")

    def _resolve_root_path(self) -> Path:
        """The music folder: the configured music.library_root_path, else the default."""
        configured = self.context.config.get("music.library_root_path", "")
        if configured:
            return Path(configured).expanduser()
        return _DEFAULT_ROOT

    @property
    def root_path(self) -> Path:
        """The music folder the library scans."""
        return self._resolve_root_path()

    # ------------------------------------------------------------------
    # Library scan
    # ------------------------------------------------------------------

    def scan_library(self, as_of: Optional[float] = None) -> ScanResult:
        """Walks root_path for audio files, indexing new ones, skipping
        tag re-reads for files whose (size, mtime) haven't changed
        since the last scan, and pruning files no longer present.

        Never auto-creates root_path (unlike TrailMapLibrary's owned
        root) and never mutates the index at all if root_path doesn't
        currently exist — a temporarily-unmounted drive must never
        look like "the whole library vanished"; the caller sees
        ScanResult(root_missing=True) instead. `as_of` (a later time) takes in
        files MIA just wrote whole, like an upload, without the wait."""
        root = self._resolve_root_path()
        # Folders the library also reads, like a phone's own Music folder.
        extras = [Path(f).expanduser() for f in self.context.config.get("music.extra_folders", []) or []]
        extras = [f for f in extras if f.exists()]
        if not root.exists() and not extras:
            log.warning("Music library root '%s' doesn't exist — scan skipped.", root)
            return ScanResult(root_missing=True)

        found: dict[str, Path] = {}
        silent: list[str] = []  # an empty extra folder may just be a permission not given
        for folder in ([root] if root.exists() else []) + extras:
            before = len(found)
            for path in folder.rglob("*"):
                if path.is_file() and path.suffix.lower() in _AUDIO_EXTENSIONS:
                    found[str(path.resolve())] = path
            if folder in extras and len(found) == before:
                silent.append(str(folder.resolve()))

        existing_by_path = {t.file_path: t for t in self._tracks}
        now = datetime.now().isoformat(timespec="seconds")
        added = updated = unchanged = 0

        for file_path, path in found.items():
            try:
                stat = path.stat()
            except OSError:
                continue
            if (as_of or time.time()) - stat.st_mtime < _MIN_QUIET_SECONDS:
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

        removed_ids = {t.track_id for t in self._tracks if t.file_path not in found
                       and not any(t.file_path.startswith(s) for s in silent)}
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
        """The song with this id, or None."""
        for track in self._tracks:
            if track.track_id == track_id:
                return track
        return None

    def all_tracks(self) -> list[Track]:
        """Every song by artist, album, track number, then title."""
        return sorted(
            self._tracks,
            key=lambda t: (t.artist.lower(), t.album.lower(), t.track_number or 0, t.title.lower()),
        )

    def search_tracks(self, query: str) -> list[Track]:
        """The songs whose title, artist or album contains the query (all of them for an empty one)."""
        needle = query.lower().strip()
        if not needle:
            return self.all_tracks()
        return [
            t for t in self.all_tracks()
            if needle in t.title.lower() or needle in t.artist.lower() or needle in t.album.lower()
        ]

    def save_upload(self, filename: str, data: bytes) -> Path:
        """A song sent from a phone or computer (Zac, 2026-10-16: "upload mp3
        files from my device's files"), saved into the library folder, then
        found by the next scan_library(). The default folder is created if
        needed; a folder the person chose that isn't there (an unplugged
        drive) is never created, same as scan_library()."""
        name = Path(str(filename or "")).name.strip()
        if Path(name).suffix.lower() not in _AUDIO_EXTENSIONS:
            raise ValueError("That isn't a song MIA can play (mp3, m4a, flac, ogg, opus or wav).")
        if len(data) > MAX_UPLOAD_BYTES:
            raise ValueError("That song is over 200 MB.")
        root = self._resolve_root_path()
        if self.context.config.get("music.library_root_path", "") and not root.exists():
            raise ValueError(f"MIA's music folder ({root}) isn't there. Plug in the drive or change it in Settings.")
        folder = root / "Uploads"
        folder.mkdir(parents=True, exist_ok=True)
        safe = "".join(ch if ch.isalnum() or ch in " .-_()&'," else "_" for ch in name).strip() or "song.mp3"
        target, n = folder / safe, 2
        while target.exists():
            target = folder / f"{Path(safe).stem} ({n}){Path(safe).suffix}"
            n += 1
        partial = folder / f".{target.name}.part"
        partial.write_bytes(data)
        partial.replace(target)
        return target

    def uploaded(self, track: "Track") -> bool:
        """A song that was uploaded into MIA (its own copy, safe to delete)."""
        try:
            return Path(track.file_path).resolve().parent == (self._resolve_root_path() / "Uploads").resolve()
        except OSError:
            return False

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
        """Makes an empty playlist."""
        playlist = Playlist(
            playlist_id=uuid.uuid4().hex[:10], name=name,
            created_at=datetime.now().isoformat(timespec="seconds"),
        )
        self._playlists.append(playlist)
        self._save_playlists()
        return playlist

    def rename_playlist(self, playlist_id: str, name: str) -> Optional[Playlist]:
        """Renames a playlist (None when it's gone)."""
        playlist = self.get_playlist(playlist_id)
        if playlist is None:
            return None
        playlist.name = name
        self._save_playlists()
        return playlist

    def delete_playlist(self, playlist_id: str) -> None:
        """Deletes a playlist; its songs stay in the library."""
        self._playlists = [p for p in self._playlists if p.playlist_id != playlist_id]
        self._save_playlists()

    def get_playlist(self, playlist_id: str) -> Optional[Playlist]:
        """The playlist with this id, or None."""
        for playlist in self._playlists:
            if playlist.playlist_id == playlist_id:
                return playlist
        return None

    def all_playlists(self) -> list[Playlist]:
        """Every playlist, by name."""
        return sorted(self._playlists, key=lambda p: p.name.lower())

    def add_track_to_playlist(self, playlist_id: str, track_id: str) -> bool:
        """Adds a song to the end of a playlist; False when the playlist is gone or already has it."""
        playlist = self.get_playlist(playlist_id)
        if playlist is None or track_id in playlist.track_ids:
            return False
        playlist.track_ids.append(track_id)
        self._save_playlists()
        return True

    def remove_track_from_playlist(self, playlist_id: str, track_id: str) -> bool:
        """Takes a song off a playlist; False when it wasn't on it."""
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
        """The QMediaPlayer, made on first use with its audio output at the last volume, moving to the next song when one
        ends and logging playback errors.
        """
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
        """When a song ends, plays the next one in the queue."""
        from PySide6.QtMultimedia import QMediaPlayer

        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            self.next_track()

    def _on_error(self, error, error_string: str) -> None:
        """Logs a playback error (never raises)."""
        log.warning("Music playback error: %s", error_string)

    def _load_track_into_player(self, track: Track) -> bool:
        """Starts playing a song's file; False (logged) when the file is no longer there."""
        from PySide6.QtCore import QUrl

        path = Path(track.file_path)
        if not path.exists():
            log.warning("Track file no longer exists: '%s'", track.file_path)
            return False
        player = self._ensure_player()
        player.setSource(QUrl.fromLocalFile(str(path)))
        player.play()
        return True

    @_on_gui_thread
    def play_queue(self, track_ids: list[str], start_index: int = 0) -> bool:
        """Plays a list of songs from a position, the rest following (a page's list: every song, an artist's, a
        search). Songs no longer in the library are left out; False when none is left or the position isn't there."""
        known = [i for i in track_ids if self.get_track(i) is not None]
        if not known or not (0 <= start_index < len(track_ids)):
            return False
        started = track_ids[start_index]
        self._queue = known
        self._queue_index = known.index(started) if started in known else 0
        self._queue_playlist_id = None
        return self._load_track_into_player(self.get_track(self._queue[self._queue_index]))

    @_on_gui_thread
    def play_track(self, track_id: str) -> bool:
        """Plays one song on its own (a queue of one)."""
        track = self.get_track(track_id)
        if track is None:
            return False
        self._queue = [track_id]
        self._queue_index = 0
        self._queue_playlist_id = None
        return self._load_track_into_player(track)

    @_on_gui_thread
    def play_playlist(self, playlist_id: str, start_index: int = 0) -> bool:
        """Plays a playlist from a position; False when it's empty or the position isn't on it."""
        tracks = self.tracks_for_playlist(playlist_id)
        if not tracks or not (0 <= start_index < len(tracks)):
            return False
        self._queue = [t.track_id for t in tracks]
        self._queue_index = start_index
        self._queue_playlist_id = playlist_id
        return self._load_track_into_player(tracks[start_index])

    @_on_gui_thread
    def pause(self) -> None:
        """Pauses (nothing when nothing has played)."""
        if self._player is not None:
            self._player.pause()

    @_on_gui_thread
    def resume(self) -> None:
        """Resumes after a pause."""
        if self._player is not None:
            self._player.play()

    @_on_gui_thread
    def stop(self) -> None:
        """Stops and clears the queue."""
        if self._player is not None:
            self._player.stop()
        self._queue = []
        self._queue_index = 0
        self._queue_playlist_id = None

    @_on_gui_thread
    def next_track(self) -> bool:
        """Plays the next song in the queue, skipping songs no longer in the library; False at the end."""
        if not self._queue or self._queue_index + 1 >= len(self._queue):
            return False
        self._queue_index += 1
        track = self.get_track(self._queue[self._queue_index])
        if track is None:
            return self.next_track()
        return self._load_track_into_player(track)

    @_on_gui_thread
    def previous_track(self) -> bool:
        """Plays the song before, skipping ones no longer in the library; False at the start."""
        if not self._queue or self._queue_index <= 0:
            return False
        self._queue_index -= 1
        track = self.get_track(self._queue[self._queue_index])
        if track is None:
            return self.previous_track()
        return self._load_track_into_player(track)

    @_on_gui_thread
    def seek(self, position_seconds: float) -> None:
        """Jumps to a position in the song, in seconds."""
        if self._player is not None:
            self._player.setPosition(int(position_seconds * 1000))

    @_on_gui_thread
    def set_volume(self, percent: int) -> None:
        """Sets the volume (0-100), remembered as music.last_volume."""
        percent = max(0, min(100, percent))
        self._ensure_player()
        self._audio_output.setVolume(percent / 100.0)
        self.context.config.set("music.last_volume", percent)

    @_on_gui_thread
    def now_playing(self) -> Optional[NowPlaying]:
        """What's playing (or paused) now with its position and queue place, or None when nothing is."""
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
