"""
core.migration
================

The move to MIA OS, checked (FW-07a: REQ-CMP-002, REQ-CMP-003, REQ-IMP-002, REQ-IMP-005, REQ-IMP-009;
docs/mia_os/MIA_OS_FINAL_MIGRATION_AND_DATA_CONTINUITY_PLAN.md). Before the move, on Windows, `manifest()` records
what he has; after the restore on MIA OS, the same is recorded there and `compare()` names anything that didn't
come across whole. The move stops at the first mismatch (MV-01). After the move, `same_files` hashes again the
very files the before manifest sampled (`manifest(..., like=before)`), so the two samples always compare.

- **Every store** (`store_entry`, `stores`): each .json and .jsonl file under MIA's data folder, its record count and a
  hash of its records in a canonical order (each record as sorted, compact JSON; the records sorted), read the way MIA
  reads it (core/at_rest.open_text), so a store sealed under the Windows key and re-sealed under the new one still
  hashes the same: the hash is of what it holds, never of the bytes on disk.
- **A sample of his files** (`sample_files`): up to N files chosen evenly across the folders given (his Documents,
  Pictures, Desktop... by default), each its path under his home, size and SHA-256.
- **His Windows programs** (`programs`, REQ-CMP-003): the installed programs' names (Windows' own list), each with its
  answer on MIA OS from `LINUX_ANSWERS`, or "no known answer yet" for him to decide.

**Hashes and names, never contents** (the plan's security line): the manifest says nothing a store holds. It's written
beside his backups (core/web_backups.folder), outside the repository and outside MIA's data, never committed.
"""

from __future__ import annotations

from core.data_root import DATA_DIR

import hashlib
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from core.logger import get_logger

log = get_logger(__name__)

VERSION = 1
SAMPLE = 200
BIG = 2 * 1024 ** 3  # a file over 2 GB is sampled by size alone (hashing it would take minutes)
SKIP_DIRS = {".keys", "lab", "history"}  # the key (re-made on MIA OS), the lab's working copies, undo blobs
DEFAULT_FOLDERS = ("Documents", "Pictures", "Desktop", "Music", "Videos")

