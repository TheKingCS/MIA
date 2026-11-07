"""
core.record_actions
=====================

The shared machinery behind the web's "add, edit, delete anything"
(2026-10-06, DEC-0017). A screen's records are described once, as a
`Record` with its `Field`s and the store methods that add, update and
delete it; from that come its action kinds on the contract in
core/actions.py (Propose → Approve → Execute → Record → Undo), the plain
sentence the person approves ("Change Water: amount $45.00 → $52.10"),
and the web's forms (`field_dict`). Used by core/money_actions.py and
core/equipment_actions.py.

The engine keeps every rule here: amounts and intervals can't be
negative, dates are real dates, choices come from the store's own lists,
a referenced record must exist. Store errors (ValueError) come back as a
plain ActionError.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Callable

_BLANK = (None, "")


# core/actions.py imports the modules built on this one, so its names are
# looked up when an action runs, never at import (any import order works).
def ActionError(message: str):  # noqa: N802  (stands in for the class)
    """Makes core/actions.py's ActionError, looked up when called (core/actions.py imports the modules built on this
    one, so importing it here at load would be circular).
    """
    from core.actions import ActionError as error

    return error(message)


def _need(context, store: str):
    """core/actions.py's _need, looked up when called for the same reason: a store from the context, or ActionError."""
    from core.actions import _need as need

    return need(context, store)


@dataclass(frozen=True)
class Field:
    """One field of a record, as the form, the parser and the sentence see it: its parameter name, label, kind (text,
    money, rate, int, amount, number, date, choice, recurrence, asset, pick...), whether it's required, its choices,
    default, how a sentence names it, and whether to leave it out of a sentence at its default.
    """
    name: str  # the parameter, and the record's attribute
    label: str
    # text | textarea | money | rate | int | amount (≥ 0) | number (any) |
    # date | choice | recurrence | asset (a maintenance asset's id) |
    # pick (one of a list the page supplies: options = (the list's name,);
    # the action itself checks the id exists)
    kind: str
    required: bool = False
    options: tuple = ()
    default: Any = None
    say: str = ""  # how a sentence names it, if not the label in lower case
    quiet_default: bool = False  # leave it out of a sentence while it's at its default

    @property
    def said(self) -> str:
        """How a sentence names the field (its `say`, else the label in lower case)."""
        return self.say or self.label.lower()


@dataclass(frozen=True)
class Record:
    """One kind of record a screen edits, described once: its key and noun, the id parameter, the store attribute and
    the store's get/add/update/delete method names, its fields, what to call one in a sentence, and what to add after
    "Delete the ...". Its add, edit and delete action kinds are made from this.
    """
    key: str  # "bill"
    noun: str  # "bill"
    id_param: str  # "bill_id"
    get: str  # the store's method names
    add: str
    update: str
    delete: str
    fields: tuple = field(default_factory=tuple)
    title_attrs: tuple = ("name",)  # what to call a record in a sentence
    store: str = "budget"  # the context attribute that holds them
    delete_note: str = ""  # said after "Delete the …", e.g. what stays


# ------------------------------------------------------------------ values


def parse(f: Field, raw) -> Any:
    """One parameter, checked. Raises ActionError with a plain sentence."""
    from core.calendar_manager import RECURRENCE_TYPES

    if f.kind in ("money", "rate", "int", "amount", "number"):
        if raw in _BLANK:
            if f.required:
                raise ActionError(f"{f.label} is needed.")
            return f.default
        try:
            value = float(str(raw).replace(",", "").lstrip("$").strip())
        except ValueError:
            raise ActionError(f"{f.label} has to be a number.") from None
        if f.kind != "number" and value < 0:
            raise ActionError(f"{f.label} can't be negative.")
        if f.kind == "int":
            if value != int(value):
                raise ActionError(f"{f.label} has to be a whole number.")
            return int(value)
        return round(value, 2) if f.kind in ("money", "rate") else value
    if f.kind == "date":
        if raw in _BLANK:
            if f.required:
                raise ActionError(f"{f.label} is needed.")
            return None if f.default is None else f.default
        try:
            return date.fromisoformat(str(raw)).isoformat()
        except ValueError:
            raise ActionError(f"{f.label} has to be a date.") from None
    if f.kind == "recurrence":
        if raw in _BLANK or raw == "none":
            return None
        if raw not in RECURRENCE_TYPES:
            raise ActionError(f"{f.label} has to be one of: {', '.join(RECURRENCE_TYPES)}.")
        return raw
    if f.kind == "choice":
        if raw in _BLANK:
            return f.default
        if raw not in f.options:
            raise ActionError(f"{f.label} has to be one of the list.")
        return raw
    text = "" if raw is None else str(raw).strip()
    if f.required and not text:
        raise ActionError(f"{f.label} is needed.")
    return text


