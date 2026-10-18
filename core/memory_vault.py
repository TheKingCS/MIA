"""
core.memory_vault
===================

The memory vault (DEC-0030 phase E, Zac 2026-10-18): the phone's photos
and videos, kept safe on the home computer, so the phone can let them go.

**On the phone** (MemoryVault, a personal store, `memory_vault.json`):
MIA reads the camera roll (DCIM, Pictures, Movies; `vault.sources` in
the config elsewhere) once it's switched on and Android allows it. Each
photo or video is known by its fingerprint (SHA-256 of the file), so the
same photo in two folders is one memory with two copies, and sending it
again is nothing. Its date and place come from the photo itself (EXIF),
else its name (IMG_20261018_101530.jpg), else the file's time.

**To the computer** (VaultLoop): whenever the phone can reach the PC it's
linked to (core/home_link.py), and only on Wi-Fi unless the person says
otherwise, each photo goes over in pieces (CHUNK_BYTES), oldest first. A
piece that didn't arrive is sent again from where it stopped; the PC
checks the whole file's fingerprint before it keeps it (VaultShelf).

**Letting go, only ever an offer.** MIA never deletes anything. It
offers to free space for photos and videos that are older than
`vault.keep_days` and that the computer has just confirmed it holds
(checked again, file by file, right before the offer); Android then
asks the person itself and moves them to its Trash (recoverable for 30
days). Exact copies on the phone can go without the PC (one copy
stays). In a burst (photos seconds apart) MIA suggests the best shot:
the sharpest, best-exposed one when the PC has looked at them
(VaultShelf.scores, with Pillow), else the largest file.

**Linked to your life.** Each day's photos show what happened that day
(the history, core/life_events.py) and the trip they were taken on
(expeditions); the Chronicle counts each week's photos.

Children's accounts don't have the vault (not in CHILD_APPS).
"""

from __future__ import annotations

import json
import os
import re
import struct
import threading
import time
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Iterable, Optional

from core.atomic_write import atomic_write_text
from core.logger import get_logger

log = get_logger(__name__)

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
FILE_NAME = "memory_vault.json"
PHOTO_EXT = frozenset({".jpg", ".jpeg", ".png", ".heic", ".heif", ".webp", ".gif", ".dng"})
VIDEO_EXT = frozenset({".mp4", ".mov", ".3gp", ".mkv", ".webm", ".m4v"})
CHUNK_BYTES = 8 * 1024 * 1024
BURST_SECONDS = 2
SCAN_BUDGET_BYTES = 400 * 1024 * 1024  # fingerprinted per round, so a big camera roll doesn't stall the phone
SEND_SECONDS = 50  # per round
LOOP_SECONDS = 60
DEFAULT_KEEP_DAYS = 30
CAMERA_FOLDERS = ("DCIM", "Pictures", "Movies")
_NAME_DATE = re.compile(r"(20\d\d)[-_]?([01]\d)[-_]?([0-3]\d)[-_ T]?([0-2]\d)[-_.]?([0-5]\d)[-_.]?([0-5]\d)")


def kind_of(name: str) -> str:
    ext = Path(name).suffix.lower()
    return "photo" if ext in PHOTO_EXT else "video" if ext in VIDEO_EXT else ""


# ------------------------------------------------------------------ pure logic: what a photo says about itself


def exif_info(head: bytes) -> dict:
    """Pure logic. {"taken_at", "lat", "lon"} from a JPEG's EXIF (the first
    part of the file is enough), whatever of them it has."""
    from core.world_map import exif_gps

    out: dict = {}
    where = exif_gps(head)
    if where:
        out["lat"], out["lon"] = where
    taken = _exif_date(head)
    if taken:
        out["taken_at"] = taken
    return out


def _exif_date(data: bytes) -> str:
    try:
        if data[:2] != b"\xff\xd8":
            return ""
        i = 2
        while i + 4 <= len(data):
            if data[i] != 0xFF:
                return ""
            marker = data[i + 1]
            size = struct.unpack(">H", data[i + 2:i + 4])[0]
            if marker == 0xE1 and data[i + 4:i + 10] == b"Exif\x00\x00":
                return _tiff_date(data[i + 10:i + 2 + size])
            if marker in (0xDA, 0xD9):
                return ""
            i += 2 + size
    except (struct.error, IndexError, ValueError):
        return ""
    return ""