# What each Windows program he might use becomes on MIA OS (REQ-CMP-003), matched by a word in its name. First match
# wins, so the more specific come first. Nothing here is installed by itself: it's the list he decides from.
LINUX_ANSWERS: tuple[tuple[str, str], ...] = (
    ("microsoft edge", "Edge for Linux (MIA's browser, DEC-0117)"),
    ("google chrome", "Chrome for Linux, or Edge"),
    ("firefox", "Firefox (in Fedora)"),
    ("microsoft office", "LibreOffice, or Office on the web"),
    ("microsoft 365", "LibreOffice, or Office on the web"),
    ("onedrive", "OneDrive on the web, or rclone"),
    ("visual studio code", "VS Code (Microsoft's RPM or Flatpak)"),
    ("visual studio", "VS Code, or JetBrains' Linux IDEs; no Visual Studio on Linux"),
    ("android studio", "Android Studio for Linux"),
    ("steam", "Steam (with Proton for Windows games)"),
    ("epic games", "Heroic Games Launcher"),
    ("discord", "Discord (Flatpak)"),
    ("spotify", "Spotify (Flatpak)"),
    ("obs studio", "OBS Studio (Flatpak)"),
    ("vlc", "VLC (Flatpak)"),
    ("7-zip", "Ark (in KDE)"),
    ("winrar", "Ark (in KDE)"),
    ("notepad++", "Kate (in KDE)"),
    ("python", "Python (in the image)"),
    ("git", "Git (in the image)"),
    ("ollama", "Ollama (in the image)"),
    ("tailscale", "Tailscale (in the image)"),
    ("nvidia", "the driver in the image (NVIDIA's for Fedora)"),
    ("amd software", "the driver in the kernel (AMD's is built in)"),
    ("realtek", "the driver in the kernel"),
    ("intel", "the driver in the kernel"),
    ("zoom", "Zoom for Linux"),
    ("teams", "Teams on the web"),
    ("slack", "Slack (Flatpak)"),
    ("gimp", "GIMP (Flatpak)"),
    ("blender", "Blender (Flatpak)"),
    ("audacity", "Audacity (Flatpak)"),
    ("handbrake", "HandBrake (Flatpak)"),
    ("qbittorrent", "qBittorrent (Flatpak)"),
    ("putty", "the terminal's own ssh"),
    ("winscp", "Dolphin's sftp:// or FileZilla"),
    ("filezilla", "FileZilla (Flatpak)"),
    ("1password", "1password for Linux, or MIA's password vault"),
    ("bitwarden", "Bitwarden (Flatpak), or MIA's password vault"),
    ("github copilot", "GitHub Copilot in VS Code"),
    ("copilot", "Copilot on the web"),
    ("opera", "Opera for Linux (RPM)"), ("brave", "Brave for Linux"), ("vivaldi", "Vivaldi for Linux"),
    ("ffmpeg", "FFmpeg (in Fedora, with RPM Fusion)"), ("tesseract", "Tesseract (in Fedora)"),
    ("bambu studio", "Bambu Studio (Flatpak)"), ("prusaslicer", "PrusaSlicer (Flatpak)"),
    ("orcaslicer", "OrcaSlicer (Flatpak)"), ("cura", "UltiMaker Cura (Flatpak)"),
    ("epic online services", "not needed: comes with Epic's games"), ("ea app", "Lutris, or Steam's Proton"),
    ("ubisoft connect", "Lutris, or Steam's Proton"), ("battle.net", "Lutris, or Steam's Proton"),
    ("gog galaxy", "Heroic Games Launcher"), ("xbox", "not on Linux: Xbox Cloud Gaming in the browser"),
    ("gameinput", "not needed: Windows' game controller layer"),
    ("razer", "OpenRazer and Polychromatic (lighting and buttons); no Synapse on Linux"),
    ("corsair", "ckb-next or OpenRGB; no iCUE on Linux"), ("logitech", "Solaar or Piper"),
    ("steelseries", "OpenRGB; no GG on Linux"), ("nzxt", "liquidctl and OpenRGB; no CAM on Linux"),
    ("gigabyte", "OpenRGB for lighting; board updates through the firmware (fwupd) or its BIOS"),
    ("gbt", "OpenRGB for lighting; board updates through the firmware (fwupd) or its BIOS"),
    ("asus", "asusctl or OpenRGB; no Armoury Crate on Linux"), ("msi center", "OpenRGB; no MSI Center on Linux"),
    ("asrock", "OpenRGB; no ASRock utility on Linux"),
    ("amd chipset", "not needed: the kernel has the chipset drivers"),
    ("furmark", "FurMark for Linux, or GpuTest"), ("hwinfo", "the system monitor, or sensors"),
    ("cpu-z", "CPU-X (Flatpak)"), ("autologon", "not needed: MIA OS signs in its own way (FW-05's PIN)"),
    ("photos", "Gwenview (in KDE)"), ("smart backup", "MIA's nightly backup and its second copy (WP-09)"),
    ("application compatibility", "not needed: part of Windows"),
    ("microsoft visual c++", "not needed: Windows' runtime"),
    (".net", "not needed unless a program asks; then dotnet from Fedora"),
    ("windows sdk", "not needed"),
)


def canonical(record) -> str:
    """Pure logic. One record as sorted, compact JSON: the same record always reads the same."""
    return json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def records_of(text: str, name: str) -> list:
    """Pure logic. A store's records: each line of a .jsonl; a list's items; an object's lists' items (each tagged with
    its key); else the whole object as one. ValueError for text that isn't JSON."""
    if name.endswith(".jsonl"):
        return [json.loads(line) for line in text.splitlines() if line.strip()]
    data = json.loads(text)
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        lists = {k: v for k, v in data.items() if isinstance(v, list)}
        if lists:
            rest = {k: v for k, v in data.items() if k not in lists}
            return [{"_in": k, "_r": item} for k, v in lists.items() for item in v] + ([{"_rest": rest}] if rest else [])
        return [data]
    return [data]