def show(f: Field, value, context=None) -> str:
    """A value as said in a sentence."""
    from core.region import money

    if value in _BLANK:
        return "none"
    if f.kind == "money":
        return money(value)
    if f.kind == "rate":
        return f"{float(value):g}%"
    if f.kind in ("int", "amount", "number"):
        return f"{float(value):g}"
    if f.kind == "date":
        day = date.fromisoformat(value)
        return f"{day:%b} {day.day}, {day.year}" if day.year != date.today().year else f"{day:%b} {day.day}"
    if f.kind == "asset" and context is not None:
        maintenance = getattr(context, "maintenance", None)
        asset = maintenance.get_asset(value) if maintenance is not None else None
        return asset.name if asset is not None else str(value)
    return str(value)


def title(record: Record, item) -> str:
    """What a sentence calls a record: its first non-empty title attribute, else the noun."""
    for attr in record.title_attrs:
        value = getattr(item, attr, "")
        if value:
            return str(value)
    return record.noun


def get(context, record: Record, params):
    """The record the params name, through the store's get method, or ActionError."""
    item = getattr(_need(context, record.store), record.get)(str(params.get(record.id_param, "")))
    if item is None:
        raise ActionError(f"That {record.noun} isn't there anymore.")
    return item


def values_of(record: Record, params, only_given: bool, context=None) -> dict:
    """The record's field values parsed from the params (all fields, or only the ones given for an edit); an asset field
    must name a maintenance asset that exists.
    """
    values = {}
    for f in record.fields:
        if only_given and f.name not in params:
            continue
        values[f.name] = parse(f, params.get(f.name))
        if f.kind == "asset" and values[f.name] and context is not None:
            if _need(context, "maintenance").get_asset(values[f.name]) is None:
                raise ActionError("That asset isn't there anymore.")
    return values


def changes(record: Record, item, values: dict) -> list[tuple[Field, Any, Any]]:
    """What would really change. A blank is a blank (None and "" are the
    same to a person), and a cleared text field stays text ("")."""
    by_name = {f.name: f for f in record.fields}
    found = []
    for k, new in values.items():
        old = getattr(item, k)
        if old in _BLANK and new in _BLANK:
            continue
        if new is None and isinstance(old, str):
            new = ""
        if old != new:
            found.append((by_name[k], old, new))
    return found


def item_id(record: Record, item) -> str:
    """A record's id."""
    return getattr(item, record.id_param)


def _store_call(fn: Callable, *args, **kwargs):
    """Calls a store method, turning the ValueError a store's own rule raises into an ActionError said plainly."""
    try:
        return fn(*args, **kwargs)
    except ValueError as problem:
        raise ActionError(str(problem)) from None  # a store's own rule, said plainly


# ------------------------------------------------------------------ add / edit / delete


