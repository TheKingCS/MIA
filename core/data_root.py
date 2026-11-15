"""
core.data_root
================

Where MIA keeps a person's files, as one setting (the MIA Runtime's next
step, DEC-0155; needed for MIA OS and the Pi, DEC-0168).

What it is: until 2026-11-15 every store worked out its own folder as
"the code's folder / data" (128 files did). That ties a person's data to
wherever the code is installed, which can't work when the code is a
read-only OS image, or a service whose data belongs under the person's
home. Now every store asks here.

The one setting is the environment variable **`MIA_HOME`**: the folder that
holds the person's MIA.
- **Not set** (the PC today, the phone, tests): MIA's home is the code's
  own folder, exactly as before. Nothing moves.
- **Set** (MIA OS, the Pi: `~/.local/share/mia`): everything MIA writes
  goes under it, in the same layout: `data/`, `config/config.json`,
  `logs/`, and the folders beside them (`trip_photos/`, `trail_maps/`,
  `maintenance_documents/`, `lite_captures/`, `homestead_snapshots/`,
  `financial_snapshots/`, `reference_library/`), and what she writes of
  her development memory (`work/`: tasks, the activity log). The parts of
  `work/` that ship with the code (her knowledge entries, the decisions
  files) are read from the home when it has its own copy, else from the
  code (`work_path`).

What stays with the code whatever `MIA_HOME` says (`SEED_DIR`, `CODE_ROOT`):
the files that ship with MIA and are never written by her: the skill tree's
definitions, the mission pathways, the food table, the model's test cases,
the default config, the web screens, the docs.

It is read once, when this module is first imported, so one running MIA
never changes folders midway. `tools/move_home.py` copies an existing
home to a new one, checks the copy, and says how to switch.

Nothing here creates a folder: each store makes its own when it first
writes, as before.
"""

from __future__ import annotations

import os
from pathlib import Path

ENV = "MIA_HOME"
CODE_ROOT = Path(__file__).resolve().parent.parent  # where MIA's code is installed


def _home() -> Path:
    """The person's MIA folder: `MIA_HOME` when it's set to something (with ~ expanded, made absolute), else the
    code's folder."""
    asked = (os.environ.get(ENV) or "").strip()
    if not asked:
        return CODE_ROOT
    return Path(asked).expanduser().resolve()


HOME = _home()  # everything MIA writes is under here
DATA_DIR = HOME / "data"  # the stores
CONFIG_DIR = HOME / "config"  # config.json (the defaults ship with the code: CODE_ROOT / "config")
LOG_DIR = HOME / "logs"
SEED_DIR = CODE_ROOT / "data"  # files that ship with MIA and she never writes (skill definitions, the food table...)
SEPARATE = HOME != CODE_ROOT  # whether the person's files are kept apart from the code


WORK_DIR = HOME / "work"  # the development memory this MIA writes: tasks, the activity log, the council's log


def work_path(name: str) -> Path:
    """A file or folder of MIA's development memory that ships with the code (her knowledge entries, the parity and
    loop decisions, the documentation baseline): the home's own copy when it has one, else the code's. With no
    `MIA_HOME` they are the same place."""
    own = WORK_DIR / name
    return own if (not SEPARATE or own.exists()) else CODE_ROOT / "work" / name


def home_dir(name: str) -> Path:
    """A folder beside data/ in the person's MIA folder (trip_photos, trail_maps, work...)."""
    return HOME / name


def describe() -> dict:
    """Where things are, for Diagnostics and /api/runtime/health: the person's folder, the code's, and whether
    they're apart."""
    return {"home": str(HOME), "code": str(CODE_ROOT), "separate": SEPARATE, "from": ENV if SEPARATE else "the code's folder"}
