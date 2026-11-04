"""
core.record_import
====================

A file nobody planned for becomes a record set and a screen (ACAF step 4,
DEC-0088/0089; `docs/ACAF_REVIEW.md` section 6: "an import with no store
becomes a record set and a screen"). A spec, not code: a CSV's columns are
read by code, each given a type from what's in it (a date, money, a number,
a choice among a few values, or text), and the screen is drafted from the
blueprint that fits its shape. No model is needed, so it works anywhere.

The draft keeps the rows beside it (`pending_rows`, not in the spec), and
publishing it (`creation.publish`) makes the record set and adds them in the
same approved, undoable step.
"""

from __future__ import annotations

import csv
import io
import re
from datetime import datetime
from typing import Optional

MAX_ROWS = 2000
MAX_COLUMNS = 12
CHOICE_MAX = 8
DATE_FORMATS = ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y", "%d.%m.%Y", "%Y/%m/%d", "%b %d, %Y", "%B %d, %Y")
MONEY_WORDS = re.compile(r"amount|price|cost|paid|total|spent|value|\$", re.I)


class ImportError_(ValueError):
    """A file that can't become a record set; the message says why."""


def _name(header: str, taken: set) -> str:
    base = re.sub(r"[^a-z0-9]+", "_", header.lower()).strip("_")[:28] or "column"
    if base[0].isdigit():
        base = "c_" + base
    name, n = base, 2
    while name in taken:
        name, n = f"{base}_{n}", n + 1
    taken.add(name)
    return name


def _date(text: str) -> Optional[str]:
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(text.strip(), fmt).date().isoformat()
        except ValueError:
            continue
    return None


def _number(text: str) -> Optional[float]:
    cleaned = text.strip().replace(",", "").replace("$", "").replace("€", "").replace("£", "")
    if cleaned.startswith("(") and cleaned.endswith(")"):
        cleaned = "-" + cleaned[1:-1]
    try:
        return float(cleaned)
    except ValueError:
        return None


def infer(text: str) -> tuple[list[dict], list[dict]]:
    """Pure logic. A CSV -> (fields, rows of values keyed by field name)."""
    try:
        sample = text[:4096]
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t") if sample.strip() else csv.excel
    except csv.Error:
        dialect = csv.excel
    table = [row for row in csv.reader(io.StringIO(text), dialect) if any(c.strip() for c in row)]
    if len(table) < 2:
        raise ImportError_("The file needs a header row and at least one row of data.")
    header, body = table[0][:MAX_COLUMNS], table[1:MAX_ROWS + 1]
    taken: set = set()
    fields = []
    for i, label in enumerate(header):
        cells = [r[i].strip() for r in body if i < len(r) and r[i].strip()]
        name = _name(label or f"column {i + 1}", taken)
        if cells and all(_date(c) for c in cells):
            kind = "date"
        elif cells and all(_number(c) is not None for c in cells):
            kind = "money" if MONEY_WORDS.search(label) or any("$" in c for c in cells) else "number"
        elif cells and len(set(c.lower() for c in cells)) <= CHOICE_MAX and len(cells) >= 2 * len(set(cells)):
            kind = "choice"
        else:
            kind = "text"
        field = {"name": name, "label": (label.strip() or f"Column {i + 1}")[:40], "type": kind}
        if kind == "choice":
            seen = []
            for c in cells:
                if c not in seen:
                    seen.append(c)
            field["choices"] = seen
        fields.append((i, field))
    rows = []
    for r in body:
        values = {}
        for i, f in fields:
            cell = r[i].strip() if i < len(r) else ""
            if not cell:
                values[f["name"]] = None
            elif f["type"] == "date":
                values[f["name"]] = _date(cell)
            elif f["type"] in ("money", "number"):
                values[f["name"]] = _number(cell)
            else:
                values[f["name"]] = cell[:500]
        rows.append(values)
    return [f for _, f in fields], rows


def draft(context, name: str, text: str) -> dict:
    """A draft screen for a file: its record set inferred, its blueprint by shape, its rows kept beside it."""
    from core import blueprints as bp
    from core.creation_spec import check

    fields, rows = infer(text)
    kinds = {f["type"] for f in fields}
    chosen = "log" if "date" in kinds and kinds & {"number", "money"} else "tracker"
    blueprint = bp.load()[chosen]
    title = " ".join((name or "Imported").split())[:60] or "Imported"
    spec = {"kind": "screen", "title": title, "icon": "inbox", "about": f"Imported from a file: {len(rows)} rows.",
            "owner": "personal", "record_set": {"name": title, "fields": fields}, "blocks": bp.fill(blueprint, fields)}
    problems = check(spec)
    if problems:
        raise ImportError_("It wouldn't make a working screen: " + "; ".join(problems[:3]))
    store = context.creations
    made = store.draft(spec, [], made_by="mia", why=f"imported {title} ({len(rows)} rows)",
                       blueprint=f"{blueprint['id']}@{blueprint['version']}")
    store.keep_rows(made["id"], rows)
    return made
