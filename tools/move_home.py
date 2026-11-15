"""
tools.move_home
=================

Copies a person's MIA to a new home folder (core/data_root.py, `MIA_HOME`;
DEC-0155, DEC-0168): the step from "her data lives inside the code's
folder" to "her data lives in the person's own folder", which MIA OS and
the Pi need.

    python -m tools.move_home ~/.local/share/mia          # copy, then check every file
    python -m tools.move_home ~/.local/share/mia --check  # only say what would be copied

What it does, in order:
1. Refuses while MIA is running on the folder being copied (the one-MIA
   lock), so no file changes midway.
2. Copies the person's files: `data/`, `config/config.json`, the folders
   beside them (trip photos, trail maps, maintenance documents, field
   captures, snapshots, the reference library) and `work/`. Logs are left
   behind. Nothing that ships with the code is copied.
3. Checks every copied file against its original (size and SHA-256).
4. Says how to switch: set `MIA_HOME` to the new folder.

What it never does: delete, move or change anything in the old folder. The
old folder stays as the fallback until the person removes it themselves.

It refuses a target that already holds a MIA (a `data` folder with
anything in it), and a target inside the folder being copied.

Sealed files (DEC-0126): sealed files open with a data key that the
computer protects for one account (the Windows sign-in; on Linux, the
machine's unlock secret, core/key_unlock.py). They copy fine and open
again on the same computer and account. On a system that doesn't hold
the key, they can't be opened until the recovery key is entered there
(`python -m tools.data_key restore`): this tool counts them and says so
before copying, and stops unless `--sealed-ok` is given.
"""

from __future__ import annotations

import hashlib
import shutil
import sys
from pathlib import Path
from typing import Optional

from core import data_root

FOLDERS = ("data", "trip_photos", "trail_maps", "maintenance_documents", "lite_captures", "homestead_snapshots",
           "financial_snapshots", "reference_library", "work")
FILES = ("config/config.json",)
SKIP_NAMES = {".mia.lock", "__pycache__"}  # the running-MIA lock belongs to a folder, not to the data


class MoveError(RuntimeError):
    """The copy can't go ahead, or didn't check out; its message is a plain sentence."""


def _shipped(source: Path) -> set[Path]:
    """The files under the source that ship with MIA's code (tracked seed files in data/), which a copy leaves out
    when the source is the code's own folder: the new home reads them from the code."""
    if source.resolve() != data_root.CODE_ROOT:
        return set()
    names = ("skill_definitions.json", "mission_pathways.json", "foods.tsv", "model_bench_cases.json",
             "conversation_cases.json", "user_sync_cases.json", ".gitkeep")
    return {source / "data" / n for n in names} | {source / "reference_library" / ".gitkeep"}


def files_to_copy(source: Path) -> list[Path]:
    """Every file of the person's under the source, as paths relative to it, sorted."""
    source = Path(source)
    shipped = _shipped(source)
    found = []
    for name in FOLDERS:
        base = source / name
        if not base.is_dir():
            continue
        for path in base.rglob("*"):
            if path.is_file() and not (SKIP_NAMES & set(path.parts)) and path not in shipped:
                found.append(path.relative_to(source))
    found += [Path(f) for f in FILES if (source / f).is_file()]
    return sorted(found)


def sealed(source: Path, files: list[Path]) -> list[Path]:
    """The files among these that are sealed (DEC-0126): they start with the seal's mark."""
    from core.at_rest import PREFIX

    mark = PREFIX.encode("utf-8")
    out = []
    for rel in files:
        try:
            with open(Path(source) / rel, "rb") as f:
                if f.read(len(mark)) == mark:
                    out.append(rel)
        except OSError:
            continue
    return out