def _tiff_date(t: bytes) -> str:
    endian = "<" if t[:2] == b"II" else ">"

    def entries(offset):
        count = struct.unpack(endian + "H", t[offset:offset + 2])[0]
        for k in range(count):
            e = offset + 2 + 12 * k
            tag, kind, n = struct.unpack(endian + "HHI", t[e:e + 8])
            yield tag, kind, n, e + 8

    def text(n, v):
        at = struct.unpack(endian + "I", t[v:v + 4])[0] if n > 4 else v
        return t[at:at + n].split(b"\x00")[0].decode("ascii", "replace")

    ifd0 = struct.unpack(endian + "I", t[4:8])[0]
    found = {}
    for tag, _kind, n, v in entries(ifd0):
        if tag == 0x0132:
            found["dt"] = text(n, v)
        elif tag == 0x8769:
            sub = struct.unpack(endian + "I", t[v:v + 4])[0]
            for tag2, _k2, n2, v2 in entries(sub):
                if tag2 == 0x9003:
                    found["original"] = text(n2, v2)
    raw = found.get("original") or found.get("dt") or ""
    try:
        return datetime.strptime(raw.strip(), "%Y:%m:%d %H:%M:%S").isoformat()
    except ValueError:
        return ""


def exif_thumbnail(head: bytes) -> Optional[bytes]:
    """Pure logic. The small preview most cameras put inside a JPEG (EXIF
    IFD1), so a screen of photos never loads every full-size picture."""
    try:
        if head[:2] != b"\xff\xd8":
            return None
        i = 2
        while i + 4 <= len(head):
            if head[i] != 0xFF:
                return None
            marker = head[i + 1]
            size = struct.unpack(">H", head[i + 2:i + 4])[0]
            if marker == 0xE1 and head[i + 4:i + 10] == b"Exif\x00\x00":
                t = head[i + 10:i + 2 + size]
                endian = "<" if t[:2] == b"II" else ">"
                ifd0 = struct.unpack(endian + "I", t[4:8])[0]
                count = struct.unpack(endian + "H", t[ifd0:ifd0 + 2])[0]
                ifd1 = struct.unpack(endian + "I", t[ifd0 + 2 + 12 * count:ifd0 + 6 + 12 * count])[0]
                if not ifd1:
                    return None
                found = {}
                for k in range(struct.unpack(endian + "H", t[ifd1:ifd1 + 2])[0]):
                    e = ifd1 + 2 + 12 * k
                    tag = struct.unpack(endian + "H", t[e:e + 2])[0]
                    if tag in (0x0201, 0x0202):
                        found[tag] = struct.unpack(endian + "I", t[e + 8:e + 12])[0]
                at, n = found.get(0x0201), found.get(0x0202)
                thumb = t[at:at + n] if at and n else b""
                return thumb if thumb[:2] == b"\xff\xd8" and len(thumb) == n else None
            if marker in (0xDA, 0xD9):
                return None
            i += 2 + size
    except (struct.error, IndexError):
        return None
    return None


def thumbnail(path: Path) -> tuple[bytes, str]:
    """(bytes, media type) of a small picture of a photo: Pillow's when
    it's here (the PC), else the photo's own preview, else the photo."""
    try:
        from PIL import Image

        import io

        with Image.open(path) as img:
            img.draft("RGB", (480, 480))
            img = img.convert("RGB")
            img.thumbnail((480, 480))
            out = io.BytesIO()
            img.save(out, "JPEG", quality=80)
            return out.getvalue(), "image/jpeg"
    except Exception:
        pass
    with open(path, "rb") as f:
        head = f.read(256 * 1024)
    small = exif_thumbnail(head)
    if small:
        return small, "image/jpeg"
    ext = path.suffix.lower().lstrip(".")
    return path.read_bytes(), "image/" + ("jpeg" if ext in ("jpg", "jpeg") else ext)


def date_from_name(name: str) -> str:
    """Pure logic. IMG_20261018_101530.jpg, PXL_20261018_101530123.jpg,
    Screenshot_2026-10-18-10-15-30.png → 2026-10-18T10:15:30."""
    m = _NAME_DATE.search(name)
    if not m:
        return ""
    try:
        return datetime(*(int(g) for g in m.groups())).isoformat()
    except ValueError:
        return ""


def bursts(items: Iterable[dict], gap: int = BURST_SECONDS) -> list[list[dict]]:
    """Pure logic. Photos taken within `gap` seconds of the one before,
    two or more: a burst. Oldest first."""
    photos = sorted((i for i in items if i.get("kind") == "photo" and i.get("taken_at")), key=lambda i: i["taken_at"])
    groups, run, last = [], [], None
    for item in photos:
        try:
            at = datetime.fromisoformat(item["taken_at"])
        except ValueError:
            continue
        if last is not None and (at - last).total_seconds() <= gap:
            run.append(item)
        else:
            if len(run) >= 2:
                groups.append(run)
            run = [item]
        last = at
    if len(run) >= 2:
        groups.append(run)
    return groups


