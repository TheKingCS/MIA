"""
core.requirement_actions
==========================

What each project needs, on the action contract (Procurement P1, DEC-0172; core/requirements.py): proposed in plain
words, approved, run, undoable (requirements.json writes through the atomic write).

- `requirement.add`: a project needs something ("the greenhouse needs four ventilation fans, under $40 each").
- `requirement.update`: change a need's quantity, specs, ceiling, condition, priority, needed-by date or status
  ("the fans are ordered").
- `requirement.got`: it's in hand (status acquired); P5 adds the inventory, budget and price record.
- `requirement.remove`: the project doesn't need it after all.
- `requirement.check`: check every open need against the workshop's materials and the inventory now.
"""

from __future__ import annotations

from core.actions import ACTION_TYPES, ActionError, ActionType, _need
from core.requirements import CONDITIONS, PRIORITIES, STATUSES


def _book(context):
    """The household's requirements, or ActionError."""
    return _need(context, "requirements")


def _project(context, params):
    """The project the params name (project_id, or `project` by its name); ActionError when none or several."""
    projects = _need(context, "projects")
    wanted = str(params.get("project_id") or "")
    found = next((p for p in projects.all_projects() if p.project_id == wanted), None) if wanted else None
    if found is None:
        words = " ".join(str(params.get("project") or "").lower().split())
        some = [p for p in projects.all_projects() if words and words in p.name.lower()]
        exact = [p for p in some if p.name.lower() == words]
        found = exact[0] if len(exact) == 1 else some[0] if len(some) == 1 else None
    if found is None:
        raise ActionError("Which project? Say its name.")
    return found


def _line(context, params):
    """The need the params name (requirement_id, or `item` within `project`); ActionError when none or several."""
    book = _book(context)
    found = book.get(str(params.get("requirement_id") or ""))
    if found is None and params.get("item"):
        project = _project(context, params) if (params.get("project") or params.get("project_id")) else None
        found = book.find(project.project_id if project else "", params.get("item"))
    if found is None:
        raise ActionError("Which need? Say the item and the project.")
    return found


def _number(value, what: str) -> float:
    """A number from a form or a tool ("$40", "4"); ActionError when it isn't one."""
    try:
        return float(str(value).replace("$", "").replace(",", "").strip())
    except ValueError:
        raise ActionError(f"What's the {what}?") from None


def _fields(params) -> dict:
    """The optional fields given, checked."""
    out = {}
    for key in ("unit", "specs", "alternatives", "fits", "needed_by"):
        if params.get(key) not in (None, ""):
            out[key] = " ".join(str(params[key]).split())
    if params.get("max_price") not in (None, ""):
        out["max_price"] = _number(params["max_price"], "most it should cost")
    for key, allowed in (("condition", CONDITIONS), ("priority", PRIORITIES), ("status", STATUSES)):
        if params.get(key) not in (None, ""):
            value = str(params[key]).strip().lower()
            if value not in allowed:
                raise ActionError(f"The {key} is one of: {', '.join(allowed)}.")
            out[key] = value
    return out


def _add_describe(context, params) -> str:
    """The approval sentence for `requirement.add`."""
    from core.region import money

    project = _project(context, params)
    item = " ".join(str(params.get("item") or "").split())
    if not item:
        raise ActionError("What does the project need?")
    qty = _number(params.get("quantity") or 1, "quantity")
    extra = _fields(params)
    tail = f", up to {money(extra['max_price'], ',.0f')}" if extra.get("max_price") else ""
    return f"{project.name} needs {qty:g} {extra.get('unit', '') + ' ' if extra.get('unit') else ''}{item}{tail}"


def _add_execute(context, params) -> str:
    """Does `requirement.add`, then checks what's on hand."""
    project = _project(context, params)
    try:
        line = _book(context).add(project.project_id, params.get("item"), _number(params.get("quantity") or 1,
                                                                                    "quantity"), **_fields(params))
    except ValueError as problem:
        raise ActionError(str(problem)) from None
    _book(context).refresh_owned(context)
    status = {"owned": " You already have enough on hand.", "partial": f" You have {line.have:g} on hand."}.get(line.status, "")
    return f"Added to {project.name}: {line.item}.{status}"


def _update_execute(context, params) -> str:
    """Does `requirement.update`."""
    line = _line(context, params)
    changes = _fields(params)
    if params.get("quantity") not in (None, ""):
        changes["quantity"] = _number(params["quantity"], "quantity")
    if not changes:
        raise ActionError("What should change?")
    _book(context).update(line.requirement_id, **changes)
    return f"Updated {line.item}."


def _got_execute(context, params) -> str:
    """Does `requirement.got`: it's in hand."""
    line = _line(context, params)
    _book(context).update(line.requirement_id, status="acquired", have=line.quantity)
    return f"Got it: {line.item}."


def _remove_execute(context, params) -> str:
    """Does `requirement.remove`."""
    line = _line(context, params)
    _book(context).remove(line.requirement_id)
    return f"{line.item} is off the list."


def _check_execute(context, params) -> str:
    """Does `requirement.check`: every open need against what's on hand."""
    changed = _book(context).refresh_owned(context)
    return f"Checked against what's on hand: {changed} changed." if changed else "Checked: nothing changed."


def _register() -> None:
    """Adds the requirement kinds to ACTION_TYPES. Runs once, when this module is imported."""
    optional = {"unit": "unit (optional)", "specs": "what it has to be (optional)",
                "alternatives": "what would also do (optional)", "fits": "what it must fit (optional)",
                "max_price": "most it should cost (optional)", "condition": "any, new or used",
                "priority": "first, later or nice to have", "needed_by": "date (optional)"}
    kinds = [
        ActionType("requirement.add", "Add a Need", {"project_id": "the project", "project": "or its name",
                                                     "item": "what it needs", "quantity": "how many", **optional},
                   _add_describe, _add_execute),
        ActionType("requirement.update", "Change", {"requirement_id": "the need", "item": "or its item",
                                                    "project": "and project", "quantity": "how many",
                                                    "status": "needed, ordered, acquired...", **optional},
                   lambda c, p: f"Change {_line(c, p).item}", _update_execute),
        ActionType("requirement.got", "Got It", {"requirement_id": "the need", "item": "or its item",
                                                 "project": "and project"},
                   lambda c, p: f"Mark {_line(c, p).item} in hand", _got_execute),
        ActionType("requirement.remove", "Not Needed", {"requirement_id": "the need", "item": "or its item",
                                                        "project": "and project"},
                   lambda c, p: f"Take {_line(c, p).item} off the list", _remove_execute),
        ActionType("requirement.check", "Check What's On Hand", {},
                   lambda c, p: (_book(c), "Check every open need against the workshop and inventory")[1],
                   _check_execute),
    ]
    for k in kinds:
        ACTION_TYPES[k.kind] = k


_register()
