"""
core.estate_actions
=====================

Every change the Real Estate screen makes (2026-10-06, DEC-0017/0018), as
action kinds on the contract in core/actions.py: properties (add, edit,
delete, with the concept's status, rent and location), recording rent
received and an expense against a property (both land in Money, tagged to
it), recording its sale (2026-11-09: what it came to, kept with it), and "track its upkeep", which gives a property its own Maintenance
asset so its tasks (HVAC filter, gutters) live in one place. Money and
property: never for a child.
"""

from __future__ import annotations

from core.actions import ACTION_TYPES, ActionError, ActionType, _need
from core.record_actions import Field, Record, field_dict, get, parse, record_form, record_kinds


def _lists():
    """The property type and status choices and the expense categories, imported late so this module loads before the
    stores.
    """
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
_PRICE = Field("sale_price", "Sale price", "money", True, say="for")
_COSTS = Field("selling_costs", "Selling costs (commission, closing)", "money", default=0.0, say="costs")


def _property(context, params):
    """The property the params name."""
    return get(context, RECORDS["property"], params)


def _rent_amount(prop, params):
    """The rent amount from the params, or the property's monthly rent when blank."""
    raw = params.get("amount")
    return parse(_AMOUNT, raw if raw not in (None, "") else (prop.monthly_rent or None))


def _describe_rent(context, params) -> str:
    """The sentence the approval card shows for `property.rent` (Propose); raises ActionError when it can't be done."""
    from core.region import money

    prop = _property(context, params)
    when = parse(_DATE, params.get("date"))
    return f"Record {money(_rent_amount(prop, params))} rent from {prop.name}" + (f" on {when}" if when else " today")


def _rent(context, params) -> str:
    """Does `property.rent` once approved, and says what happened. It lands in Money as rental income tagged to the property."""
    from core.region import money

    prop = _property(context, params)
    amount = _rent_amount(prop, params)
    _need(context, "budget")
    context.real_estate.record_rental_income(prop.property_id, amount, parse(_DATE, params.get("date")),
                                             parse(_WHAT, params.get("description")) or f"Rent: {prop.name}")
    return f"{money(amount)} rent from {prop.name} is in Money."


def _describe_expense(context, params) -> str:
    """The sentence the approval card shows for `property.expense` (Propose); raises ActionError when it can't be done."""
    from core.region import money

    prop = _property(context, params)
    what = parse(_WHAT, params.get("description"))
    return (f"Record a {money(parse(_AMOUNT, params.get('amount')))} {parse(_CATEGORY, params.get('category')).lower()} "
            f"expense on {prop.name}" + (f" ({what})" if what else ""))


def _expense(context, params) -> str:
    """Does `property.expense` once approved, and says what happened. It lands in Money as an expense tagged to the property."""
    prop = _property(context, params)
    _need(context, "budget")
    context.real_estate.record_property_expense(prop.property_id, parse(_AMOUNT, params.get("amount")),
                                                parse(_CATEGORY, params.get("category")), parse(_DATE, params.get("date")),
                                                parse(_WHAT, params.get("description")))
    return f"The expense is recorded against {prop.name}."


def _describe_upkeep(context, params) -> str:
    """The sentence the approval card shows for `property.track_upkeep` (Propose); raises ActionError when it can't be done. A property already tracked is refused."""
    prop = _property(context, params)
    maintenance = _need(context, "maintenance")
    if prop.maintenance_asset_id and maintenance.get_asset(prop.maintenance_asset_id) is not None:
        raise ActionError(f"{prop.name}'s upkeep is already tracked.")
    return f"Track {prop.name}'s upkeep in Maintenance (filters, gutters, inspections)"


def _upkeep(context, params) -> str:
    """Does `property.track_upkeep` once approved, and says what happened. The property gets its own Maintenance asset, so its tasks live in
    one place.
    """
    prop = _property(context, params)
    asset = context.maintenance.add_asset(prop.name, "Property", notes="Its property in Real Estate.")
    context.real_estate.update_property(prop.property_id, maintenance_asset_id=asset.asset_id)
    return f"{prop.name}'s upkeep is tracked. Add its tasks here or in Maintenance."


def _describe_sell(context, params) -> str:
    """The sentence the approval card shows for `property.sell` (Propose); raises ActionError when it can't be done. A
    property already sold, or no price, is refused."""
    from core.region import money

    prop = _property(context, params)
    if prop.sale_date:
        raise ActionError(f"{prop.name} is already recorded as sold on {prop.sale_date}.")
    price, costs = parse(_PRICE, params.get("sale_price")), parse(_COSTS, params.get("selling_costs")) or 0.0
    when = parse(_DATE, params.get("date"))
    return (f"Record {prop.name} as sold for {money(price)}" + (f" on {when}" if when else " today")
            + (f", {money(costs)} in selling costs" if costs else "") + "; it leaves the portfolio's totals")


def _sell(context, params) -> str:
    """Does `property.sell` once approved, and says what happened: the cash left after costs and the loan, and the
    gain as an estimate."""
    from core.real_estate_manager import sale_summary
    from core.region import money

    prop = _property(context, params)
    try:
        sold = context.real_estate.record_sale(prop.property_id, parse(_PRICE, params.get("sale_price")),
                                               parse(_DATE, params.get("date")) or "",
                                               parse(_COSTS, params.get("selling_costs")) or 0.0)
    except ValueError as problem:
        raise ActionError(str(problem))
    s = sale_summary(sold)
    return (f"{sold.name} is recorded as sold: about {money(s['net_proceeds'])} after costs and the loan payoff, and "
            f"an estimated gain of {money(s['gain'])} (not a tax figure: give your preparer the closing statement).")


def _kinds() -> list[ActionType]:
    """Every Real Estate action kind: the property record kinds and the rent, expense, upkeep and sale kinds."""
    kinds = record_kinds(RECORDS["property"])
    kinds += [
        ActionType("property.rent", "Record rent", {"property_id": "", "amount": "default: its monthly rent", "date": "",
                                                    "description": ""}, _describe_rent, _rent),
        ActionType("property.expense", "Add expense", {"property_id": "", "amount": "", "category": "", "date": "",
                                                       "description": ""}, _describe_expense, _expense),
        ActionType("property.track_upkeep", "Track upkeep", {"property_id": ""}, _describe_upkeep, _upkeep),
        ActionType("property.sell", "Record the sale", {"property_id": "", "sale_price": "", "selling_costs": "",
                                                        "date": ""}, _describe_sell, _sell),
    ]
    return kinds


ESTATE_ACTIONS: dict[str, ActionType] = {k.kind: k for k in _kinds()}
ACTION_TYPES.update(ESTATE_ACTIONS)


def form_spec() -> dict:
    """The forms the Real Estate screen uses: a property's fields, rent, an expense, and its sale."""
    forms = {"property": record_form(RECORDS["property"])}
    forms["rent"] = {"noun": "rent", "id_param": "property_id", "fields": [field_dict(f) for f in (_AMOUNT, _DATE, _WHAT)]}
    forms["expense"] = {"noun": "expense", "id_param": "property_id",
                        "fields": [field_dict(f) for f in (_AMOUNT, _CATEGORY, _DATE, _WHAT)]}
    forms["sell"] = {"noun": "sale", "id_param": "property_id", "fields": [field_dict(f) for f in (_PRICE, _COSTS, _DATE)]}
    return forms
