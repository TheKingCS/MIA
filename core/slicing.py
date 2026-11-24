"""
core.slicing
==============

Slicing a part for his printer (docs/future/HUB_AND_ENGINEER_PLAN.md part 2, step 2): the STL files MIA makes
(core/print_parts.py) sliced by Bambu Studio's own command line, on his PC, offline, for the printer Bambu Studio is
set up for (its settings' `machine` preset, a Bambu Lab P1P 0.4 nozzle on his), with that printer's stock
"0.20mm Standard" process and Bambu PLA Basic. Measured 2026-11-24: about a second a part, and Bambu read MIA's
enclosure at its exact size with no warnings.

**What comes back** (`slice_files`): the print time and the filament (its length, and its grams worked out here at PLA's
1.24 g/cm³ on 1.75 mm filament, since Bambu's stock filament profile leaves the density at 0 on the command line),
and the sliced project (a .3mf) beside the part, ready to open in Bambu Studio and send to the printer from there.
Nothing is printed: sending a job to the printer is a later step, on his yes (WAITING_ON 0zr).

**Where it runs**: Bambu Studio installed (Windows: Program Files; elsewhere `bambu-studio` on the path) with its
profiles beside it; without it, or with a printer it has no stock profiles for, it says so. Never in a test run
(the program is a separate process; tests pass a runner).
Each part is sliced on its own plate in a fresh folder; printer names map to Bambu's profile codes (`MODELS`), only
for a 0.4 mm nozzle; times are added up (`to_seconds`, `said_time`).
"""

from __future__ import annotations

import math
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Callable, Optional

from core.logger import get_logger

log = get_logger(__name__)

PLA_G_PER_CM3 = 1.24
FILAMENT_MM = 1.75
_WINDOWS_EXE = Path(r"C:\Program Files\Bambu Studio\bambu-studio.exe")


def _exe() -> Optional[Path]:
    """Bambu Studio's program, or None."""
    if _WINDOWS_EXE.exists():
        return _WINDOWS_EXE
    found = shutil.which("bambu-studio")
    return Path(found) if found else None


def _settings_file() -> Optional[Path]:
    """Bambu Studio's own settings file (Windows %APPDATA%, else ~/.config), or None."""
    for base in (os.environ.get("APPDATA"), str(Path.home() / ".config")):
        if base and (Path(base) / "BambuStudio" / "BambuStudio.conf").exists():
            return Path(base) / "BambuStudio" / "BambuStudio.conf"
    return None


def printer(conf_text: str) -> str:
    """Pure logic. The printer preset Bambu Studio is set up for ("Bambu Lab P1P 0.4 nozzle"), from its settings'
    text; "" when it isn't there."""
    m = re.search(r'"machine"\s*:\s*"([^"]+)"', conf_text or "")
    return m.group(1) if m else ""


# Bambu's printer names to the code its process and filament profiles use (the P1S shares the P1P's processes)
MODELS = {"X1 Carbon": "X1C", "X1C": "X1C", "X1": "X1C", "X1E": "X1E", "P1S": "P1P", "P1P": "P1P", "A1": "A1",
          "A1 mini": "A1M", "H2D": "H2D", "H2D Pro": "H2DP", "H2S": "H2S", "P2S": "P2S"}


def profiles(machine: str, root: Path) -> Optional[dict]:
    """The stock profile files for this printer under Bambu's profiles folder (`root` is its BBL folder): its
    machine, its "0.20mm Standard" process and a PLA Basic filament (its own, else the X1C's), the model's code from
    `MODELS`; None for a nozzle other than 0.4 mm, a printer not in `MODELS`, or one with no stock profile there."""
    model = re.match(r"Bambu Lab (.+?) (\d+(?:\.\d+)?) nozzle$", machine or "")
    if not model or model.group(2) != "0.4":
        return None  # a printer we can't name, or a nozzle the 0.20mm Standard process isn't for
    m = MODELS.get(model.group(1))
    if m is None:
        return None
    machine_file = root / "machine" / f"{machine}.json"
    process = root / "process" / f"0.20mm Standard @BBL {m}.json"
    filament = next((f for f in (root / "filament" / f"Bambu PLA Basic @BBL {m}.json",
                                 root / "filament" / "Bambu PLA Basic @BBL X1C.json") if f.exists()), None)
    if not (machine_file.exists() and process.exists() and filament is not None):
        return None
    return {"machine": machine_file, "process": process, "filament": filament, "model": m}


