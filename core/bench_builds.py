"""
core.bench_builds
===================

His builds on My Bench, kept (brainstorm round 13, idea 5; 2026-11-25): a free build or one of MIA's designs saved by
name with its board, parts, wires and sketch, opened on the bench again later, and marked built, which takes its parts
out of his Component DB's counts (core/component_manager.py). Kept in data/labs/bench_builds.json, sealed at rest
(core/at_rest.SEALED), written through atomic_write_text so "undo that" restores it.

- **The book** (`BuildBook`): `save`, `get`, `all` (newest first), `remove`, `mark_built`.
- **His parts** (`parts_used`): each of a build's parts matched to his Component DB by its model ("HC-SR04" in
  "HC-SR04 sensor"), with how many it takes and how many he has.
- **Actions** (core/actions.py): `benchbuild.save` (Save This Build) and `benchbuild.remove` (his own record, undoable),
  `benchbuild.built` (Mark It Built: his Component DB's counts go down, so it's approved, and the card says each
  change: "HC-SR04 ultrasonic sensor: 2 to 1"). Tool `bench_builds` ("what have I built on the bench?").
"""

from __future__ import annotations

import json
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from core.actions import ACTION_TYPES, ActionError, ActionType
from core.at_rest import open_text
from core.atomic_write import atomic_write_text
from core.data_root import DATA_DIR
from core.logger import get_logger

log = get_logger(__name__)


class BuildBook:
    """His saved builds (see the module's opening)."""

    def __init__(self, context=None, data_dir: Optional[Path] = None):
        """Loads them from `data_dir` (data/labs by default)."""
        self.context = context
        self.data_dir = Path(data_dir or DATA_DIR / "labs")
        self._file = self.data_dir / "bench_builds.json"
        self.builds: list = []
        self._load()

    def _load(self) -> None:
        """Reads the file through open_text (sealed at rest); none yet, or unreadable: no builds."""
        try:
            self.builds = json.loads(open_text(self._file)).get("builds", []) if self._file.exists() else []
        except (OSError, ValueError, AttributeError) as problem:
            log.warning("Couldn't read his bench builds: %s", problem)
            self.builds = []

    def _save(self) -> None:
        """Writes it atomically (sealed, and undoable)."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_text(self._file, json.dumps({"builds": self.builds}, indent=1, ensure_ascii=False))

    def save(self, name: str, board: str, parts: list, wires: list, sketch: str = "", design: str = "") -> dict:
        """Keeps a build (one of the same name on the same board is replaced: a new version). ValueError for no name
        or nothing on the board.
        A re-saved build is a new version, not built."""
        name = " ".join(str(name or "").split())[:80]
        if not name:
            raise ValueError("Give the build a name.")
        if not parts:
            raise ValueError("There's nothing on the board to save.")
        now = datetime.now().isoformat(timespec="minutes")
        found = next((b for b in self.builds if b["name"].lower() == name.lower() and b["board"] == board), None)
        build = found or {"id": uuid.uuid4().hex[:8], "created": now}
        build["built"] = ""  # a new version isn't built yet
        build.update({"name": name, "board": str(board), "parts": [dict(id=str(p["id"]), spec=str(p["spec"]))
                                                                    for p in parts][:20],
                      "wires": [[str(a), str(b)] for a, b in wires][:80], "sketch": str(sketch or "")[:20000],
                      "design": str(design or ""), "updated": now})
        if found is None:
            self.builds.append(build)
        self._save()
        return build

    def get(self, build_id: str) -> Optional[dict]:
        """A build by its id, or None."""
        return next((b for b in self.builds if b["id"] == build_id), None)

    def all(self) -> list:
        """His builds, the newest change first."""
        return sorted(self.builds, key=lambda b: b.get("updated", ""), reverse=True)

    def remove(self, build_id: str) -> dict:
        """Takes one away. KeyError for one that isn't there."""
        build = self.get(build_id)
        if build is None:
            raise KeyError(build_id)
        self.builds.remove(build)
        self._save()
        return build

    def mark_built(self, build_id: str) -> dict:
        """Notes the day it was built."""
        build = self.get(build_id)
        if build is None:
            raise KeyError(build_id)
        build["built"] = datetime.now().isoformat(timespec="minutes")
        self._save()
        return build


def book(context=None) -> BuildBook:
    """His build book: the context's, else one on the data folder."""
    found = getattr(context, "bench_builds", None) if context is not None else None
    return found if found is not None else BuildBook(context)


def parts_used(context, build: dict) -> list:
    """Each kind of part a build takes: {spec, name, count, component (his one matching Component DB entry, by whole
    word; None when none or several could be it), several, on_hand}."""
    from core import part_specs

    specs = part_specs.book(context).all()
    store = getattr(context, "components", None)
    stock = store.all_components() if store is not None else []
    counts: dict = {}
    for part in build.get("parts", []):
        counts[part["spec"]] = counts.get(part["spec"], 0) + 1
    out = []
    for spec_id, n in counts.items():
        spec = specs.get(spec_id)
        name = spec.name if spec else spec_id
        model = re.sub(r"[^a-z0-9]+", "", name.lower().split(" ")[0])
        from core.bench_designs import matching_parts

        found = matching_parts(stock, spec) if spec else []
        match = found[0] if len(found) == 1 else None  # several that could be it: never a guess
        out.append({"spec": spec_id, "name": name, "count": n, "component": match, "several": len(found) > 1,
                    "on_hand": int(match.quantity or 0) if match else None})
    return out


