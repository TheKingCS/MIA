"""
core.money_actions
====================

Every change the Money screen can make (2026-10-06, DEC-0017: the web
does everything the PC app's Budget screen does), as action kinds on the
contract in core/actions.py: Propose → Approve → Execute → Record → Undo.

One table, `RECORDS`, describes each kind of money record (bills, income
sources, income, expenses, debts): its fields, and the BudgetManager
methods that add, edit and delete it. From it come the action kinds
(`bill.add`, `bill.edit`, `bill.delete`, ...), the sentence the person
approves ("Change Electric: amount $120.00 → $130.00"), and the forms the
web shows (`form_spec()`), so they can't drift apart. Plus `debt.pay`
and monthly budget targets.

The engine keeps every rule: amounts can't be negative, dates are real
dates, categories come from the budget's own lists. None of these are
for a child account (core/actions.py refuses them).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Optional

from core.actions import ACTION_TYPES, ActionError, ActionType, _need


@dataclass(frozen=True)
class Field:
    name: str  # the parameter, and the record's attribute
    label: str
    kind: str  # text | textarea | money | rate | date | choice | recurrence
    required: bool = False
    options: tuple = ()
    default: Any = None
    say: str = ""  # how a sentence names it, if not the label in lower case

    @property
    def said(self) -> str:
        return self.say or self.label.lower()


@dataclass(frozen=True)
class Record:
    key: str  # "bill"
    noun: str  # "bill"
    id_param: str  # "bill_id"
    get: str  # BudgetManager method names
    add: str
    update: str
    delete: str
    fields: tuple = field(default_factory=tuple)
    title_attrs: tuple = ("name",)  # what to call a record in a sentence


def _lists():
    from core.budget_manager import DEBT_TYPES, EXPENSE_CATEGORIES, INCOME_CATEGORIES

    return tuple(EXPENSE_CATEGORIES), tuple(INCOME_CATEGORIES), tuple(DEBT_TYPES)


_EXPENSE, _INCOME, _DEBT = _lists()

RECORDS: dict[str, Record] = {r.key: r for r in (
    Record("bill", "bill", "bill_id", "get_bill", "add_bill", "update_bill", "delete_bill", (
        Field("name", "Name", "text", True),
        Field("amount", "Amount", "money", True),
        Field("due_date", "Due date", "date", True, say="due"),
        Field("recurrence", "Repeats", "recurrence", default="monthly", say="repeats"),
        Field("category", "Category", "choice", options=_EXPENSE, default="Utilities"),
        Field("notes", "Notes", "textarea"),
    )),
    Record("income_source", "income source", "source_id", "get_income_source", "add_income_source",
           "update_income_source", "delete_income_source", (
               Field("name", "Name", "text", True),
               Field("expected_amount", "Expected amount", "money", True, say="expected"),
               Field("next_date", "Next date", "date", True, say="next"),
               Field("recurrence", "Repeats", "recurrence", default="biweekly", say="repeats"),
               Field("category", "Category", "choice", options=_INCOME, default="Salary"),
               Field("notes", "Notes", "textarea"),
           )),
    Record("income", "income", "entry_id", "get_income", "add_income", "update_income", "delete_income", (
        Field("amount", "Amount", "money", True),
        Field("date", "Date", "date", True),
        Field("category", "Category", "choice", options=_INCOME, default="Other"),
        Field("description", "What it was", "text", say="for"),
        Field("notes", "Notes", "textarea"),
    ), ("description", "category")),
    Record("expense", "expense", "entry_id", "get_expense", "add_expense", "update_expense", "delete_expense", (
        Field("amount", "Amount", "money", True),
        Field("date", "Date", "date", True),
        Field("category", "Category", "choice", options=_EXPENSE, default="Other"),
        Field("description", "What it was", "text", say="for"),
        Field("payee", "Paid to", "text", say="paid to"),
        Field("notes", "Notes", "textarea"),
    ), ("description", "payee", "category")),
    Record("debt", "debt", "debt_id", "get_debt", "add_debt", "update_debt", "delete_debt", (
        Field("name", "Name", "text", True),
        Field("balance", "Balance", "money", True),
        Field("interest_rate", "APR (%)", "rate", True, say="APR"),
        Field("minimum_payment", "Minimum payment", "money", default=0.0, say="minimum"),
        Field("debt_type", "Type", "choice", options=_DEBT, default="Credit Card"),
        Field("promo_apr", "Promo APR (%)", "rate", say="promo APR"),
        Field("promo_expires_date", "Promo ends", "date", say="promo ends"),
        Field("notes", "Notes", "textarea"),
    )),
)}

_BLANK = (None, "")


# ------------------------------------------------------------------ values


def _parse(f: Field, raw) -> Any:
    """One parameter, checked. Raises ActionError with a plain sentence."""
    from core.calendar_manager import RECURRENCE_TYPES

    if f.kind in ("money", "rate"):
        if raw in _BLANK:
            if f.required:
                raise ActionError(f"{f.label} is needed.")
            return f.default
        try:
            value = round(float(str(raw).replace(",", "").lstrip("$").strip()), 2)
        except ValueError:
            raise ActionError(f"{f.label} has to be a number.") from None
        if value < 0:
            raise ActionError(f"{f.label} can't be negative.")
        return value
    if f.kind == "date":
        if raw in _BLANK:
            if f.required:
                raise ActionError(f"{f.label} is needed.")
            return None
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


def _show(f: Field, value) -> str:
    """Pure logic. A value as said in a sentence."""
    from core.region import money

    if value in _BLANK:
        return "none"
    if f.kind == "money":
        return money(value)
    if f.kind == "rate":
        return f"{float(value):g}%"
    if f.kind == "date":
        day = date.fromisoformat(value)
        return f"{day:%b} {day.day}, {day.year}" if day.year != date.today().year else f"{day:%b} {day.day}"
    return str(value)


def _title(record: Record, item) -> str:
    for attr in record.title_attrs:
        value = getattr(item, attr, "")
        if value:
            return str(value)
    return record.noun


def _get(context, record: Record, params):
    item = getattr(_need(context, "budget"), record.get)(str(params.get(record.id_param, "")))
    if item is None:
        raise ActionError(f"That {record.noun} isn't there anymore.")
    return item


def _values(record: Record, params, only_given: bool) -> dict:
    values = {}
    for f in record.fields:
        if only_given and f.name not in params:
            continue
        values[f.name] = _parse(f, params.get(f.name))
    return values


def _changes(record: Record, item, values: dict) -> list[tuple[Field, Any, Any]]:
    by_name = {f.name: f for f in record.fields}
    return [(by_name[k], getattr(item, k), v) for k, v in values.items() if getattr(item, k) != v]


# ------------------------------------------------------------------ add / edit / delete


def _add_describe(record: Record):
    def describe(context, params) -> str:
        values = _values(record, params, only_given=False)
        main = [f for f in record.fields if f.kind != "textarea" and values.get(f.name) not in _BLANK]
        used = next((a for a in record.title_attrs if values.get(a)), None)
        title = str(values[used]) if used else record.noun
        details = ", ".join(f"{f.said} {_show(f, values[f.name])}" for f in main if f.name != used)
        return f"Add the {record.noun} {title}: {details}"
    return describe


def _add_execute(record: Record):
    def execute(context, params) -> str:
        values = _values(record, params, only_given=False)
        item = getattr(_need(context, "budget"), record.add)(**values)
        return f"Added the {record.noun} {_title(record, item)}."
    return execute


def _edit_describe(record: Record):
    def describe(context, params) -> str:
        item = _get(context, record, params)
        changes = _changes(record, item, _values(record, params, only_given=True))
        if not changes:
            raise ActionError("Nothing to change.")
        said = "; ".join(f"{f.said} {_show(f, old)} → {_show(f, new)}" for f, old, new in changes)
        return f"Change {_title(record, item)}: {said}"
    return describe


def _edit_execute(record: Record):
    def execute(context, params) -> str:
        item = _get(context, record, params)
        values = {f.name: new for f, _old, new in _changes(record, item, _values(record, params, only_given=True))}
        getattr(_need(context, "budget"), record.update)(item_id(record, item), **values)
        return f"{_title(record, item)} is updated."
    return execute


def item_id(record: Record, item) -> str:
    return getattr(item, record.id_param)


def _delete_describe(record: Record):
    def describe(context, params) -> str:
        item = _get(context, record, params)
        amount = next((f for f in record.fields if f.kind == "money"), None)
        extra = f" ({_show(amount, getattr(item, amount.name))})" if amount else ""
        note = " Its past payments stay in Expenses." if record.key == "bill" else ""
        return f"Delete the {record.noun} {_title(record, item)}{extra}.{note}"
    return describe


def _delete_execute(record: Record):
    def execute(context, params) -> str:
        item = _get(context, record, params)
        getattr(_need(context, "budget"), record.delete)(item_id(record, item))
        return f"Deleted the {record.noun} {_title(record, item)}. Undo brings it back."
    return execute


# ------------------------------------------------------------------ debts and budgets


_PAYMENT = Field("amount", "Payment", "money", True)
_TARGET = Field("monthly_amount", "Monthly budget", "money", True)
_CATEGORY = Field("category", "Category", "choice", True, _EXPENSE)


def _describe_debt_pay(context, params) -> str:
    from core.region import money

    debt = _get(context, RECORDS["debt"], params)
    amount = _parse(_PAYMENT, params.get("amount", debt.minimum_payment or None))
    return f"Record a {money(amount)} payment on {debt.name} ({money(max(0.0, debt.balance - amount))} left)"


def _debt_pay(context, params) -> str:
    from core.region import money

    debt = _get(context, RECORDS["debt"], params)
    amount = _parse(_PAYMENT, params.get("amount", debt.minimum_payment or None))
    _need(context, "budget").record_debt_payment(debt.debt_id, amount)
    return f"Paid {money(amount)} on {debt.name}. {money(debt.balance)} left."


def _describe_target(context, params) -> str:
    from core.region import money

    category = _parse(_CATEGORY, params.get("category"))
    return f"Set a monthly {category} budget of {money(_parse(_TARGET, params.get('monthly_amount')))}"


def _set_target(context, params) -> str:
    category = _parse(_CATEGORY, params.get("category"))
    _need(context, "budget").set_budget_target(category, _parse(_TARGET, params.get("monthly_amount")))
    return f"{category} has a monthly budget now."


def _describe_target_delete(context, params) -> str:
    category = _parse(_CATEGORY, params.get("category"))
    if _need(context, "budget").get_budget_target(category) is None:
        raise ActionError(f"There's no {category} budget.")
    return f"Remove the monthly {category} budget"


def _delete_target(context, params) -> str:
    category = _parse(_CATEGORY, params.get("category"))
    _need(context, "budget").delete_budget_target(category)
    return f"The {category} budget is removed."


# ------------------------------------------------------------------ the kinds


def _kinds() -> list[ActionType]:
    kinds = []
    for record in RECORDS.values():
        names = {f.name: f.label for f in record.fields}
        kinds += [
            ActionType(f"{record.key}.add", "Add", dict(names), _add_describe(record), _add_execute(record)),
            ActionType(f"{record.key}.edit", "Edit", {record.id_param: f"the {record.noun}", **names},
                       _edit_describe(record), _edit_execute(record)),
            ActionType(f"{record.key}.delete", "Delete", {record.id_param: f"the {record.noun}"},
                       _delete_describe(record), _delete_execute(record)),
        ]
    kinds += [
        ActionType("debt.pay", "Record payment", {"debt_id": "the debt", "amount": "what was paid"},
                   _describe_debt_pay, _debt_pay),
        ActionType("budget_target.set", "Set budget", {"category": "the category", "monthly_amount": "per month"},
                   _describe_target, _set_target),
        ActionType("budget_target.delete", "Remove", {"category": "the category"},
                   _describe_target_delete, _delete_target),
    ]
    return kinds


MONEY_ACTIONS: dict[str, ActionType] = {k.kind: k for k in _kinds()}
ACTION_TYPES.update(MONEY_ACTIONS)


def form_spec() -> dict:
    """What the web's forms ask for, from the same table (JSON-ready)."""
    from core.calendar_manager import RECURRENCE_TYPES

    def as_dict(f: Field) -> dict:
        options = list(f.options) if f.kind == "choice" else (["none", *RECURRENCE_TYPES] if f.kind == "recurrence"
                                                              else [])
        return {"name": f.name, "label": f.label, "type": f.kind, "required": f.required, "options": options,
                "default": f.default}

    forms = {key: {"noun": r.noun, "id_param": r.id_param, "fields": [as_dict(f) for f in r.fields]}
             for key, r in RECORDS.items()}
    forms["debt_payment"] = {"noun": "payment", "id_param": "debt_id", "fields": [as_dict(_PAYMENT)]}
    forms["budget_target"] = {"noun": "budget", "id_param": None, "fields": [as_dict(_CATEGORY), as_dict(_TARGET)]}
    return forms