def best_of(group: list[dict]) -> dict:
    """Pure logic. The suggested keeper: the best score the PC gave
    (sharp, well exposed) when it looked at all of them, else the largest
    file (in a burst of the same scene, more detail makes a bigger JPEG)."""
    if all(isinstance(i.get("score"), (int, float)) for i in group):
        return max(group, key=lambda i: (i["score"], i.get("size", 0)))
    return max(group, key=lambda i: i.get("size", 0))


def score_photo(path: Path) -> Optional[float]:
    """How good a photo looks, 0..1: sharpness (edges) and exposure (not
    too dark, too bright or clipped). Needs Pillow (the PC has it); None
    without it or for a format it can't read."""
    try:
        from PIL import Image, ImageFilter, ImageStat
    except ImportError:
        return None
    try:
        with Image.open(path) as img:
            img.draft("L", (320, 320))
            gray = img.convert("L")
            gray.thumbnail((320, 320))
            edges = gray.filter(ImageFilter.Kernel((3, 3), (0, 1, 0, 1, -4, 1, 0, 1, 0), 1, 128))
            w, h = edges.size
            edges = edges.crop((2, 2, w - 2, h - 2)) if w > 8 and h > 8 else edges  # the filter's own border isn't the photo
            sharp = min(1.0, ImageStat.Stat(edges).var[0] / 400.0)
            hist = gray.histogram()
            total = sum(hist) or 1
            mean = sum(i * n for i, n in enumerate(hist)) / total
            clipped = (sum(hist[:6]) + sum(hist[250:])) / total
            exposure = max(0.0, 1.0 - abs(mean - 120) / 120 - clipped)
            return round(0.7 * sharp + 0.3 * exposure, 4)
    except Exception:  # a damaged or unusual file: no score, never a crash
        return None


# ------------------------------------------------------------------ where the photos are


def camera_roll() -> list[Path]:
    """The phone's camera roll folders (Android), else none."""
    try:
        from java import jclass  # Chaquopy, on the phone only
    except ImportError:
        return []
    try:
        root = Path(str(jclass("android.os.Environment").getExternalStorageDirectory().getAbsolutePath()))
    except Exception:
        root = Path("/storage/emulated/0")
    return [root / name for name in CAMERA_FOLDERS]


def on_metered_network() -> bool:
    """True on mobile data (Android says the network is metered). Off the
    phone, or when Android can't say, False."""
    try:
        from java import jclass
    except ImportError:
        return False
    try:
        app = jclass("com.chaquo.python.Python").getPlatform().getApplication()
        return bool(app.getSystemService("connectivity").isActiveNetworkMetered())
    except Exception:
        return False


def sources(context) -> list[Path]:
    configured = context.config.get("vault.sources", None)
    if configured:
        return [Path(p).expanduser() for p in configured]
    return camera_roll()


def _setting(context, key: str, default):
    from core.person_settings import get

    try:
        return get(context, key, default)
    except Exception:
        return default


def keep_days(context) -> int:
    try:
        return max(0, int(_setting(context, "vault.keep_days", DEFAULT_KEEP_DAYS)))
    except (TypeError, ValueError):
        return DEFAULT_KEEP_DAYS


def is_on(context) -> bool:
    return bool(_setting(context, "vault.on", False))


def wifi_only(context) -> bool:
    return bool(_setting(context, "vault.wifi_only", True))


# ------------------------------------------------------------------ the phone's catalog


