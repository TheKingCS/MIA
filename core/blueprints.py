"""
core.blueprints
=================

The blueprints MIA builds screens from (DEC-0090; `blueprints/README.md`):
versioned JSON in the repo, with fields named by role (`$title`, `$date`,
`$group`, `$number`, `$all`, `$details`). `fill()` turns one into blocks for
a particular record set, leaving out what has no field to show.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent.parent / "blueprints"


def load(root: Path = ROOT) -> dict:
    """id -> blueprint."""
    out = {}
    for path in sorted(Path(root).glob("*.json")):
        try:
            found = json.loads(path.read_text(encoding="utf-8"))
            out[found["id"]] = found
        except (OSError, ValueError, KeyError):
            continue
    return out


def roles(fields: list[dict]) -> dict:
    """Pure logic. Which field plays which part."""
    def first(*types: str, skip: Optional[str] = None) -> Optional[str]:
        return next((f["name"] for f in fields if f["type"] in types and f["name"] != skip), None)

    title = first("text", "choice")
    group = first("choice", "yesno", skip=title) or next(
        (f["name"] for f in fields if f["type"] == "text" and f["name"] != title), None)
    return {"$title": title, "$date": first("date"), "$group": group, "$number": first("money", "number"),
            "$all": [f["name"] for f in fields][:6], "$details": [f["name"] for f in fields if f["name"] != title][:3]}


class _Missing(Exception):
    pass


def _fill(value, filled: dict, labels: dict):
    if isinstance(value, str):
        if value in filled:
            if filled[value] is None:
                raise _Missing
            return copy.copy(filled[value])
        if value.startswith("-$"):
            if filled.get(value[1:]) is None:
                raise _Missing
            return "-" + filled[value[1:]]
        for role, name in filled.items():
            if isinstance(name, str) and role in value:
                value = value.replace(role, labels.get(name, name).lower())
        return value
    if isinstance(value, list):
        out = []
        for v in value:
            try:
                out.append(_fill(v, filled, labels))
            except _Missing:
                if not isinstance(v, dict):
                    raise
        return out
    if isinstance(value, dict):
        return {k: _fill(v, filled, labels) for k, v in value.items()}
    return value


def fill(blueprint: dict, fields: list[dict]) -> list[dict]:
    """Pure logic. The blueprint's blocks for these fields; a block or stat with a missing role is left out."""
    filled = roles(fields)
    labels = {f["name"]: f.get("label") or f["name"] for f in fields}
    blocks = []
    for block in blueprint["blocks"]:
        try:
            made = _fill(block, filled, labels)
        except _Missing:
            continue
        if made.get("block") == "stats" and not made.get("items"):
            continue
        if "sort" in made and not made["sort"].lstrip("-"):
            made.pop("sort")
        blocks.append(made)
    return blocks
