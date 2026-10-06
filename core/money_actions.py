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

from core.actions import ACTION_TYPES, ActionError, ActionType, _need
from core.record_actions import Field, Record, field_dict, get, parse, record_form, record_kinds


def _lists():
    from core.budget_manager import DEBT_TYPES, EXPENSE_CATEGORIES, INCOME_CATEGORIES

    return tuple(EXPENSE_CATEGORIES), tuple(INCOME_CATEGORIES), tuple(DEBT_TYPES)


_EXPENSE, _INCOME, _DEBT = _lists()

RECORDS: dict[str, Record] = {r.key: r for r in (
    Record("bill", "bill", "bill_id", "get_bill", "add_bill", "update_bill", "delete_bill", delete_note="Its past payments stay in Expenses.", fields=(
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

# ------------------------------------------------------------------ debts and budgets


_PAYMENT = Field("amount", "Payment", "money", True)
_TARGET = Field("monthly_amount", "Monthly budget", "money", True)
_CATEGORY = Field("category", "Category", "choice", True, _EXPENSE)


def _describe_debt_pay(context, params) -> str:
    from core.region import money

    debt = get(context, RECORDS["debt"], params)
    amount = parse(_PAYMENT, params.get("amount", debt.minimum_payment or None))
    return f"Record a {money(amount)} payment on {debt.name} ({money(max(0.0, debt.balance - amount))} left)"


def _debt_pay(context, params) -> str:
    from core.region import money

    debt = get(context, RECORDS["debt"], params)
    amount = parse(_PAYMENT, params.get("amount", debt.minimum_payment or None))
    _need(context, "budget").record_debt_payment(debt.debt_id, amount)
    return f"Paid {money(amount)} on {debt.name}. {money(debt.balance)} left."


def _describe_target(context, params) -> str:
    from core.region import money

    category = parse(_CATEGORY, params.get("category"))
    return f"Set a monthly {category} budget of {money(parse(_TARGET, params.get('monthly_amount')))}"


def _set_target(context, params) -> str:
    category = parse(_CATEGORY, params.get("category"))
    _need(context, "budget").set_budget_target(category, parse(_TARGET, params.get("monthly_amount")))
    return f"{category} has a monthly budget now."


def _describe_target_delete(context, params) -> str:
    category = parse(_CATEGORY, params.get("category"))
    if _need(context, "budget").get_budget_target(category) is None:
        raise ActionError(f"There's no {category} budget.")
    return f"Remove the monthly {category} budget"


def _delete_target(context, params) -> str:
    category = parse(_CATEGORY, params.get("category"))
    _need(context, "budget").delete_budget_target(category)
    return f"The {category} budget is removed."


# ------------------------------------------------------------------ the kinds


def _kinds() -> list[ActionType]:
    kinds = []
    for record in RECORDS.values():
        kinds += record_kinds(record)
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
    forms = {key: record_form(r) for key, r in RECORDS.items()}
    forms["debt_payment"] = {"noun": "payment", "id_param": "debt_id", "fields": [field_dict(_PAYMENT)]}
    forms["budget_target"] = {"noun": "budget", "id_param": None, "fields": [field_dict(_CATEGORY), field_dict(_TARGET)]}
    return forms