# ------------------------------------------------------------------ actions and the tool

def _save_describe(context, params) -> str:
    """What benchbuild.save says."""
    name = " ".join(str(params.get("name", "") or "").split())
    if not name:
        raise ActionError("Give the build a name.")
    parts, wires = params.get("parts") or [], params.get("wires") or []
    if not parts:
        raise ActionError("There's nothing on the board to save.")
    return f"Save \"{name}\": {len(parts)} part{'s' if len(parts) != 1 else ''} and {len(wires)} wire" + \
        ("s" if len(wires) != 1 else "")


def _save_execute(context, params) -> str:
    """Does benchbuild.save."""
    try:
        build = book(context).save(params.get("name"), str(params.get("board", "")), params.get("parts") or [],
                                   params.get("wires") or [], params.get("sketch", ""), params.get("design", ""))
    except ValueError as problem:
        raise ActionError(str(problem))
    return f"Saved \"{build['name']}\": open it on My Bench any time."


def _remove_describe(context, params) -> str:
    """What benchbuild.remove says."""
    build = book(context).get(str(params.get("build_id", "")))
    if build is None:
        raise ActionError("That build isn't saved.")
    return f"Delete the saved build \"{build['name']}\""


def _remove_execute(context, params) -> str:
    """Does benchbuild.remove."""
    build = book(context).remove(str(params.get("build_id", "")))
    return f"Deleted \"{build['name']}\"."


def _built_describe(context, params) -> str:
    """What benchbuild.built says: each Component DB count it changes, and the parts he has no record of.
    One already built is refused; a part several of his could be is named, never guessed."""
    build = book(context).get(str(params.get("build_id", "")))
    if build is None:
        raise ActionError("That build isn't saved.")
    if build.get("built"):
        raise ActionError(f"\"{build['name']}\" is already marked built.")
    changes, unknown = [], []
    for used in parts_used(context, build):
        if used["component"] is None:
            unknown.append(used["name"] + (" (several of your parts could be it: change the count yourself)"
                                           if used.get("several") else ""))
        else:
            changes.append(f"{used['component'].name}: {used['on_hand']} to {max(0, used['on_hand'] - used['count'])}")
    said = f"Mark \"{build['name']}\" built" + (f", taking its parts from your Component DB ({'; '.join(changes)})"
                                                 if changes else "")
    return said + (f". Not in your Component DB: {', '.join(unknown)}" if unknown else "")


def _built_execute(context, params) -> str:
    """Does benchbuild.built: the counts down, the day kept; never twice."""
    build = book(context).get(str(params.get("build_id", "")))
    store = getattr(context, "components", None)
    if build is None:
        raise ActionError("That build isn't saved.")
    if build.get("built"):
        raise ActionError(f"\"{build['name']}\" is already marked built.")
    taken = []
    for used in parts_used(context, build):
        if used["component"] is not None and store is not None:
            store.adjust_quantity(used["component"].component_id, -used["count"])
            taken.append(f"{used['count']} {used['component'].name}")
    book(context).mark_built(build["id"])
    return f"Marked \"{build['name']}\" built" + (f": took {', '.join(taken)} from your parts." if taken else ".")


ACTIONS = {a.kind: a for a in (
    ActionType("benchbuild.save", "Save This Build", {"name": "what to call it", "board": "the board",
                                                      "parts": "its parts", "wires": "its wires",
                                                      "sketch": "its sketch (optional)",
                                                      "design": "the design it came from (optional)"},
               _save_describe, _save_execute),
    ActionType("benchbuild.remove", "Delete This Build", {"build_id": "a saved build"},
               _remove_describe, _remove_execute),
    ActionType("benchbuild.built", "Mark It Built", {"build_id": "a saved build"}, _built_describe, _built_execute),
)}
ACTION_TYPES.update(ACTIONS)


def _list_tool(context, arguments: dict) -> str:
    """Tool bench_builds: his saved builds, newest first, and which are built."""
    builds = book(context).all()
    if not builds:
        return "You haven't saved a build on My Bench yet: put one together there and press Save This Build."
    said = "; ".join(f"{b['name']} ({b['board']}, {len(b['parts'])} parts" + (", built" if b.get("built") else "")
                     + ")" for b in builds[:8])
    return f"Your bench builds: {said}."


def register_build_tools(registry) -> None:
    """Registers bench_builds."""
    from core.assistant_actions import AssistantAction

    registry.register(AssistantAction(
        name="bench_builds", domain="learning",
        description="His builds saved on My Bench (electronics), newest first, and which he's built.",
        parameters={"type": "object", "properties": {}, "required": []}, subjects=("builds", "bench"),
        handler=_list_tool, trigger_phrases=("built on the bench", "builds on my bench", "my bench builds",
                                            "saved builds", "on my bench"),
    ))
