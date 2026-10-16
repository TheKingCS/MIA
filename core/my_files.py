"""
core.my_files
===============

Files on the web (Zac, 2026-10-16: the Files app was empty on the phone).
Each person has their own MIA files folder, `my_files/` inside their own
data folder (core/personal_data.py), the same folder as their journal:
upload from the phone, open, make folders, rename, delete. It is never
the computer's whole disk: MIA's server can be reachable from the phone
(Tailscale), and a page on a phone must not be able to browse or delete
anything else on the machine. The desktop Files app keeps its full file
manager.

Every path a request names is relative to that folder and is checked to
stay inside it (no "..", no absolute paths, no links out).
"""

from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path

FOLDER = "my_files"
MAX_UPLOAD = 50 * 1024 * 1024
_BAD = set('<>:"|?*\\/') | {chr(c) for c in range(32)}


def clean_name(name: str) -> str:
    """Pure logic. A file or folder name as typed, made safe, or ValueError."""
    name = str(name or "").strip().strip(".").strip()
    if not name:
        raise ValueError("Give it a name.")
    if any(ch in _BAD for ch in name) or name in (".", ".."):
        raise ValueError("A name can't have / \\ : * ? \" < > | in it.")
    if len(name) > 120:
        raise ValueError("That name is too long.")
    return name


def kind_of(name: str) -> str:
    """Pure logic. What a file is, for its icon and how it opens."""
    ext = Path(name).suffix.lower()
    if ext in (".jpg", ".jpeg", ".png", ".gif", ".webp", ".heic", ".bmp"):
        return "image"
    if ext == ".pdf":
        return "pdf"
    if ext in (".mp3", ".m4a", ".wav", ".ogg", ".flac", ".aac"):
        return "audio"
    if ext in (".mp4", ".mov", ".webm", ".mkv"):
        return "video"
    if ext in (".txt", ".md", ".csv", ".json", ".log"):
        return "text"
    return "file"


def size_text(size: int) -> str:
    """Pure logic. 1536 -> "1.5 KB"."""
    value = float(size)
    for unit in ("bytes", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            return f"{int(value)} bytes" if unit == "bytes" else f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} GB"


def _changed() -> None:
    """Screens re-read on the live version (core/live.py); file changes
    don't go through atomic_write_text, so they move it themselves."""
    from core.live import bump

    bump()


class MyFiles:
    def __init__(self, root: Path) -> None:
        self.root = Path(root)

    @classmethod
    def for_context(cls, context) -> "MyFiles":
        journal = getattr(context, "journal", None)
        if journal is None or getattr(journal, "data_dir", None) is None:
            raise ValueError("Files aren't set up on this MIA.")
        return cls(Path(journal.data_dir) / FOLDER)

    def resolve(self, relative: str) -> Path:
        """The real path for a relative one, never outside the folder."""
        self.root.mkdir(parents=True, exist_ok=True)
        rel = str(relative or "").replace("\\", "/").strip("/")
        if rel.startswith("/") or any(part in ("..",) for part in rel.split("/")):
            raise ValueError("That isn't in your files.")
        path = (self.root / rel).resolve() if rel else self.root.resolve()
        root = self.root.resolve()
        if path != root and root not in path.parents:
            raise ValueError("That isn't in your files.")
        return path

    def relative(self, path: Path) -> str:
        return path.resolve().relative_to(self.root.resolve()).as_posix()

    def listing(self, folder: str = "") -> dict:
        here = self.resolve(folder)
        if not here.is_dir():
            raise ValueError("That folder isn't there anymore.")
        folders, files = [], []
        for entry in sorted(here.iterdir(), key=lambda p: p.name.lower()):
            if entry.is_symlink():
                continue
            stat = entry.stat()
            when = datetime.fromtimestamp(stat.st_mtime).date().isoformat()
            if entry.is_dir():
                folders.append({"name": entry.name, "path": self.relative(entry), "count": sum(1 for _ in entry.iterdir()),
                                "modified": when})
            else:
                files.append({"name": entry.name, "path": self.relative(entry), "kind": kind_of(entry.name),
                              "size": stat.st_size, "size_text": size_text(stat.st_size), "modified": when})
        rel = "" if here == self.root.resolve() else self.relative(here)
        crumbs = [{"name": "My Files", "path": ""}]
        so_far = []
        for part in [p for p in rel.split("/") if p]:
            so_far.append(part)
            crumbs.append({"name": part, "path": "/".join(so_far)})
        total = sum(p.stat().st_size for p in self.root.rglob("*") if p.is_file() and not p.is_symlink())
        return {"path": rel, "crumbs": crumbs, "folders": folders, "files": files,
                "used": total, "used_text": size_text(total)}

    def make_folder(self, folder: str, name: str) -> str:
        target = self.resolve(folder) / clean_name(name)
        if target.exists():
            raise ValueError(f"There's already something called {target.name} here.")
        target.mkdir(parents=True)
        _changed()
        return target.name

    def save(self, folder: str, name: str, data: bytes) -> str:
        """Saves an upload; a name already used gets " (2)" added."""
        if len(data) > MAX_UPLOAD:
            raise ValueError("That file is over 50 MB.")
        here = self.resolve(folder)
        if not here.is_dir():
            raise ValueError("That folder isn't there anymore.")
        name = clean_name(Path(str(name)).name)
        target, n = here / name, 2
        while target.exists():
            target = here / f"{Path(name).stem} ({n}){Path(name).suffix}"
            n += 1
        target.write_bytes(data)
        _changed()
        return self.relative(target)

    def file(self, relative: str) -> Path:
        path = self.resolve(relative)
        if not path.is_file() or path.is_symlink():
            raise ValueError("That file isn't there anymore.")
        return path

    def is_folder(self, relative: str) -> bool:
        path = self.resolve(relative)
        if path == self.root.resolve():
            raise ValueError("That's your whole files folder.")
        if not path.exists():
            raise ValueError("That isn't there anymore.")
        return path.is_dir()

    def rename(self, relative: str, name: str) -> str:
        path = self.resolve(relative)
        if path == self.root.resolve() or not path.exists():
            raise ValueError("That isn't there anymore.")
        target = path.with_name(clean_name(name))
        if target.exists():
            raise ValueError(f"There's already something called {target.name} here.")
        path.rename(target)
        _changed()
        return self.relative(target)

    def delete(self, relative: str) -> None:
        if self.is_folder(relative):
            shutil.rmtree(self.resolve(relative))
        else:
            self.resolve(relative).unlink()
        _changed()
