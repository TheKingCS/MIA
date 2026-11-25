"""
core.utility_bills
====================

"Why was power so high this month?" (Jarvis brainstorm, round 10), answered from his own records: each energy bill
(electric, propane, natural gas, heating oil) said against the same month last year and his last three months'
average, and, when one of his energy sources has a kWh meter he logs, whether it was more use or a higher rate.

**The bills** (`KINDS`, `monthly`): his expenses whose description, payee or category say the kind ("Electric Co-op",
"propane fill", "gas bill"; never "gas" for the truck: `_NOT`), totalled by month. The month asked about is the
latest month with that bill, or the one he names.

**The meter** (`kwh_used`): an energy source's meter logged in kWh (core/energy_manager.py, a running total), its rise
over the month; with the bill, the cost a kWh. Without a meter, the answer says so: what changed can't be told apart.

Read only; every number from his records, never a guess at the weather or the rate.
"""

from __future__ import annotations

import re
from datetime import date
from typing import Optional

KINDS = {
    "electric": ("electric", r"electric|electricity|power bill|power company|co-?op|kwh|energy co"),
    "propane": ("propane", r"propane|\blp\b|lp gas"),
    "natural gas": ("natural gas", r"natural gas|gas bill|gas company|gas utility"),
    "heating oil": ("heating oil", r"heating oil|fuel oil|oil delivery"),
}
_NOT = re.compile(r"\b(?:gas station|gasoline|fuel for the|truck|car|diesel|mower|chainsaw)\b", re.I)


def kind_of(text: str) -> Optional[str]:
    """Pure logic. The energy bill a description or payee names, or None."""
    text = str(text or "")
    if _NOT.search(text):
        return None
    for kind, (_name, words) in KINDS.items():
        if re.search(words, text, re.I):
            return kind
    return None


def monthly(expenses: list, kind: str) -> dict:
    """Pure logic. {"YYYY-MM": total} of one kind's bills."""
    out: dict = {}
    for e in expenses:
        words = " ".join(str(getattr(e, a, "") or "") for a in ("description", "payee", "category", "notes"))
        if kind_of(words) != kind or not str(getattr(e, "date", "") or "")[:7]:
            continue
        month = str(e.date)[:7]
        out[month] = round(out.get(month, 0.0) + float(e.amount or 0), 2)
    return out


def _back(month: str, n: int) -> str:
    """Pure logic. "2026-11" minus n months."""
    y, m = int(month[:4]), int(month[5:7]) - n
    while m < 1:
        y, m = y - 1, m + 12
    return f"{y:04d}-{m:02d}"


def kwh_used(context, month: str) -> Optional[float]:
    """The rise of a kWh meter over the month (the first and last reading in it), or None without one."""
    energy = getattr(context, "energy", None)
    if energy is None:
        return None
    for source in energy.all_energy_sources():
        for meter in energy.energy_source_meter_names(source.source_id):
            readings = [r for r in energy.energy_source_readings(source.source_id, meter)
                        if str(r.unit or "").lower() == "kwh" and str(r.timestamp)[:7] == month]
            if len(readings) >= 2:
                readings.sort(key=lambda r: str(r.timestamp))
                rise = float(readings[-1].value) - float(readings[0].value)
                if rise > 0:
                    return rise
    return None


def _month_name(month: str) -> str:
    """Pure logic. "2026-11" -> "November 2026"."""
    return date(int(month[:4]), int(month[5:7]), 1).strftime("%B %Y")


def say(context, kind: str = "electric", month: str = "") -> str:
    """The answer (see the module's opening) for one kind of bill."""
    from core.region import money

    kind = kind if kind in KINDS else (kind_of(kind) or "electric")
    budget = getattr(context, "budget", None)
    bills = monthly(budget.all_expenses() if budget is not None else [], kind)
    if not bills:
        return (f"I don't see a {KINDS[kind][0]} bill in your expenses. Log it in Money (\"electric bill $182\") and "
                "next month I can say how it compares.")
    month = month if month in bills else max(bills)
    amount = bills[month]
    parts = [f"Your {KINDS[kind][0]} bill was {money(amount)} for {_month_name(month)}."]
    last_year = bills.get(_back(month, 12))
    if last_year:
        diff = amount - last_year
        parts.append(f"That's {money(abs(diff))} {'more' if diff > 0 else 'less'} than {_month_name(_back(month, 12))} "
                     f"({money(last_year)}).")
    prior = [bills[m] for m in (_back(month, 1), _back(month, 2), _back(month, 3)) if m in bills]
    if prior:
        avg = sum(prior) / len(prior)
        parts.append(f"Your {len(prior)}-month average before it was {money(avg)}"
                     + (f", so it ran {money(amount - avg)} over." if amount > avg else "."))
    if not last_year and not prior:
        parts.append("It's the only month I have, so there's nothing to compare yet.")
    if kind == "electric":
        used, before = kwh_used(context, month), kwh_used(context, _back(month, 1))
        if used:
            rate = amount / used
            parts.append(f"Your meter shows {used:,.0f} kWh this month, about {money(rate)} a kWh"
                         + (f", against {before:,.0f} kWh the month before." if before else "."))
        else:
            parts.append("Without a kWh meter logged, I can't tell more use from a higher rate: log the meter's "
                         "reading on the Power page at the start and end of a month.")
    return " ".join(parts)


def _tool(context, arguments: dict) -> str:
    """Tool why_bill_high: one kind's bill against last year and his recent average, and the meter. A month that
    isn't one (the model sometimes sends "YYYY-MM" itself) is the latest."""
    month = str(arguments.get("month", "") or "")[:7]
    return say(context, str(arguments.get("kind", "") or "electric"),
               month if re.fullmatch(r"\d{4}-\d{2}", month) else "")


def register_utility_bill_actions(registry) -> None:
    """Registers why_bill_high (reached by asking why a bill was high, never by logging one: that's add_expense)."""
    from core.assistant_actions import AssistantAction

    registry.register(AssistantAction(
        name="why_bill_high", domain="budget",
        description="Why an energy bill (electric, propane, natural gas, heating oil) was high: this month's against "
                    "the same month last year and his recent average, and his kWh meter if he logs one. Logging a "
                    "bill he paid is add_expense.",
        parameters={"type": "object", "properties": {
            "kind": {"type": "string", "description": "electric, propane, natural gas or heating oil"},
            "month": {"type": "string", "description": "YYYY-MM, only if he named a month"}}},
        handler=_tool, trigger_phrases=("bill so high", "bill was so high", "bill so expensive", "bill go up",
                                        "bill went up", "bill higher", "bill this high", "why was power",
                                        "why was my electric", "why was my propane", "compare my electric",
                                        "power cost so much", "electric cost so much"),
    ))
