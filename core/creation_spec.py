"""
core.creation_spec
====================

What a screen MIA makes may say, and what it shows (DEC-0088/0091; ACAF,
`docs/ACAF_REVIEW.md` sections 3.2 to 4). A screen is a specification: a
title, the record set it shows (core/record_sets.py) and a list of
**blocks** from a fixed catalogue. It holds no HTML, script or free formula:
values are a small vocabulary (`count`, `sum`, `avg`, `min`, `max`,
`latest`), worked out here, in core (DEC-0013), and `web/made.js` only
draws the blocks with MIA's own classes and tokens (DEC-0023). So a spec
can't run anything, reach data it shouldn't, or look foreign, and new
combinations of blocks still give screens nobody planned.

- `check(spec, child=False)`: every problem, in words; an empty list passes.
  Unknown keys are refused, so nothing can be smuggled in.
- `assemble(spec, record_set)`: the blocks with their values, ready to draw.

A screen shows its own record set, or one **source** from the catalogue
(core/creation_sources.py: eggs, workouts, spending...), read-only: a source
has no form, and money sources never reach a child. A chart over dates can
group them by day, week or month.
"""

from __future__ import annotations

from collections import OrderedDict
from typing import Optional

from core.record_sets import FIELD_TYPES, check_fields

BLOCKS = {
    # block: (allowed keys, what it is)
    "stats": ({"block", "title", "items"}, "a row of numbers"),
    "chart": ({"block", "title", "type", "x", "y", "by"}, "bars by a field, or a line over dates (by day, week or month)"),
    "table": ({"block", "title", "columns", "sort", "limit"}, "the records as rows"),
    "list": ({"block", "title", "title_field", "detail_fields", "sort", "limit"}, "the records as a list"),
    "cards": ({"block", "title", "title_field", "detail_fields", "sort", "limit"}, "the records as cards"),
    "meter": ({"block", "title", "label", "value", "goal"}, "one number against a goal"),
    "timeline": ({"block", "title", "date_field", "title_field", "limit"}, "the records by date"),
    "form": ({"block", "title"}, "add a record"),
    "note": ({"block", "text"}, "a line of plain text"),
}
VALUES = ("count", "sum", "avg", "min", "max", "latest")
NUMERIC = ("number", "money")
SPEC_KEYS = {"kind", "title", "icon", "about", "owner", "record_set", "source", "blocks"}
ICONS = ("mia", "home", "dashboard", "apps", "greenhouse", "garage", "kitchen", "workout", "property", "missions",
         "skills", "budget", "maintenance", "character", "profile", "assistant", "settings", "household", "workshop",
         "compliance", "freedom", "issues", "flock", "insurance", "security", "business", "power", "observations",
         "relationships", "notes", "classroom", "inbox", "expeditions", "memories", "maps", "navigation",
         "knowledge", "toolbox")
MAX_BLOCKS = 12
MAX_ROWS = 200


PERIODS = ("day", "week", "month")


def _fields(spec: dict) -> dict:
    from core.creation_sources import fields_of, source_of

    source = source_of(spec)
    found = fields_of(source.id) if source else (spec.get("record_set") or {}).get("fields") or []
    return {f["name"]: f for f in found if isinstance(f, dict) and "name" in f}


def _value_problems(value, fields: dict, where: str) -> list[str]:
    if not isinstance(value, dict) or len(value) != 1:
        return [f"{where}: a value is one of {', '.join(VALUES)}, like {{\"count\": true}} or {{\"sum\": \"field\"}}."]
    (op, field), = value.items()
    if op not in VALUES:
        return [f"{where}: {op!r} isn't a value MIA works out (one of {', '.join(VALUES)})."]
    if op == "count":
        return []
    if field not in fields:
        return [f"{where}: there's no field {field!r}."]
    kind = fields[field]["type"]
    if op in ("sum", "avg") and kind not in NUMERIC:
        return [f"{where}: {op} needs a number or money field, and {field!r} is {kind}."]
    if op in ("min", "max") and kind not in (*NUMERIC, "date"):
        return [f"{where}: {op} needs a number, money or date field, and {field!r} is {kind}."]
    return []


