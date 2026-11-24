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


def profiles(machine: str, root: Path) -> Optional[dict]:
    """The stock profile files for this printer under Bambu's profiles folder (`root` is its BBL folder): its
    machine, its "0.20mm Standard" process and a PLA Basic filament (its own, else the X1C's); None when the printer
    has no stock machine profile there."""
    model = re.search(r"Bambu Lab (\S+)", machine or "")
    if not model:
        return None
    m = model.group(1)
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
    """Slices these STL files together for his printer and says the print time and filament, with where the sliced
    project is; or why it can't."""
    exe = _exe()
    if exe is None:
        return "Bambu Studio isn't installed here, so I can't slice it: open the STL in your slicer."
    conf = _settings_file()
    machine = printer(conf.read_text(encoding="utf-8", errors="replace")) if conf else ""
    found = profiles(machine, exe.parent / "resources" / "profiles" / "BBL") if machine else None
    if found is None:
        return ("I couldn't tell which printer Bambu Studio is set up for, or it has no stock profile for it, so I "
                "didn't slice it: open the STL in Bambu Studio.")
    paths = [Path(p) for p in stl_paths]
    folder = paths[0].parent
    out = folder / f"{out_name}-sliced"
    args = [str(exe), "--slice", "0", "--load-settings", f"{found['machine']};{found['process']}",
            "--load-filaments", str(found["filament"]), "--outputdir", str(out), "--export-3mf", f"{out_name}.3mf",
            *[p.name for p in paths]]
    if run is None and os.environ.get("PYTEST_CURRENT_TEST"):
        return "Not sliced in a test run."
    try:
        code = (run or _run)(args, folder)
    except Exception:  # noqa: BLE001 - the slicer failing never breaks the part
        log.exception("Bambu Studio couldn't slice %s", out_name)
        code = -1
    gcode = out / "plate_1.gcode"
    if code != 0 or not gcode.exists():
        return "Bambu Studio couldn't slice it here; the STL files are fine to open in it yourself."
    head = read_gcode_header(gcode.read_text(encoding="utf-8", errors="replace")[:20000])
    return (f"Sliced for your {machine} (0.20 mm layers, PLA): about {head['time']} to print and about "
            f"{head['grams']} g of filament ({head['length_mm'] / 1000:.1f} m). The sliced project is "
            f"{out / (out_name + '.3mf')}: open it in Bambu Studio to send it to the printer.")