def _opened(path: Path) -> str:
    """A store's text opened the way MIA does, but never copying aside one that won't open (writing the manifest on
    MIA OS before the recovery key is entered must leave no copies behind): ValueError instead."""
    from core import at_rest

    text = path.read_text(encoding="utf-8")
    if at_rest.line_sealed(path):
        lines, failed = at_rest.open_lines(text)
        if failed:
            raise ValueError(f"{failed} line(s) are sealed under a key not held here (enter the recovery key first)")
        return "\n".join(lines)
    return at_rest.unseal(text) if at_rest.is_sealed(text) else text


def store_entry(path: Path) -> dict:
    """One store's {count, hash}, read the way MIA reads it (sealed ones opened); {error} when it won't open or read
    (nothing copied aside)."""
    try:
        records = records_of(_opened(path), path.name)
    except (OSError, ValueError) as problem:
        return {"error": str(problem)[:120] or type(problem).__name__}
    digest = hashlib.sha256("\n".join(sorted(canonical(r) for r in records)).encode("utf-8")).hexdigest()
    return {"count": len(records), "hash": digest}


def stores(root: Optional[Path] = None) -> dict:
    """Every store under MIA's data folder: {path under it (with /): store_entry}. The key folder, the lab's working
    copies and undo blobs are left out (they're re-made, not moved)."""
    root = Path(root) if root is not None else Path(DATA_DIR)
    out = {}
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root)
        if not path.is_file() or path.suffix.lower() not in (".json", ".jsonl") or SKIP_DIRS & set(rel.parts[:-1]):
            continue
        out[rel.as_posix()] = store_entry(path)
    return out