def check(spec: dict, child: bool = False) -> list[str]:
    """Pure logic. Every problem with a screen spec; an empty list passes."""
    if not isinstance(spec, dict):
        return ["A screen is a JSON object."]
    problems = [f"Unknown part {k!r}." for k in spec if k not in SPEC_KEYS]
    if spec.get("kind") != "screen":
        problems.append("Its kind is \"screen\".")
    title = str(spec.get("title", "")).strip()
    if not 1 <= len(title) <= 60:
        problems.append("It needs a title of up to 60 characters.")
    if spec.get("icon") and spec["icon"] not in ICONS:
        problems.append(f"Icon {spec['icon']!r} isn't one of MIA's.")
    if spec.get("owner") not in ("personal", "household"):
        problems.append("It's personal or the household's.")
    if child and spec.get("owner") == "household":
        problems.append("A child's screens are their own, not the household's.")
    from core.creation_sources import SOURCES, source_of

    rs, source = spec.get("record_set"), source_of(spec)
    if spec.get("source"):
        if source is None:
            problems.append(f"There's no source {spec['source']!r} (one of {', '.join(SOURCES)}).")
            return problems
        if rs:
            problems.append("It shows a source or its own record set, not both.")
        if child and source.money:
            problems.append("Money doesn't go on a child's screen.")
    else:
        if not isinstance(rs, dict) or not isinstance(rs.get("fields"), list):
            problems.append("It needs the record set it shows, with its fields.")
            return problems
        problems += [f"Record set: {p}" for p in check_fields(rs["fields"])]
        if not str(rs.get("name", "")).strip():
            problems.append("The record set needs a name.")
    fields = _fields(spec)
    if child and any(f["type"] == "money" for f in fields.values()):
        problems.append("Money doesn't go on a child's screen.")
    blocks = spec.get("blocks")
    if not isinstance(blocks, list) or not 1 <= len(blocks) <= MAX_BLOCKS:
        problems.append(f"It needs 1 to {MAX_BLOCKS} blocks.")
        return problems
    for i, b in enumerate(blocks, 1):
        where = f"Block {i}"
        if not isinstance(b, dict) or b.get("block") not in BLOCKS:
            problems.append(f"{where}: one of {', '.join(BLOCKS)}.")
            continue
        kind, allowed = b["block"], BLOCKS[b["block"]][0]
        where = f"Block {i} ({kind})"
        problems += [f"{where}: unknown part {k!r}." for k in b if k not in allowed]
        if len(str(b.get("title", ""))) > 60:
            problems.append(f"{where}: its title is too long.")
        if "limit" in b and not (isinstance(b["limit"], int) and 1 <= b["limit"] <= MAX_ROWS):
            problems.append(f"{where}: limit is 1 to {MAX_ROWS}.")
        named = []
        if kind == "stats":
            items = b.get("items")
            if not isinstance(items, list) or not 1 <= len(items) <= 6:
                problems.append(f"{where}: 1 to 6 items.")
            else:
                for n, item in enumerate(items, 1):
                    if not isinstance(item, dict) or set(item) - {"label", "value"} or not str(item.get("label", "")).strip():
                        problems.append(f"{where} item {n}: a label and a value.")
                    else:
                        problems += _value_problems(item.get("value"), fields, f"{where} item {n}")
        elif kind == "chart":
            if b.get("type") not in ("bar", "line"):
                problems.append(f"{where}: type is bar or line.")
            named.append(b.get("x"))
            if b.get("type") == "line" and fields.get(b.get("x"), {}).get("type") != "date":
                problems.append(f"{where}: a line runs over a date field.")
            problems += _value_problems(b.get("y"), fields, f"{where} y")
            if "by" in b and (b["by"] not in PERIODS or fields.get(b.get("x"), {}).get("type") != "date"):
                problems.append(f"{where}: by is day, week or month, over a date field.")
        elif kind == "table":
            columns = b.get("columns")
            if not isinstance(columns, list) or not columns:
                problems.append(f"{where}: which columns.")
            else:
                named += columns
        elif kind in ("list", "cards"):
            named += [b.get("title_field")] + list(b.get("detail_fields") or [])
        elif kind == "timeline":
            named += [b.get("date_field"), b.get("title_field")]
            if fields.get(b.get("date_field"), {}).get("type") != "date":
                problems.append(f"{where}: date_field is a date field.")
        elif kind == "meter":
            problems += _value_problems(b.get("value"), fields, f"{where} value")
            if not isinstance(b.get("goal"), (int, float)) or b["goal"] <= 0:
                problems.append(f"{where}: a goal above zero.")
            if not str(b.get("label", "")).strip():
                problems.append(f"{where}: a label.")
        elif kind == "note":
            if not 1 <= len(str(b.get("text", "")).strip()) <= 300:
                problems.append(f"{where}: up to 300 characters of text.")
        sort = str(b.get("sort", "")).lstrip("-")
        if sort:
            named.append(sort)
        problems += [f"{where}: there's no field {n!r}." for n in named if n not in fields]
    if source and any(isinstance(b, dict) and b.get("block") == "form" for b in blocks):
        problems.append(f"{source.title} is read here and added in {source.app}: no form.")
    if not any(b.get("block") in ("table", "list", "cards", "timeline", "form", "chart", "stats", "meter")
               for b in blocks if isinstance(b, dict)):
        problems.append("It should show the records or let someone add one.")
    return problems


# ------------------------------------------------------------------ assembling (all the working out is here)

def _text(field: dict, value, money) -> str:
    if value is None:
        return "—"
    if field["type"] == "money":
        return money(value)
    if field["type"] == "number":
        return f"{value:g}" if isinstance(value, float) else str(value)
    if field["type"] == "yesno":
        return "Yes" if value else "No"
    return str(value)