def _digest(path: Path) -> str:
    """A file's SHA-256."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def check_target(source: Path, target: Path) -> None:
    """MoveError when the target can't take a copy: it is the source, is inside one of the source's copied folders,
    or already holds a MIA."""
    source, target = Path(source).resolve(), Path(target).expanduser().resolve()
    if target == source:
        raise MoveError("That's the folder MIA is already in.")
    if any(target == (source / f) or (source / f) in target.parents for f in FOLDERS):
        raise MoveError("The new home can't be inside one of the folders being copied.")
    data = target / "data"
    if data.is_dir() and any(data.iterdir()):
        raise MoveError(f"{target} already holds a MIA (its data folder isn't empty). Choose an empty folder.")


def copy(source: Path, target: Path) -> dict:
    """Copies the person's files from source to target and checks each against its original: {"files", "bytes"}.
    MoveError naming the first files that differ. The source is only ever read."""
    source, target = Path(source).resolve(), Path(target).expanduser().resolve()
    check_target(source, target)
    files = files_to_copy(source)
    total = 0
    for rel in files:
        dest = target / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source / rel, dest)
    wrong = []
    for rel in files:
        a, b = source / rel, target / rel
        if not b.is_file() or a.stat().st_size != b.stat().st_size or _digest(a) != _digest(b):
            wrong.append(str(rel))
        total += a.stat().st_size
    if wrong:
        raise MoveError(f"{len(wrong)} file(s) didn't copy correctly (the first: {', '.join(wrong[:3])}). The old "
                        f"folder is untouched; remove {target} and try again.")
    return {"files": len(files), "bytes": total}


def main(argv: Optional[list] = None) -> int:
    """`python -m tools.move_home TARGET [--check] [--sealed-ok]`: 0 when the copy is made and checked (or, with
    --check, could be), 1 with the reason otherwise."""
    from core import at_rest, instance_lock

    args = list(argv if argv is not None else sys.argv[1:])
    only_check, sealed_ok = "--check" in args, "--sealed-ok" in args
    places = [a for a in args if not a.startswith("--")]
    if len(places) != 1:
        print(__doc__.strip().split("\n\n")[1])
        return 1
    source, target = data_root.HOME, Path(places[0]).expanduser().resolve()
    try:
        check_target(source, target)
    except MoveError as problem:
        print(problem)
        return 1
    files = files_to_copy(source)
    locked = sealed(source, files)
    size = sum((source / f).stat().st_size for f in files)
    print(f"From {source}\n  to {target}\n{len(files)} files, {size / 1e6:.1f} MB.")
    if locked:
        print(f"{len(locked)} of them are sealed (DEC-0126).")
        if not at_rest.status()["sealing"]:
            print("This system doesn't hold the key that opens them (they were sealed on another computer or "
                  "account).\n"
                  "They would copy, but MIA here can't read them until the recovery key is entered. On the computer\n"
                  "that sealed them, keep the recovery key (python -m tools.data_key recovery). Then copy with\n"
                  f"--sealed-ok and, with {data_root.ENV} set to the new folder:\n"
                  "  python -m tools.data_key protect    (Linux, once)\n"
                  "  python -m tools.data_key restore")
            if not sealed_ok and not only_check:
                print("Nothing was copied. Add --sealed-ok to copy anyway.")
                return 1
    if only_check:
        print("Nothing was copied (--check).")
        return 0
    if not instance_lock.acquire():
        print("MIA is running on this folder. Close her first, so nothing changes during the copy.")
        return 1
    try:
        done = copy(source, target)
    except (MoveError, OSError) as problem:
        print(problem)
        return 1
    print(f"Copied and checked {done['files']} files. The old folder is untouched.\n"
          f"To switch, start MIA with {data_root.ENV} set to the new folder:\n"
          f"  Linux:   export {data_root.ENV}={target}   (deploy/install_runtime.sh does this for the service)\n"
          f"  Windows: setx {data_root.ENV} \"{target}\"   (then start MIA again)\n"
          f"Once you're sure everything is there, the old data folder can be removed by hand.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