def _sha256(path: Path) -> str:
    """A file's SHA-256, read in pieces."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def sample_files(folders: list[Path], home: Optional[Path] = None, count: int = SAMPLE) -> list[dict]:
    """Up to `count` of his files chosen evenly across these folders (every k-th in sorted order, so the same folders
    give the same choice): each {path under his home, size, sha256}; a file over BIG has its size only."""
    home = Path(home) if home is not None else Path.home()
    found = []
    for folder in folders:
        try:
            found += sorted(p for p in Path(folder).rglob("*") if p.is_file() and not p.is_symlink())
        except OSError:
            continue
    if not found:
        return []
    step = max(1, len(found) // count)
    out = []
    for path in found[::step][:count]:
        try:
            size = path.stat().st_size
            rel = path.relative_to(home).as_posix() if path.is_relative_to(home) else path.as_posix()
            out.append({"path": rel, "size": size, "sha256": _sha256(path) if size <= BIG else ""})
        except OSError:
            continue
    return out


def answer_for(program: str) -> str:
    """Pure logic. A Windows program's answer on MIA OS (`LINUX_ANSWERS`, matched as whole words, so "git" isn't
    "Digital"), or "no known answer yet"."""
    import re

    low = program.lower()
    return next((answer for word, answer in LINUX_ANSWERS
                 if re.search(r"(?<![a-z0-9])" + re.escape(word) + r"(?![a-z0-9])", low)),
                "no known answer yet: his to decide")


def installed_programs() -> list[str]:
    """The programs Windows lists as installed (its Uninstall keys, for every user and this one), by name, once each;
    [] off Windows."""
    if sys.platform != "win32":
        return []
    import winreg

    names = set()
    roots = ((winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
             (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
             (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"))
    for hive, key in roots:
        try:
            with winreg.OpenKey(hive, key) as top:
                for i in range(winreg.QueryInfoKey(top)[0]):
                    try:
                        with winreg.OpenKey(top, winreg.EnumKey(top, i)) as entry:
                            name, _ = winreg.QueryValueEx(entry, "DisplayName")
                            system = winreg.QueryValueEx(entry, "SystemComponent")[0] if _has(entry, "SystemComponent") else 0
                            if name and not system:
                                names.add(str(name).strip())
                    except OSError:
                        continue
        except OSError:
            continue
    return sorted(names)


def _has(entry, value: str) -> bool:
    """Whether a registry key has this value."""
    import winreg

    try:
        winreg.QueryValueEx(entry, value)
        return True
    except OSError:
        return False


def programs(names: Optional[list[str]] = None) -> list[dict]:
    """His programs, each {name, answer} (REQ-CMP-003)."""
    return [{"name": n, "answer": answer_for(n)} for n in (installed_programs() if names is None else names)]


def same_files(before: list[dict], home: Optional[Path] = None) -> list[dict]:
    """The after side's file sample: exactly the files the before manifest sampled, by their path under his home
    (re-choosing would differ across systems: case-sensitive sorting, Windows' own desktop.ini files). A file that
    isn't there is left out, so compare names it missing."""
    home = Path(home) if home is not None else Path.home()
    out = []
    for f in before:
        path = home / f["path"]
        try:
            size = path.stat().st_size
            out.append({"path": f["path"], "size": size, "sha256": _sha256(path) if size <= BIG else ""})
        except OSError:
            continue
    return out


def manifest(root: Optional[Path] = None, folders: Optional[list[Path]] = None, sample: int = SAMPLE,
             program_names: Optional[list[str]] = None, like: Optional[dict] = None) -> dict:
    """Everything recorded before (or after) the move: {version, made, system, stores, files, programs}. After the
    move, `like` is the before manifest: its very files are hashed again (`same_files`)."""
    home = Path.home()
    folders = folders if folders is not None else [home / f for f in DEFAULT_FOLDERS if (home / f).is_dir()]
    files = same_files(like.get("files", []), home) if like is not None else sample_files(folders, home, sample)
    return {"version": VERSION, "made": datetime.now().isoformat(timespec="seconds"), "system": sys.platform,
            "stores": stores(root), "files": files, "programs": programs(program_names)}


def compare(before: dict, after: dict) -> dict:
    """What came across and what didn't: {ok, stores: {matched, changed: [{store, why}], missing, unreadable},
    files: {matched, changed, missing}}. A store or file missing after, changed, or unreadable after is a mismatch;
    one that's new after (MIA made it at its first start) isn't."""
    sb, sa = before.get("stores", {}), after.get("stores", {})
    changed, missing, unreadable, matched = [], [], [], 0
    for name, entry in sorted(sb.items()):
        if "error" in entry:
            continue  # unreadable before the move: nothing to compare (the restore drill says so)
        got = sa.get(name)
        if got is None:
            missing.append(name)
        elif "error" in got:
            unreadable.append(name)
        elif got != entry:
            why = f"{entry['count']} records before, {got['count']} after" if got["count"] != entry["count"] \
                else "the same count, different contents"
            changed.append({"store": name, "why": why})
        else:
            matched += 1
    fa = {f["path"]: f for f in after.get("files", [])}
    f_changed, f_missing, f_matched = [], [], 0
    for f in before.get("files", []):
        got = fa.get(f["path"])
        if got is None:
            f_missing.append(f["path"])
        elif (got["size"], got["sha256"]) != (f["size"], f["sha256"]):
            f_changed.append(f["path"])
        else:
            f_matched += 1
    ok = not (changed or missing or unreadable or f_changed or f_missing)
    return {"ok": ok, "stores": {"matched": matched, "changed": changed, "missing": missing, "unreadable": unreadable},
            "files": {"matched": f_matched, "changed": f_changed, "missing": f_missing}}


def write(path: Path, data: dict) -> Path:
    """Writes a manifest (beside his backups, never in the repository)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, path)
    return path