class MemoryVault:
    """What's on this phone's camera roll, by fingerprint, and what the
    home computer already holds."""

    def __init__(self, context=None, data_dir: Optional[Path] = None) -> None:
        self.context = context
        self.data_dir = Path(data_dir) if data_dir is not None else _DATA_DIR
        self._file = self.data_dir / FILE_NAME
        self.items: dict[str, dict] = {}
        self.paths: dict[str, list] = {}  # path -> [size, mtime_ns, sha]
        self.freed: list[dict] = []
        self.status: dict = {}
        self._load()

    def _load(self) -> None:
        self.items, self.paths, self.freed, self.status = {}, {}, [], {}
        if not self._file.exists():
            return
        try:
            data = json.loads(self._file.read_text(encoding="utf-8"))
            self.items = dict(data.get("items") or {})
            self.paths = dict(data.get("paths") or {})
            self.freed = list(data.get("freed") or [])
            self.status = dict(data.get("status") or {})
        except (OSError, ValueError, AttributeError):
            log.exception("Couldn't read %s; the vault starts its list again (your photos are untouched).", FILE_NAME)

    def save(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_text(self._file, json.dumps({"version": 1, "items": self.items, "paths": self.paths,
                                                  "freed": self.freed[-50:], "status": self.status}))

    # -- reading
    def on_phone(self, item: dict) -> list[str]:
        return [p for p in item.get("sources") or [] if p in self.paths]

    def waiting(self) -> list[dict]:
        """Still only on the phone, oldest first."""
        out = [i for i in self.items.values() if not i.get("on_pc") and self.on_phone(i)]
        return sorted(out, key=lambda i: i.get("taken_at") or "")

    def file_of(self, sha: str) -> Optional[Path]:
        item = self.items.get(sha)
        for p in self.on_phone(item) if item else []:
            if Path(p).is_file():
                return Path(p)
        return None


def scan(context, vault: MemoryVault, roots: Optional[list[Path]] = None, budget: int = SCAN_BUDGET_BYTES,
         lock=None) -> dict:
    """Look through the camera roll: new and changed files are
    fingerprinted (up to `budget` bytes a round), gone ones forgotten
    (a memory the PC holds stays in the list, marked as no longer on the
    phone). Returns {seen, new, complete}."""
    from core.sync import file_digest

    lock = lock or threading.Lock()
    roots = roots if roots is not None else sources(context)
    seen: dict[str, list] = {}
    fresh: list[tuple[str, int, int]] = []
    for root in roots:
        if not root.is_dir():
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if not d.startswith(".")]  # .thumbnails, .trashed-...
            for name in filenames:
                if name.startswith(".") or not kind_of(name):
                    continue
                path = os.path.join(dirpath, name)
                try:
                    st = os.stat(path)
                except OSError:
                    continue
                known = vault.paths.get(path)
                if known and known[0] == st.st_size and known[1] == st.st_mtime_ns:
                    seen[path] = known
                else:
                    fresh.append((path, st.st_size, st.st_mtime_ns))
    spent, new, complete = 0, 0, True
    added: dict[str, tuple[list, dict]] = {}
    for path, size, mtime_ns in sorted(fresh, key=lambda f: f[0]):
        if spent and spent + size > budget:
            complete = False
            break
        try:
            sha = file_digest(Path(path))
            with open(path, "rb") as f:
                head = f.read(256 * 1024)
        except OSError:
            continue
        spent += size
        name = os.path.basename(path)
        info = exif_info(head) if kind_of(name) == "photo" else {}
        taken = info.get("taken_at") or date_from_name(name) or \
            datetime.fromtimestamp(mtime_ns / 1e9).isoformat(timespec="seconds")
        added[path] = ([size, mtime_ns, sha], {"sha": sha, "name": name, "size": size, "kind": kind_of(name),
                                               "taken_at": taken, **({"lat": info["lat"], "lon": info["lon"]}
                                                                     if "lat" in info else {})})
    with lock:
        if complete:
            gone = [p for p in vault.paths if p not in seen and p not in added]
        else:  # an unfinished round: only forget what's really gone
            gone = [p for p in vault.paths if p not in seen and p not in added and not os.path.exists(p)]
        for path in gone:
            del vault.paths[path]
        for path, (entry, item) in added.items():
            vault.paths[path] = entry
            old = vault.items.get(item["sha"])
            if old is None:
                vault.items[item["sha"]] = {**item, "sources": [path], "on_pc": False}
                new += 1
            elif path not in old.setdefault("sources", []):
                old["sources"].append(path)
        for sha, item in list(vault.items.items()):
            item["sources"] = [p for p in item.get("sources") or [] if p in vault.paths]
            if not item["sources"] and not item.get("on_pc"):
                del vault.items[sha]  # gone from the phone before it reached the PC: nothing to keep a record of
        vault.status["scanned_at"] = datetime.now().isoformat(timespec="seconds")
        if gone or added:
            vault.save()
    return {"seen": len(seen) + len(added), "new": new, "complete": complete}


# ------------------------------------------------------------------ the phone sending

class Stopped(Exception):
    pass


def send(context, vault: MemoryVault, call=None, seconds: float = SEND_SECONDS, lock=None,
         clock=time.monotonic) -> dict:
    """Send what's waiting to the PC for up to `seconds`. First asks which
    the PC already has (sending again is nothing), then sends the rest a
    piece at a time, from where an earlier try stopped."""
    from core.home_link import home_call

    call = call or home_call
    lock = lock or threading.Lock()
    start = clock()
    waiting = vault.waiting()
    done = {"sent": 0, "already": 0, "bytes": 0}
    if not waiting:
        return done
    have = {}
    for k in range(0, len(waiting), 500):
        batch = waiting[k:k + 500]
        have.update(call(context, "/api/vault/have", {"shas": [i["sha"] for i in batch]}, timeout=30).get("have", {}))
    with lock:
        for item in waiting:
            if (have.get(item["sha"]) or {}).get("stored"):
                item["on_pc"], item["sent_at"] = True, datetime.now().isoformat(timespec="seconds")
                done["already"] += 1
        if done["already"]:
            vault.save()
    for item in waiting:
        if item.get("on_pc"):
            continue
        if clock() - start > seconds:
            break
        path = vault.file_of(item["sha"])
        if path is None:
            continue
        offset = int((have.get(item["sha"]) or {}).get("partial") or 0)
        size = path.stat().st_size
        meta = f"&size={size}&name={_q(item.get('name'))}&taken_at={_q(item.get('taken_at'))}&kind={item.get('kind')}"
        answer = {}
        with open(path, "rb") as f:
            while offset < size or size == 0:
                f.seek(offset)  # the PC says where it is: after a cut, it carries on from there
                chunk = f.read(CHUNK_BYTES)
                answer = call(context, f"/api/vault/blob/{item['sha']}?offset={offset}{meta}", timeout=120,
                              method="PUT", body=chunk, headers={"Content-Type": "application/octet-stream"})
                offset = int(answer.get("partial") or offset + len(chunk))
                done["bytes"] += len(chunk)
                if answer.get("stored") or size == 0:
                    break
                if clock() - start > seconds * 3:  # a slow link: carry on next round from here
                    raise Stopped()
        if answer.get("stored"):
            with lock:
                item["on_pc"], item["sent_at"] = True, datetime.now().isoformat(timespec="seconds")
                vault.status["last_sent"] = item["sent_at"]
                vault.save()
            done["sent"] += 1
    return done