def read_gcode_header(text: str) -> dict:
    """Pure logic. The print time and filament length from a G-code file's header: {"time", "length_mm", "grams"}
    (grams worked out from the length on 1.75 mm filament at PLA's density)."""
    t = re.search(r"total estimated time:\s*([^\n;]+)", text) or re.search(r"model printing time:\s*([^\n;]+)", text)
    length = re.search(r"total filament length \[mm\]\s*:\s*([\d.]+)", text)
    mm = float(length.group(1)) if length else 0.0
    grams = mm * math.pi * (FILAMENT_MM / 2) ** 2 / 1000 * PLA_G_PER_CM3
    return {"time": t.group(1).strip() if t else "", "length_mm": mm, "grams": round(grams)}


def _run(args: list, cwd: Path) -> int:
    """Runs Bambu Studio's command line with no window, two minutes at most; its exit code."""
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    return subprocess.run(args, cwd=str(cwd), capture_output=True, timeout=120, creationflags=flags).returncode


def slice_files(stl_paths: list, out_name: str, run: Optional[Callable] = None) -> str:
    """Slices each of these STL files on its own plate for his printer (a fresh output folder each, never an old
    G-code) and says the print time and filament for them all, with where the sliced projects are; or why it
    can't."""
    exe = _exe()
    if exe is None:
        return "Bambu Studio isn't installed here, so I can't slice it: open the STL in your slicer."
    conf = _settings_file()
    machine = printer(conf.read_text(encoding="utf-8", errors="replace")) if conf else ""
    found = profiles(machine, exe.parent / "resources" / "profiles" / "BBL") if machine else None
    if found is None:
        return ("I couldn't tell which printer Bambu Studio is set up for, or it has no stock profile for it, so I "
                "didn't slice it: open the STL in Bambu Studio.")
    if run is None and os.environ.get("PYTEST_CURRENT_TEST"):
        return "Not sliced in a test run."
    seconds, grams, metres, projects = 0, 0, 0.0, []
    for path in [Path(p) for p in stl_paths]:  # each part on its own plate: a big box and lid needn't fit together
        out = path.parent / f"{path.stem}-sliced"
        shutil.rmtree(out, ignore_errors=True)  # never yesterday's G-code read as today's
        args = [str(exe), "--slice", "0", "--load-settings", f"{found['machine']};{found['process']}",
                "--load-filaments", str(found["filament"]), "--outputdir", str(out), "--export-3mf",
                f"{path.stem}.3mf", path.name]
        try:
            code = (run or _run)(args, path.parent)
        except Exception:  # noqa: BLE001 - the slicer failing never breaks the part
            log.exception("Bambu Studio couldn't slice %s", path.name)
            code = -1
        gcode = out / "plate_1.gcode"
        if code != 0 or not gcode.exists():
            return (f"Bambu Studio couldn't slice {path.name} here (too big for the bed, or another problem); the "
                    "STL files are fine to open in it yourself.")
        head = read_gcode_header(gcode.read_text(encoding="utf-8", errors="replace")[:20000])
        seconds += to_seconds(head["time"])
        grams += head["grams"]
        metres += head["length_mm"] / 1000
        projects.append(str(out / f"{path.stem}.3mf"))
    return (f"Sliced for your {machine} (0.20 mm layers, PLA): about {said_time(seconds)} to print"
            + (" in all" if len(projects) > 1 else "") + f" and about {grams} g of filament ({metres:.1f} m). The "
            "sliced project" + ("s are " if len(projects) > 1 else " is ") + ", ".join(projects)
            + ": open " + ("them" if len(projects) > 1 else "it") + " in Bambu Studio to send to the printer.")


def to_seconds(said: str) -> int:
    """Pure logic. "1h 2m 3s" or "57m 20s" in seconds; 0 for words it can't read."""
    total = 0
    for n, unit in re.findall(r"(\d+)\s*([dhms])", said or ""):
        total += int(n) * {"d": 86400, "h": 3600, "m": 60, "s": 1}[unit]
    return total


def said_time(seconds: int) -> str:
    """Pure logic. Seconds as a print time ("1h 4m", "57m")."""
    h, m = divmod(round(seconds / 60), 60)
    return f"{h}h {m}m" if h else f"{m}m"
