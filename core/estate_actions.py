"""
core.estate_actions
=====================

Every change the Real Estate screen makes (2026-10-06, DEC-0017/0018), as
action kinds on the contract in core/actions.py: properties (add, edit,
delete, with the concept's status, rent and location), recording rent
received and an expense against a property (both land in Money, tagged to
it), and "track its upkeep", which gives a property its own Maintenance
asset so its tasks (HVAC filter, gutters) live in one place. Money and
property: never for a child.
"""

from __future__ import annotations

from core.actions import ACTION_TYPES, ActionError, ActionType, _need
from core.record_actions import Field, Record, field_dict, get, parse, record_form, record_kinds


def _lists():
    from core.budget_manager import EXPENSE_CATEGORIES
    from core.real_estate_manager import PROPERTY_STATUSES, PROPERTY_TYPES

    return tuple(PROPERTY_TYPES), ("",) + tuple(PROPERTY_STATUSES), tuple(EXPENSE_CATEGORIES)


_TYPES, _STATUSES, _EXPENSES = _lists()

RECORDS: dict[str, Record] = {r.key: r for r in (
    Record("property", "property", "property_id", "get_property", "add_property", "update_property", "delete_property",
           store="real_estate", delete_note="Its rent and expenses stay in Money.", fields=(
               Field("name", "Name", "text", True),
               Field("property_type", "Kind", "choice", options=_TYPES, default="Rental", say="kind"),
               Field("status", "Status", "choice", options=_STATUSES, default="", quiet_default=True),
               Field("location", "Where", "text", say="in"),
               Field("monthly_rent", "Rent per month", "money", default=0.0, say="rent"),
               Field("current_value", "What it's worth", "money", default=0.0, say="worth"),
               Field("mortgage_balance", "Mortgage owed", "money", default=0.0, say="owed"),
               Field("purchase_date", "Bought on", "date", say="bought"),
               Field("purchase_price", "Price paid", "money", default=0.0, say="price"),
               Field("original_loan_amount", "Loan amount (at the start)", "money", default=0.0, say="loan"),
               Field("interest_rate_pct", "Mortgage rate (%)", "rate", default=0.0, say="rate"),
               Field("loan_term_months", "Loan term (months)", "int", default=0, say="term (months)"),
               Field("loan_start_date", "Loan started", "date", say="loan started"),
               Field("notes", "Notes", "textarea"),
           )),
)}

_AMOUNT = Field("amount", "Amount", "money", True)
_DATE = Field("date", "Date", "date")
_WHAT = Field("description", "What it was", "text", say="for")
_CATEGORY = Field("category", "Category", "choice", options=_EXPENSES, default="Maintenance")


def _property(context, params):
    return get(context, RECORDS["property"], params)


def _rent_amount(prop, params):
    raw = params.get("amount")
    return parse(_AMOUNT, raw if raw not in (None, "") else (prop.monthly_rent or None))


def _describe_rent(context, params) -> str:
    from core.region import money

    prop = _property(context, params)
    when = parse(_DATE, params.get("date"))
    return f"Record {money(_rent_amount(prop, params))} rent from {prop.name}" + (f" on {when}" if when else " today")


def _rent(context, params) -> str:
    from core.region import money

    prop = _property(context, params)
    amount = _rent_amount(prop, params)
    _need(context, "budget")
    context.real_estate.record_rental_income(prop.property_id, amount, parse(_DATE, params.get("date")),
                                             parse(_WHAT, params.get("description")) or f"Rent: {prop.name}")
    return f"{money(amount)} rent from {prop.name} is in Money."


def _describe_expense(context, params) -> str:
    from core.region import money

    prop = _property(context, params)
    what = parse(_WHAT, params.get("description"))
    return (f"Record a {money(parse(_AMOUNT, params.get('amount')))} {parse(_CATEGORY, params.get('category')).lower()} "
            f"expense on {prop.name}" + (f" ({what})" if what else ""))


def _expense(context, params) -> str:
    prop = _property(context, params)
    _need(context, "budget")
    context.real_estate.record_property_expense(prop.property_id, parse(_AMOUNT, params.get("amount")),
                                                parse(_CATEGORY, params.get("category")), parse(_DATE, params.get("date")),
                                                parse(_WHAT, params.get("description")))
    return f"The expense is recorded against {prop.name}."


def _describe_upkeep(context, params) -> str:
    prop = _property(context, params)
    maintenance = _need(context, "maintenance")
    if prop.maintenance_asset_id and maintenance.get_asset(prop.maintenance_asset_id) is not None:
        raise ActionError(f"{prop.name}'s upkeep is already tracked.")
    return f"Track {prop.name}'s upkeep in Maintenance (filters, gutters, inspections)"


def _upkeep(context, params) -> str:
    prop = _property(context, params)
    asset = context.maintenance.add_asset(prop.name, "Property", notes="Its property in Real Estate.")
    context.real_estate.update_property(prop.property_id, maintenance_asset_id=asset.asset_id)
    return f"{prop.name}'s upkeep is tracked. Add its tasks here or in Maintenance."


def _kinds() -> list[ActionType]:
    kinds = record_kinds(RECORDS["property"])
    kinds += [
        ActionType("property.rent", "Record rent", {"property_id": "", "amount": "default: its monthly rent", "date": "",
                                                    "description": ""}, _describe_rent, _rent),
        ActionType("property.expense", "Add expense", {"property_id": "", "amount": "", "category": "", "date": "",
                                                       "description": ""}, _describe_expense, _expense),
        ActionType("property.track_upkeep", "Track upkeep", {"property_id": ""}, _describe_upkeep, _upkeep),
    ]
    return kinds


ESTATE_ACTIONS: dict[str, ActionType] = {k.kind: k for k in _kinds()}
ACTION_TYPES.update(ESTATE_ACTIONS)


def form_spec() -> dict:
    forms = {"property": record_form(RECORDS["property"])}
    forms["rent"] = {"noun": "rent", "id_param": "property_id", "fields": [field_dict(f) for f in (_AMOUNT, _DATE, _WHAT)]}
    forms["expense"] = {"noun": "expense", "id_param": "property_id",
                        "fields": [field_dict(f) for f in (_AMOUNT, _CATEGORY, _DATE, _WHAT)]}
    return forms
