"""
core.linux_apps
=================

MIA OS's own desktop, reached from MIA (FW-11, the first version's part; DEC-0233, DEC-0227):

- **Linux apps** (REQ-DSK-007, REQ-ARC-013): the conventional applications installed on the computer, read from the
  system's own desktop entries (the XDG folders and Flatpak's exports), listed in MIA's launcher marked as Linux apps
  and never added to her registry; installing and updating them stays the OS's (Flatpak, the image). `entries()` lists
  them; `launch()` opens one through GLib's launcher (`gio launch` on its desktop file), which goes through the
  desktop's own mechanism.
- **System settings** (REQ-DSK-023, REQ-FUN-003): MIA's Settings opens the matching page of KDE's System Settings for
  each system setting (`SYSTEM_SETTINGS`: display, network, sound...), never a copy of it (`open_setting`).

Both act only on this computer, with fixed arguments (never a shell); a desktop entry is opened only by an id from the
list, a settings page only by a key from the table. Off Linux there are none (on Windows the list is empty and opening
says so).
"""

from __future__ import annotations

import configparser
import os
import subprocess
import sys
from pathlib import Path
from typing import Callable, Optional

from core.logger import get_logger

log = get_logger(__name__)

# MIA's words for each system setting -> (what it's called, KDE's System Settings module that is it).
SYSTEM_SETTINGS: dict[str, tuple[str, str]] = {
    "display": ("Display and monitors", "kcm_kscreen"),
    "network": ("Wi-Fi and network", "kcm_networkmanagement"),
    "sound": ("Sound", "kcm_pulseaudio"),
    "bluetooth": ("Bluetooth", "kcm_bluetooth"),
    "users": ("Users", "kcm_users"),
    "power": ("Power and battery", "kcm_powerdevilprofilesconfig"),
    "time": ("Date and time", "kcm_clock"),
    "keyboard": ("Keyboard", "kcm_keyboard"),
    "mouse": ("Mouse and touchpad", "kcm_mouse"),
    "printers": ("Printers", "kcm_printer_manager"),
    "accessibility": ("Accessibility", "kcm_access"),
    "language": ("Language and region", "kcm_regionandlang"),
    "updates": ("Software updates", "kcm_updates"),
}


def _dirs() -> list[Path]:
    """Where desktop entries live, most specific first: his own, then the system's (XDG), then Flatpak's exports."""
    home = Path.home()
    data_home = Path(os.environ.get("XDG_DATA_HOME") or home / ".local" / "share")
    system = [Path(d) for d in (os.environ.get("XDG_DATA_DIRS") or "/usr/local/share:/usr/share").split(":") if d]
    flatpak = [home / ".local" / "share" / "flatpak" / "exports" / "share", Path("/var/lib/flatpak/exports/share")]
    return [d / "applications" for d in [data_home, *system, *flatpak]]


def read_entry(path: Path) -> Optional[dict]:
    """One desktop entry as {id, name, comment, icon, categories, flatpak, path}, or None for one the launcher doesn't
    show (not an application, hidden, meant for another desktop, unreadable)."""
    parser = configparser.ConfigParser(interpolation=None, strict=False)
    parser.optionxform = str  # keys are case-sensitive in desktop entries
    try:
        parser.read(path, encoding="utf-8")
        e = parser["Desktop Entry"]
    except (configparser.Error, KeyError, OSError, UnicodeDecodeError):
        return None
    yes = lambda key: e.get(key, "").strip().lower() == "true"  # noqa: E731
    only = [d for d in e.get("OnlyShowIn", "").split(";") if d]
    not_in = [d for d in e.get("NotShowIn", "").split(";") if d]
    if e.get("Type") != "Application" or yes("NoDisplay") or yes("Hidden") or not e.get("Name") \
            or (only and "KDE" not in only) or "KDE" in not_in:
        return None
    return {"id": path.name, "name": e.get("Name", "").strip(), "comment": e.get("Comment", "").strip(),
            "icon": e.get("Icon", "").strip(), "categories": [c for c in e.get("Categories", "").split(";") if c],
            "flatpak": bool(e.get("X-Flatpak")), "path": str(path)}


def entries(dirs: Optional[list[Path]] = None) -> list[dict]:
    """Every Linux app the launcher shows, A to Z, each once (an entry in an earlier folder hides a later one with the
    same id, as the desktop does); [] off Linux."""
    if dirs is None:
        if not sys.platform.startswith("linux"):
            return []
        dirs = _dirs()
    seen, out = set(), []
    for folder in dirs:
        try:
            files = sorted(folder.glob("*.desktop"))
        except OSError:
            continue
        for path in files:
            if path.name in seen:
                continue
            seen.add(path.name)
            found = read_entry(path)
            if found:
                out.append(found)
    return sorted(out, key=lambda a: a["name"].lower())


def launch(app_id: str, run: Callable = subprocess.run, dirs: Optional[list[Path]] = None) -> str:
    """Opens one listed Linux app through the desktop's launcher; ValueError for an id that isn't listed, RuntimeError
    when it couldn't start. Returns its name."""
    found = next((a for a in entries(dirs) if a["id"] == app_id), None)
    if found is None:
        raise ValueError("That isn't one of the Linux apps on this computer.")
    done = run(["gio", "launch", found["path"]], capture_output=True, text=True, timeout=30)
    if done.returncode != 0:
        raise RuntimeError(f"{found['name']} didn't start: {(done.stderr or '').strip()[:160]}")
    return found["name"]


def setting_for(words: str) -> Optional[str]:
    """Pure logic. Which system setting some words mean ("the display", "wifi", "Date and time"), or None."""
    low = (words or "").lower()
    aliases = {"wifi": "network", "wi-fi": "network", "internet": "network", "monitor": "display", "screen": "display",
               "volume": "sound", "audio": "sound", "battery": "power", "clock": "time", "date": "time",
               "touchpad": "mouse", "printer": "printers", "region": "language", "update": "updates"}
    for key, (label, _kcm) in SYSTEM_SETTINGS.items():
        if key in low or label.lower() in low:
            return key
    return next((key for word, key in aliases.items() if word in low), None)


def _start(argv: list[str]):
    """Starts a window's program and lets it run on its own (never waited for, never killed with MIA)."""
    return subprocess.Popen(argv, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True,
                            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))


def open_setting(key: str, start: Callable = _start) -> str:
    """Opens KDE's System Settings at this system setting's page (never a copy of it), left running on its own;
    ValueError for one that isn't in the table, RuntimeError off MIA OS or when it couldn't start. Returns the page's
    name."""
    if key not in SYSTEM_SETTINGS:
        raise ValueError("That isn't one of the computer's settings MIA can open.")
    label, kcm = SYSTEM_SETTINGS[key]
    if not sys.platform.startswith("linux"):
        raise RuntimeError(f"{label} is opened in the system's own settings on MIA OS.")
    try:
        start(["systemsettings", kcm])
    except OSError as problem:
        raise RuntimeError(f"System Settings couldn't open: {problem}") from None
    return label
