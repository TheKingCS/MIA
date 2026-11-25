"""
core.spending_pace
====================

"Am I spending more on groceries than usual?" (Jarvis brainstorm, round 11; finance from his own records): a spending
category this month so far, at the pace it's going, against his usual month, the average of the last three full
months it had spending in (the same normal core/unusual.py learns from). Asked for; the daily check that speaks up
on its own is core/unusual.spending_over.

**Which category** (`category_of`): his words read in code ("groceries" and "food" are Groceries, "gas" is
Transportation, "eating out" is Entertainment): a budget category by name or one of its plain words (`WORDS`); none
named, every category with a usual is compared and the ones furthest over pace said first.

**The pace** (`pace`): so far / (days gone / days in the month). A month a third gone with a third of the usual spent
is on pace, never "a third of usual". The first few days are said as too early to tell (`EARLY_DAYS`).

His household's spending only (a business's is its own, entity ""), money in his currency. Read only.
"""

from __future__ import annotations

import calendar
import re
from datetime import date
from typing import Optional

EARLY_DAYS = 5
MONTHS = 3
WORDS = {
    "Groceries": ("groceries", "grocery", "food", "supermarket"),
    "Utilities": ("utilities", "utility", "bills", "electric", "power", "water bill", "internet"),
    "Transportation": ("gas", "fuel", "car", "truck", "transportation", "driving"),
    "Medical": ("medical", "doctor", "pharmacy", "health"),
    "Personal Care": ("personal care", "haircut"),
    "Shopping": ("shopping", "amazon", "stuff"),
    "Entertainment": ("entertainment", "fun", "eating out", "restaurants", "movies"),
    "Travel": ("travel", "trips", "hotels"),
    "Insurance": ("insurance",),
    "Maintenance": ("maintenance", "repairs"),
    "Building Materials": ("building materials", "lumber", "materials"),
    "Tools & Equipment": ("tools", "equipment"),
}


def category_of(text: str, categories: list) -> Optional[str]:
    """Pure logic. The budget category his words name (by its own name first, then its plain words), or None."""
    said = " " + re.sub(r"[^a-z& ]", " ", str(text or "").lower()) + " "
    for name in sorted(categories, key=len, reverse=True):
        if f" {name.lower()} " in said:
            return name
    for name, words in WORDS.items():
        if name in categories and any(f" {w} " in said for w in words):
            return name
    return None


def pace(so_far: float, today: date) -> float:
    """Pure logic. What the month comes to at the rate it's going."""
    days = calendar.monthrange(today.year, today.month)[1]
    return so_far * days / max(1, today.day)


def _usual(budget, today: date) -> tuple[dict, dict]:
    """({category: usual month}, {category: this month so far}) from his household's expenses."""
    from core.unusual import _month_bounds

    months = []
    for back in range(1, MONTHS + 1):
        start, end = _month_bounds(today, back)
        months.append(budget.total_expenses_by_category(start.isoformat(), end.isoformat(), entity_id=""))
    usual = {}
    for category in {c for m in months for c in m}:
        past = [m[category] for m in months if m.get(category, 0) > 0]
        if len(past) >= 2:
            usual[category] = sum(past) / len(past)
    start, _end = _month_bounds(today, 0)
    return usual, budget.total_expenses_by_category(start.isoformat(), today.isoformat(), entity_id="")


def _line(category: str, so_far: float, usual: float, today: date) -> str:
    """Pure logic (with the person's currency): one category's line."""
    from core.region import money

    going = pace(so_far, today)
    diff = going - usual
    where = ("about on your usual" if abs(diff) <= 0.1 * usual else
             f"{money(abs(diff))} {'over' if diff > 0 else 'under'} your usual")
    return (f"{category}: {money(so_far)} so far, on pace for {money(going)} this month, {where} "
            f"({money(usual)} a month).")


def say(context, text: str = "", today: Optional[date] = None) -> str:
    """The answer for one category he named, or the ones furthest over their usual pace."""
    from core.budget_manager import EXPENSE_CATEGORIES

    today = today or date.today()
    budget = getattr(context, "budget", None)
    if budget is None:
        return "Your budget isn't on this MIA."
    if today.day <= EARLY_DAYS:
        return f"It's only day {today.day} of the month: too early to tell its pace. Ask me in a few days."
    usual, so_far = _usual(budget, today)
    named = category_of(text, list(EXPENSE_CATEGORIES))
    if named:
        if named not in usual:
            return (f"I don't have two months of {named} spending yet to know your usual; "
                    f"so far this month it's {_money(so_far.get(named, 0.0))}.")
        return _line(named, so_far.get(named, 0.0), usual[named], today)
    ranked = sorted(usual, key=lambda c: usual[c] - pace(so_far.get(c, 0.0), today))
    over = [c for c in ranked if pace(so_far.get(c, 0.0), today) > usual[c] * 1.1]
    if not usual:
        return "I need two months of your spending to know your usual. Log expenses in Money as they happen."
    if not over:
        return "Nothing is running over its usual pace this month."
    return " ".join(_line(c, so_far.get(c, 0.0), usual[c], today) for c in over[:3])


def _money(amount: float) -> str:
    """An amount in his currency."""
    from core.region import money

    return money(amount)


def _tool(context, arguments: dict) -> str:
    """Tool spending_vs_usual."""
    return say(context, str(arguments.get("category", "") or ""))


def register_spending_pace_actions(registry) -> None:
    """Registers spending_vs_usual."""
    from core.assistant_actions import AssistantAction

    registry.register(AssistantAction(
        name="spending_vs_usual", domain="budget",
        description="Whether he's spending more than usual this month: a category (groceries, gas, fun...) so far and "
                    "at its pace against his usual month, or the categories running over. What's left of a set "
                    "budget is budget_left.",
        parameters={"type": "object", "properties": {
            "category": {"type": "string", "description": "the spending he asked about, in his words; empty for all"}}},
        handler=_tool, trigger_phrases=("than usual", "more than i usually", "spending more on",
                                        "spend more on", "spending too much", "overspending", "on pace",
                                        "spending pace"),
    ))