def _q(text) -> str:
    import urllib.parse

    return urllib.parse.quote(str(text or ""), safe="")


def fetch_scores(context, vault: MemoryVault, call=None, lock=None) -> int:
    """Ask the PC to look at the photos in bursts it holds (sharpness and
    exposure), so the best shot is the best one, not just the biggest."""
    from core.home_link import home_call

    call = call or home_call
    lock = lock or threading.Lock()
    want = [i["sha"] for group in bursts(vault.items.values()) for i in group
            if i.get("on_pc") and "score" not in i]
    if not want:
        return 0
    got = call(context, "/api/vault/scores", {"shas": want[:200]}, timeout=120).get("scores", {})
    with lock:
        for sha, value in got.items():
            if sha in vault.items:
                vault.items[sha]["score"] = value
        vault.save()
    return len(got)


class VaultLoop:
    """Every LOOP_SECONDS while the vault is on: read the camera roll, and
    when the PC is reachable (on Wi-Fi unless the person said otherwise)
    send what's waiting. A background thread, like core/sync.SyncLoop."""

    def __init__(self, context, lock) -> None:
        self.context, self.lock = context, lock
        self._stop = threading.Event()
        self._wake = threading.Event()
        self.thread: Optional[threading.Thread] = None

    def start(self) -> None:
        if self.thread is None:
            self.thread = threading.Thread(target=self._run, name="mia-vault", daemon=True)
            self.thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._wake.set()

    def poke(self) -> None:
        self._wake.set()

    def _run(self) -> None:
        first = True
        while not self._stop.is_set():
            if not first:
                self._wake.wait(LOOP_SECONDS)
            first = False
            self._wake.clear()
            if self._stop.is_set():
                break
            try:
                round_(self.context, self.lock)
            except Exception:
                log.exception("Memory vault round failed.")


def owner_vault(context):
    """The vault of whoever this phone belongs to (its signed-in person)."""
    from core.sync import owner

    pid = owner(context)
    if pid is None:
        return None, None
    personal = getattr(context, "personal_data", None)
    view = personal.view(pid) if personal is not None else context
    return view, getattr(view, "memory_vault", None)


def round_(context, lock, call=None) -> dict:
    """One round of the loop (tests call it directly)."""
    from core.home_link import HomeLinkError, linked

    view, vault = owner_vault(context)
    if vault is None or not is_on(view):
        return {"state": "off"}
    found = scan(view, vault, lock=lock)
    if not linked(context):
        state = "not_linked"
    elif wifi_only(view) and on_metered_network():
        state = "waiting_wifi"
    else:
        try:
            sent = send(context, vault, call=call, lock=lock)
            fetch_scores(context, vault, call=call, lock=lock)
            state = "sending" if vault.waiting() else "safe"
            found.update(sent)
        except (HomeLinkError, Stopped, OSError) as problem:
            state = "waiting_pc" if not isinstance(problem, Stopped) else "sending"
    with lock:
        if vault.status.get("state") != state:
            vault.status["state"] = state
            vault.save()
    return {"state": state, **found}


# ------------------------------------------------------------------ the computer keeping them