def add_describe(record: Record):
    """Builds the describe for adding a record: "Add the <noun> <name>: <details>", leaving out blanks, quiet
    defaults and optional zeros.
    """
    def describe(context, params) -> str:
        values = values_of(record, params, only_given=False, context=context)
        main = [f for f in record.fields if f.kind != "textarea" and values.get(f.name) not in _BLANK
                and not (f.quiet_default and values.get(f.name) == f.default)
                and not (not f.required and f.kind in ("money", "amount", "int", "number") and values.get(f.name) == 0)]
        used = next((a for a in record.title_attrs if values.get(a)), None)
        name = str(values[used]) if used else record.noun
        details = ", ".join(f"{f.said} {show(f, values[f.name], context)}" for f in main if f.name != used)
        return f"Add the {record.noun} {name}" + (f": {details}" if details else "")
    return describe


def add_execute(record: Record):
    """Builds the execute for adding a record through the store's add method."""
    def execute(context, params) -> str:
        values = values_of(record, params, only_given=False, context=context)
        item = _store_call(getattr(_need(context, record.store), record.add), **values)
        return f"Added the {record.noun} {title(record, item)}."
    return execute


def edit_describe(record: Record):
    """Builds the describe for editing a record: each changed field as old → new ("Nothing to change" when none are)."""
    def describe(context, params) -> str:
        item = get(context, record, params)
        found = changes(record, item, values_of(record, params, only_given=True, context=context))
        if not found:
            raise ActionError("Nothing to change.")
        said = "; ".join(f"{f.said} {show(f, old, context)} → {show(f, new, context)}" for f, old, new in found)
        return f"Change {title(record, item)}: {said}"
    return describe


def edit_execute(record: Record):
    """Builds the execute for editing a record: only the changed fields go to the store's update method."""
    def execute(context, params) -> str:
        item = get(context, record, params)
        values = {f.name: new for f, _old, new in
                  changes(record, item, values_of(record, params, only_given=True, context=context))}
        _store_call(getattr(_need(context, record.store), record.update), item_id(record, item), **values)
        return f"{title(record, item)} is updated."
    return execute


def delete_describe(record: Record):
    """Builds the describe for deleting a record, with its amount when it has one, and the record's delete note."""
    def describe(context, params) -> str:
        item = get(context, record, params)
        amount = next((f for f in record.fields if f.kind == "money"), None)
        extra = f" ({show(amount, getattr(item, amount.name))})" if amount and getattr(item, amount.name) else ""
        return f"Delete the {record.noun} {title(record, item)}{extra}." + (f" {record.delete_note}" if record.delete_note else "")
    return describe


def delete_execute(record: Record):
    """Builds the execute for deleting a record (undo brings it back)."""
    def execute(context, params) -> str:
        item = get(context, record, params)
        _store_call(getattr(_need(context, record.store), record.delete), item_id(record, item))
        return f"Deleted the {record.noun} {title(record, item)}. Undo brings it back."
    return execute


def record_kinds(record: Record, child_ok: bool = False) -> list:
    """`<key>.add`, `<key>.edit`, `<key>.delete` for one record."""
    from core.actions import ActionType

    names = {f.name: f.label for f in record.fields}
    return [
        ActionType(f"{record.key}.add", "Add", dict(names), add_describe(record), add_execute(record), child_ok),
        ActionType(f"{record.key}.edit", "Edit", {record.id_param: f"the {record.noun}", **names},
                   edit_describe(record), edit_execute(record), child_ok),
        ActionType(f"{record.key}.delete", "Delete", {record.id_param: f"the {record.noun}"},
                   delete_describe(record), delete_execute(record), child_ok),
    ]


def field_dict(f: Field) -> dict:
    """A field as the web's forms read it (JSON-ready)."""
    from core.calendar_manager import RECURRENCE_TYPES

    options = (list(f.options) if f.kind in ("choice", "pick")
               else (["none", *RECURRENCE_TYPES] if f.kind == "recurrence" else []))
    return {"name": f.name, "label": f.label, "type": f.kind, "required": f.required, "options": options,
            "default": f.default}


def record_form(record: Record) -> dict:
    """The form a screen shows for a record: its noun, id parameter and fields (field_dict)."""
    return {"noun": record.noun, "id_param": record.id_param, "fields": [field_dict(f) for f in record.fields]}