def _work_out(value: dict, records: list[dict], fields: dict, money) -> tuple[Optional[float], str]:
    (op, name), = value.items()
    if op == "count":
        return float(len(records)), str(len(records))
    present = [r["values"].get(name) for r in records if r["values"].get(name) is not None]
    field = fields[name]
    if not present:
        return None, "—"
    if op == "latest":
        latest = present[-1]  # the last one added (records keep the order they came in)
        return (latest if isinstance(latest, (int, float)) else None), _text(field, latest, money)
    if op in ("min", "max"):
        found = (min if op == "min" else max)(present)
        return (found if isinstance(found, (int, float)) else None), _text(field, found, money)
    total = sum(present)
    result = total if op == "sum" else total / len(present)
    return result, _text(field, round(result, 2), money)


def _sorted(records: list[dict], sort: str) -> list[dict]:
    if not sort:
        return list(reversed(records))  # newest first: records keep the order they came in
    name, reverse = sort.lstrip("-"), sort.startswith("-")
    have = [r for r in records if r["values"].get(name) is not None]
    missing = [r for r in records if r["values"].get(name) is None]
    return sorted(have, key=lambda r: r["values"][name], reverse=reverse) + missing


def _period(day, by: str) -> str:
    """Pure logic. "2026-11-04" -> its day, its week's Monday ("Week of Nov 2"), or its month ("Nov 2026")."""
    from datetime import date, timedelta

    try:
        d = date.fromisoformat(str(day)[:10])
    except ValueError:
        return "—"
    if by == "week":
        monday = d - timedelta(days=d.weekday())
        return f"Week of {monday:%b} {monday.day}"
    if by == "month":
        return f"{d:%b %Y}"
    return d.isoformat()


def assemble(spec: dict, record_set: Optional[dict], money=None) -> dict:
    """A checked spec and its record set (None for a draft not yet published) -> what web/made.js draws."""
    if money is None:
        from core.region import money
    fields = _fields(spec)
    records = list((record_set or {}).get("records") or [])
    out = []
    for b in spec["blocks"]:
        kind, title = b["block"], b.get("title", "")
        drawn = {"block": kind, "title": title}
        if kind == "stats":
            drawn["items"] = [{"label": i["label"], "value": _work_out(i["value"], records, fields, money)[1]}
                              for i in b["items"]]
        elif kind == "chart":
            groups: "OrderedDict[str, list]" = OrderedDict()
            ordered = sorted(records, key=lambda r: str(r["values"].get(b["x"]) or ""))
            for r in ordered:
                key = _period(r["values"].get(b["x"]), b["by"]) if b.get("by") else \
                    _text(fields[b["x"]], r["values"].get(b["x"]), money)
                groups.setdefault(key, []).append(r)
            points = []
            for label, members in groups.items():
                number, text = _work_out(b["y"], members, fields, money)
                points.append({"label": label, "value": number or 0, "text": text})
            drawn.update(type=b["type"], points=points,
                         text="; ".join(f"{p['label']}: {p['text']}" for p in points) or "No records yet.")
        elif kind in ("table", "list", "cards", "timeline"):
            rows = _sorted(records, b.get("sort", "") if kind != "timeline" else "-" + b["date_field"])
            rows = rows[: b.get("limit", 50 if kind != "cards" else 12)]
            if kind == "table":
                drawn["columns"] = [fields[c]["label"] for c in b["columns"]]
                drawn["rows"] = [{"id": r["id"], "cells": [_text(fields[c], r["values"].get(c), money) for c in b["columns"]]}
                                 for r in rows]
            elif kind == "timeline":
                drawn["items"] = [{"id": r["id"], "date": _text(fields[b["date_field"]], r["values"].get(b["date_field"]), money),
                                   "title": _text(fields[b["title_field"]], r["values"].get(b["title_field"]), money)}
                                  for r in rows]
            else:
                drawn["items"] = [{"id": r["id"], "title": _text(fields[b["title_field"]], r["values"].get(b["title_field"]), money),
                                   "details": [{"label": fields[d]["label"], "text": _text(fields[d], r["values"].get(d), money)}
                                               for d in b.get("detail_fields") or []]} for r in rows]
            drawn["total"] = len(records)
        elif kind == "meter":
            number, text = _work_out(b["value"], records, fields, money)
            share = max(0.0, min(1.0, (number or 0) / b["goal"]))
            drawn.update(label=b["label"], value=text, goal=b["goal"], share=round(share, 3),
                         text=f"{b['label']}: {text} of {b['goal']:g}")
        elif kind == "form":
            drawn["fields"] = [{"name": f["name"], "label": f["label"],
                                "type": {"yesno": "choice", "number": "number", "money": "money", "date": "date",
                                         "choice": "choice"}.get(f["type"], "text"),
                                **({"options": f["choices"]} if f["type"] == "choice" else {}),
                                **({"options": ["no", "yes"]} if f["type"] == "yesno" else {})}
                               for f in fields.values()]
        elif kind == "note":
            drawn["text"] = b["text"]
        out.append(drawn)
    return {"title": spec["title"], "icon": spec.get("icon") or "apps", "about": spec.get("about", ""), "blocks": out,
            "records": len(records), "fields": [dict(f) for f in fields.values()]}


__all__ = ["BLOCKS", "VALUES", "check", "assemble", "FIELD_TYPES"]