class VaultShelf:
    """Where the PC keeps a person's memories: `vault/YYYY/MM/` in their
    folder, each file named by its date and fingerprint, with an index
    (`vault/index.json`) of what's there. Never deletes anything."""

    def __init__(self, folder: Path) -> None:
        self.folder = Path(folder)
        self._index_file = self.folder / "index.json"
        self._lock = threading.Lock()
        try:
            self.index: dict[str, dict] = json.loads(self._index_file.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            self.index = {}

    def _save(self) -> None:
        self.folder.mkdir(parents=True, exist_ok=True)
        atomic_write_text(self._index_file, json.dumps(self.index, indent=1))

    def _part(self, sha: str) -> Path:
        return self.folder / ".incoming" / f"{sha}.part"

    def path_of(self, sha: str) -> Optional[Path]:
        entry = self.index.get(sha)
        path = self.folder / entry["path"] if entry else None
        return path if path is not None and path.is_file() else None

    def have(self, shas: Iterable[str]) -> dict:
        out = {}
        for sha in shas:
            sha = _clean_sha(sha)
            part = self._part(sha)
            out[sha] = {"stored": self.path_of(sha) is not None,
                        "partial": part.stat().st_size if part.is_file() else 0}
        return out

    def receive(self, sha: str, offset: int, data: bytes, size: int, name: str = "", taken_at: str = "",
                kind: str = "") -> dict:
        """One piece of a file, at `offset`. The last piece completes it:
        its fingerprint is checked, then it's put on the shelf."""
        from core.sync import file_digest

        sha = _clean_sha(sha)
        with self._lock:
            if self.path_of(sha) is not None:
                return {"stored": True, "partial": size}
            part = self._part(sha)
            part.parent.mkdir(parents=True, exist_ok=True)
            have = part.stat().st_size if part.is_file() else 0
            if offset != have:
                return {"stored": False, "partial": have, "resend_from": have}
            with open(part, "ab") as f:
                f.write(data)
            have += len(data)
            if have < size:
                return {"stored": False, "partial": have}
            if have > size or file_digest(part) != sha:
                part.unlink()
                raise ValueError("That file arrived damaged; it's sent again from the start.")
            when = _parse(taken_at) or datetime.now()
            ext = Path(name).suffix.lower() if kind_of(name) else ""
            rel = Path(f"{when:%Y}") / f"{when:%m}" / f"{when:%Y%m%d_%H%M%S}_{sha[:10]}{ext}"
            target = self.folder / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            os.replace(part, target)
            self.index[sha] = {"path": rel.as_posix(), "size": size, "name": Path(name).name, "taken_at": taken_at,
                               "kind": kind or kind_of(name), "stored_at": datetime.now().isoformat(timespec="seconds")}
            self._save()
            return {"stored": True, "partial": size}

    def verify(self, shas: Iterable[str]) -> dict:
        """Read each file again, now: {sha: True} only when it's here and whole."""
        from core.sync import file_digest

        out = {}
        for sha in shas:
            sha = _clean_sha(sha)
            path = self.path_of(sha)
            try:
                out[sha] = path is not None and file_digest(path) == sha
            except OSError:
                out[sha] = False
        return out

    def scores(self, shas: Iterable[str]) -> dict:
        out, changed = {}, False
        for sha in shas:
            sha = _clean_sha(sha)
            entry = self.index.get(sha)
            path = self.path_of(sha)
            if entry is None or path is None:
                continue
            if "score" not in entry:
                entry["score"] = score_photo(path)
                changed = True
            if entry["score"] is not None:
                out[sha] = entry["score"]
        if changed:
            with self._lock:
                self._save()
        return out


_SHELVES: dict[str, VaultShelf] = {}
_SHELVES_LOCK = threading.Lock()


def shelf_for(context, profile_id: str) -> VaultShelf:
    """The person's shelf on this computer (one per folder, so its index
    and its lock are shared by every request)."""
    personal = getattr(context, "personal_data", None)
    folder = Path(personal.folder(profile_id) if personal is not None else _DATA_DIR / "profiles" / profile_id) / "vault"
    with _SHELVES_LOCK:
        shelf = _SHELVES.get(str(folder))
        if shelf is None:
            shelf = _SHELVES[str(folder)] = VaultShelf(folder)
        return shelf


def _clean_sha(sha: str) -> str:
    sha = str(sha or "").lower()
    if not re.fullmatch(r"[0-9a-f]{64}", sha):
        raise ValueError("That isn't a photo's fingerprint.")
    return sha


def _parse(text: str) -> Optional[datetime]:
    try:
        return datetime.fromisoformat(str(text)) if text else None
    except ValueError:
        return None


# ------------------------------------------------------------------ letting go (always an offer)


def free_offer(context, vault: MemoryVault, today: Optional[date] = None) -> dict:
    """What could go from the phone: photos and videos older than
    keep_days that the PC holds. Only an offer; nothing is checked with
    the PC here (free_plan does, right before)."""
    today = today or date.today()
    cutoff = (today - timedelta(days=keep_days(context))).isoformat()
    items = [i for i in vault.items.values() if i.get("on_pc") and vault.on_phone(i) and (i.get("taken_at") or "") < cutoff]
    return {"count": len(items), "bytes": sum(i.get("size", 0) * len(vault.on_phone(i)) for i in items),
            "older_than_days": keep_days(context), "shas": [i["sha"] for i in items]}


def copies_offer(vault: MemoryVault) -> dict:
    """The same photo more than once on the phone: all but one copy."""
    extra = []
    for item in vault.items.values():
        here = vault.on_phone(item)
        extra += [(p, item.get("size", 0)) for p in sorted(here)[1:]]
    return {"count": len(extra), "bytes": sum(s for _p, s in extra), "paths": [p for p, _s in extra]}


def burst_offers(vault: MemoryVault, limit: int = 12) -> list[dict]:
    out = []
    for group in reversed(bursts(vault.items.values())):
        best = best_of(group)
        others = [i for i in group if i["sha"] != best["sha"]]
        out.append({"id": group[0]["sha"][:12], "day": group[0]["taken_at"][:10], "count": len(group),
                    "best": best["sha"], "scored": all("score" in i for i in group),
                    "others": [i["sha"] for i in others],
                    "others_on_phone": sum(1 for i in others if vault.on_phone(i)),
                    "others_safe": all(i.get("on_pc") for i in others),
                    "bytes": sum(i.get("size", 0) for i in others if vault.on_phone(i))})
        if len(out) >= limit:
            break
    return out


def free_plan(context, vault: MemoryVault, what: str, call=None, today: Optional[date] = None) -> dict:
    """The exact files Android will be asked to move to its Trash, for
    "old", "copies" or "burst:<id>". For anything that isn't an exact
    copy, the PC is asked right now to read each file again; only the
    ones it confirms whole are in the plan."""
    from core.home_link import home_call

    call = call or home_call
    if what == "copies":
        offer = copies_offer(vault)
        return {"paths": offer["paths"], "count": offer["count"], "bytes": offer["bytes"], "checked": 0}
    if what == "old":
        shas = free_offer(context, vault, today)["shas"]
    elif what.startswith("burst:"):
        found = next((b for b in burst_offers(vault, limit=10_000) if b["id"] == what[6:]), None)
        if found is None:
            raise ValueError("That burst isn't here any more.")
        shas = [s for s in found["others"] if vault.items[s].get("on_pc")]
    else:
        raise ValueError("Free what?")
    confirmed = {}
    for k in range(0, len(shas), 200):
        confirmed.update(call(context, "/api/vault/verify", {"shas": shas[k:k + 200]}, timeout=600).get("ok", {}))
    safe = [s for s in shas if confirmed.get(s) is True]
    paths = [p for s in safe for p in vault.on_phone(vault.items[s])]
    return {"paths": paths, "count": len(safe),
            "bytes": sum(vault.items[s].get("size", 0) * len(vault.on_phone(vault.items[s])) for s in safe),
            "checked": len(shas), "not_confirmed": len(shas) - len(safe)}


def note_freed(context, vault: MemoryVault, paths: list[str], lock=None) -> dict:
    """After Android's own dialog: the files that really went are
    forgotten (the memories stay in the list, on the PC)."""
    lock = lock or threading.Lock()
    gone = [p for p in paths if not os.path.exists(p)]
    with lock:
        size = 0
        for p in gone:
            entry = vault.paths.pop(p, None)
            size += entry[0] if entry else 0
        for item in vault.items.values():
            item["sources"] = [p for p in item.get("sources") or [] if p in vault.paths]
        if gone:
            vault.freed.append({"at": datetime.now().isoformat(timespec="seconds"), "count": len(gone), "bytes": size})
            vault.save()
    return {"count": len(gone), "bytes": size}


# ------------------------------------------------------------------ the screen


STATE_WORDS = {
    "off": "The vault is off.",
    "not_linked": "Waiting for the home computer: link it in Settings → Home Computer.",
    "waiting_wifi": "Waiting for Wi-Fi to copy to the home computer.",
    "waiting_pc": "Waiting for the home computer (it's off, or out of reach).",
    "sending": "Copying to the home computer…",
    "safe": "Everything is safe on the home computer.",
}


def _size(n: int) -> str:
    for unit, step in (("GB", 1 << 30), ("MB", 1 << 20), ("KB", 1 << 10)):
        if n >= step:
            return f"{n / step:.1f} {unit}"
    return f"{n} bytes"


def _day_label(day: str) -> str:
    try:
        d = date.fromisoformat(day)
    except ValueError:
        return day
    return f"{d:%A}, {d:%B} {d.day}, {d:%Y}"


def vault_page(context, month: str = "", today: Optional[date] = None) -> dict:
    """The Memory Vault screen: how much is safe, what could be freed,
    the bursts, and one month of photos by day with what happened then."""
    from core.home_link import linked

    vault = getattr(context, "memory_vault", None)
    if vault is None:
        return {"available": False}
    today = today or date.today()
    items = list(vault.items.values())
    on_phone = [i for i in items if vault.on_phone(i)]
    waiting = vault.waiting()
    state = vault.status.get("state") or ("off" if not is_on(context) else "not_linked")
    if not is_on(context):
        state = "off"
    elif state != "off" and not linked(context):
        state = "not_linked"
    months = sorted({(i.get("taken_at") or "")[:7] for i in items if i.get("taken_at")}, reverse=True)
    month = month if month in months else (months[0] if months else today.strftime("%Y-%m"))
    burst_of = {i["sha"]: b["id"] for b in burst_offers(vault, limit=10_000) for i in
                [vault.items[s] for s in [b["best"]] + b["others"]]}
    best = {b["best"] for b in burst_offers(vault, limit=10_000)}
    shown = sorted((i for i in items if (i.get("taken_at") or "").startswith(month)),
                   key=lambda i: i.get("taken_at") or "", reverse=True)
    days: dict[str, list] = {}
    for item in shown:
        days.setdefault(item["taken_at"][:10], []).append({
            "sha": item["sha"], "kind": item.get("kind"), "name": item.get("name"), "on_pc": bool(item.get("on_pc")),
            "on_phone": bool(vault.on_phone(item)), "copies": len(vault.on_phone(item)),
            "burst": burst_of.get(item["sha"], ""), "best": item["sha"] in best,
            "time": (item.get("taken_at") or "")[11:16]})
    happened = _what_happened(context, month)
    trips = _trips(context)
    free = free_offer(context, vault, today)
    copies = copies_offer(vault)
    return {
        "available": True, "on": is_on(context), "linked": linked(context), "wifi_only": wifi_only(context),
        "keep_days": keep_days(context), "state": state, "state_words": STATE_WORDS.get(state, ""),
        "summary": {"photos": sum(1 for i in items if i.get("kind") == "photo"),
                    "videos": sum(1 for i in items if i.get("kind") == "video"),
                    "on_pc": sum(1 for i in items if i.get("on_pc")), "on_phone": len(on_phone),
                    "waiting": len(waiting), "waiting_size": _size(sum(i.get("size", 0) for i in waiting)),
                    "size": _size(sum(i.get("size", 0) for i in items)),
                    "last_sent": vault.status.get("last_sent", ""), "scanned_at": vault.status.get("scanned_at", "")},
        "free": {"count": free["count"], "size": _size(free["bytes"]), "older_than_days": free["older_than_days"]},
        "copies": {"count": copies["count"], "size": _size(copies["bytes"])},
        "bursts": [{**b, "size": _size(b["bytes"])} for b in burst_offers(vault) if b["others_on_phone"]],
        "freed": [{**f, "size": _size(f.get("bytes", 0))} for f in reversed(vault.freed[-5:])],
        "months": [{"month": m, "label": f"{date.fromisoformat(m + '-01'):%B %Y}",
                    "count": sum(1 for i in items if (i.get("taken_at") or "").startswith(m))} for m in months],
        "month": month,
        "days": [{"day": d, "label": _day_label(d), "items": its, "happened": happened.get(d, [])[:4],
                  "trip": next((t["name"] for t in trips if t["start"] <= d <= (t["end"] or t["start"])), "")}
                 for d, its in days.items()],
    }


def _what_happened(context, month: str) -> dict[str, list[str]]:
    from core.life_events import AUDIT_ONLY, events_for, reversed_ids

    try:
        start = date.fromisoformat(month + "-01")
    except ValueError:
        return {}
    end = (start.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
    try:
        events = events_for(context, start.isoformat(), end.isoformat())
    except Exception:
        log.exception("Vault: reading the history failed")
        return {}
    gone = reversed_ids(events)
    out: dict[str, list[str]] = {}
    for e in events:
        if e.event_id in gone or e.type in AUDIT_ONLY or not e.summary:
            continue
        lines = out.setdefault(e.day, [])
        if e.summary not in lines:
            lines.append(e.summary)
    return out


def _trips(context) -> list[dict]:
    expeditions = getattr(context, "expeditions", None)
    if expeditions is None:
        return []
    return [{"name": x.name, "start": x.start_date, "end": x.end_date} for x in expeditions.all_expeditions()
            if x.start_date]


def photos_between(context, start: str, end: str) -> dict:
    """{count, cover}: the vault's photos taken between two ISO dates (the Chronicle)."""
    vault = getattr(context, "memory_vault", None)
    if vault is None:
        return {"count": 0, "cover": ""}
    hits = [i for i in vault.items.values() if start <= (i.get("taken_at") or "")[:10] <= end]
    photos = [i for i in hits if i.get("kind") == "photo"]
    return {"count": len(hits), "cover": max(photos, key=lambda i: i.get("size", 0))["sha"] if photos else ""}
