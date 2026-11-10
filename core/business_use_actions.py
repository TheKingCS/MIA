"""
core.business_use_actions
===========================

Business use of a tool or vehicle on its asset page (2026-11-09, the
self-audit's last web gap: core/business_use.py was voice-only). The
page shows this year's worksheet in brief (business and personal use,
the business share and what it comes to, the jobs logged), and two
actions change it on the contract in core/actions.py, the same as
saying it:

- `asset.business_use_log` (Log Use): hours, or miles for a vehicle,
  business or personal, who it was for, the day.
- `asset.business_use_remove` (Remove): takes one logged job back off.

Records and arithmetic, not tax advice: the full worksheet (by voice,
"show me the mower's business use", or its printable page) keeps the
notes on anything uncertain, and the section repeats the first of them.
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from core.actions import ACTION_TYPES, ActionError, ActionType
from core.logger import get_logger

log = get_logger(__name__)

FORM = [
    {"name": "hours", "label": "Hours", "type": "number"},
    {"name": "miles", "label": "Miles (a vehicle)", "type": "number"},
    {"name": "purpose", "label": "Business or personal", "type": "choice", "options": ["business", "personal"],
     "default": "business"},
    {"name": "client", "label": "Who it was for", "type": "text"},
    {"name": "date", "label": "Day", "type": "date"},
    {"name": "note", "label": "Note", "type": "text"},
]


def _store(context):
    """The business-use log, or ActionError when it isn't on this MIA."""
    store = getattr(context, "business_use", None)
    if store is None:
        raise ActionError("Business-use tracking isn't on this MIA.")
    return store


def _asset(context, params):
    """The asset the params name, or ActionError."""
    maintenance = getattr(context, "maintenance", None)
    asset = maintenance.get_asset(str(params.get("asset_id") or "")) if maintenance is not None else None
    if asset is None:
        raise ActionError("That tool or vehicle isn't here anymore.")
    return asset


def _amount(value) -> float:
    """A positive number from a form field, or 0 (blank, words, or zero and below)."""
    try:
        n = float(value)
    except (TypeError, ValueError):
        return 0.0
    return n if n > 0 else 0.0


def _use(params) -> tuple[float, float, str]:
    """(hours, miles, purpose) from the params; ActionError without a positive amount."""
    hours, miles = _amount(params.get("hours")), _amount(params.get("miles"))
    if not hours and not miles:
        raise ActionError("How many hours was it (or miles, for a vehicle)?")
    purpose = "personal" if str(params.get("purpose") or "").lower().startswith("personal") else "business"
    return hours, miles, purpose


def _describe_log(context, params) -> str:
    """The approval sentence for asset.business_use_log."""
    _store(context)
    asset = _asset(context, params)
    hours, miles, purpose = _use(params)
    amount = f"{miles:g} miles" if miles else f"{hours:g} hours"
    client = str(params.get("client") or "").strip()
    return f"Log {amount} of {purpose} use on {asset.name}" + (f" for {client}" if client else "")


def _log(context, params) -> str:
    """Does asset.business_use_log: logs the use and says this year's total of that kind."""
    store = _store(context)
    asset = _asset(context, params)
    hours, miles, purpose = _use(params)
    day = str(params.get("date") or "").strip() or None
    if day:
        try:
            date.fromisoformat(day)
        except ValueError:
            raise ActionError("That day isn't a date.") from None
    entry = store.log_use(asset.asset_id, hours, purpose=purpose, use_date=day,
                          client=str(params.get("client") or "").strip()[:80],
                          note=str(params.get("note") or "").strip()[:200], miles=miles)
    unit = "miles" if miles else "hours"
    total = sum(e.amount(unit) for e in store.entries_for(asset.asset_id, int(entry.date[:4])) if e.purpose == purpose)
    return f"Logged it. {entry.date[:4]} so far on {asset.name}: {total:g} {purpose} {unit}."


def _entry(context, params):
    """The logged job the params name, or ActionError."""
    entry_id = str(params.get("entry_id") or "")
    found = next((e for e in _store(context)._entries if e.entry_id == entry_id), None)
    if found is None:
        raise ActionError("That logged use isn't there anymore.")
    return found


def _describe_remove(context, params) -> str:
    """The approval sentence for asset.business_use_remove."""
    e = _entry(context, params)
    return f"Take the {e.purpose} use on {e.date} off the log"


def _remove(context, params) -> str:
    """Does asset.business_use_remove."""
    e = _entry(context, params)
    _store(context).delete_entry(e.entry_id)
    return f"Took the {e.purpose} use on {e.date} off the log."


BUSINESS_USE_ACTIONS = {a.kind: a for a in (
    ActionType("asset.business_use_log", "Log Use",
               {"asset_id": "the tool or vehicle", "hours": "hours of use", "miles": "miles (a vehicle)",
                "purpose": "business or personal", "client": "who it was for", "date": "the day", "note": "a note"},
               _describe_log, _log),
    ActionType("asset.business_use_remove", "Remove", {"entry_id": "the logged use"}, _describe_remove, _remove),
)}
ACTION_TYPES.update(BUSINESS_USE_ACTIONS)


def page_section(context, asset, today: Optional[date] = None) -> Optional[dict]:
    """The asset page's business use for this year: the worksheet's figures in brief and its jobs (each with its
    Remove action), and the Log Use form; None without the log on this MIA. A tool with nothing logged still gets
    the form, with no figures."""
    store = getattr(context, "business_use", None)
    if store is None:
        return None
    from core.business_use import MILES, build_worksheet

    year = (today or date.today()).year
    out = {"year": year, "form": FORM, "logged": False, "unit": "hours", "figures": [], "jobs": [], "note": ""}
    if not store.entries_for(asset.asset_id, year):
        return out
    try:
        sheet = build_worksheet(context, asset, year)
    except Exception:
        log.exception("Couldn't build the business-use worksheet for %s.", asset.name)
        return out
    from core.region import money

    unit = "miles" if sheet.unit == MILES else "hours"
    figures = [("Business use", f"{sheet.business_hours:g} {unit}"),
               ("Total use", f"{sheet.total_hours:g} {unit} ({sheet.total_method})" if sheet.total_hours else "not known"),
               ("Business share", f"{sheet.business_pct:g}%" if sheet.business_pct is not None else "not known")]
    if sheet.business_running_costs is not None:
        figures.append(("Business share of running costs", money(sheet.business_running_costs)))
    if sheet.business_basis is not None:
        figures.append(("Business share of the cost basis", money(sheet.business_basis)))
    if sheet.standard_mileage is not None:
        figures.append(("Standard mileage", money(sheet.standard_mileage)))
    jobs = [{"id": e.entry_id, "date": e.date, "purpose": e.purpose, "amount": f"{e.amount(unit):g} {unit}",
             "for": e.client, "note": e.note,
             "remove": {"kind": "asset.business_use_remove", "params": {"entry_id": e.entry_id}}}
            for e in sorted(store.entries_for(asset.asset_id, year), key=lambda e: e.date, reverse=True)]
    out.update(logged=True, unit=unit, figures=[{"label": a, "value": b} for a, b in figures], jobs=jobs[:20],
               note=sheet.notes[0] if sheet.notes else "")
    return out
