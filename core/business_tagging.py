"""
core.business_tagging
========================

Sorting bank transactions to the owner's businesses (2026-09-28):
"auto-tagging business transactions (lawn care, rentals, homestead) to
the right business entity after bank sync."

**MIA learns from the owner's own choices.** Every expense already tagged
to a business (by hand, when entering it, or in the review list) and
every one marked personal teaches it where that merchant's charges go.
There's no separate rule list to maintain: "Shell" charges tagged to
Lawn Care three times running are Lawn Care's.

After each bank sync (`auto_tag_new()`):
- a merchant sorted the same way at least `SURE_COUNT` times, and at
  least 90% of the time, is tagged automatically and marked `auto`, so
  the review list shows it as "tagged automatically" and it can be
  changed;
- an expense for a rental property takes that property's business;
- everything else waits in the review list (Budget → Review Business
  Tags, or "which charges need a business?"), with MIA's best guess
  filled in when she has one.

Personal is a real answer: marking a charge personal teaches MIA too,
and it stops asking about it. Nothing here runs until the owner has at
least one business set up.
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Optional

PERSONAL = "personal"
SURE_COUNT = 3
_SURE_SHARE = 0.9
_REVIEW_DAYS = 120  # older unsorted charges stop being asked about
_GENERIC = {"llc", "inc", "co", "company", "corp", "services", "service", "the", "and", "of", "my", "group", "enterprises",
            "business", "holdings", "properties", "property"}


def merchant_key(text: str) -> str:
    """Pure logic. A stable name for a merchant: 'SHELL OIL 57444 BOWLING
    GRN' and 'Shell' -> 'shell', "The Home Depot #1234" -> 'home depot'."""
    words = re.findall(r"[a-z]+", text.lower().replace("'", "").replace("’", ""))
    words = [w for w in words if w not in ("the", "www", "com", "sq", "tst", "pos", "debit", "purchase", "card")]
    if not words:
        return ""
    if words[0] in ("home", "tractor", "harbor", "sams", "dollar", "family", "circle", "rural", "true", "ace", "north",
                    "northern", "o", "auto", "costco") and len(words) > 1:
        return " ".join(words[:2])
    return words[0]


def _expense_key(expense) -> str:
    return merchant_key(expense.payee or expense.description)


def learn(expenses) -> dict[str, Counter]:
    """Pure logic. merchant -> Counter(entity_id or PERSONAL), from the
    owner's own decisions (MIA's automatic ones don't teach her)."""
    history: dict[str, Counter] = defaultdict(Counter)
    for expense in expenses:
        if getattr(expense, "entity_auto", False):
            continue
        key = _expense_key(expense)
        if not key:
            continue
        if expense.entity_id:
            history[key][expense.entity_id] += 1
        elif getattr(expense, "entity_reviewed", False):
            history[key][PERSONAL] += 1
    return history


@dataclass
class Suggestion:
    entity_id: str  # a BusinessEntity's id, or PERSONAL
    reason: str  # shown to the owner
    sure: bool = False  # safe to apply without asking


def suggest(expense, history: dict[str, Counter], entities, property_entities: Optional[dict] = None) -> Optional[Suggestion]:
    """Pure logic. Where this expense most likely belongs."""
    names = {e.entity_id: e.name for e in entities}
    if expense.property_id and property_entities and property_entities.get(expense.property_id) in names:
        entity_id = property_entities[expense.property_id]
        return Suggestion(entity_id, f"it's for a property owned by {names[entity_id]}", sure=True)
    key = _expense_key(expense)
    counts = history.get(key)
    if counts:
        (best, best_count), total = counts.most_common(1)[0], sum(counts.values())
        if best == PERSONAL or best in names:
            where = "personal" if best == PERSONAL else names[best]
            reason = f"you've put {key.title()} charges under {where} {best_count} time{'s' if best_count != 1 else ''}"
            return Suggestion(best, reason, sure=best_count >= SURE_COUNT and best_count / total >= _SURE_SHARE)
    text = f"{expense.payee} {expense.description}".lower()
    for entity in entities:
        distinctive = [w for w in re.findall(r"[a-z]+", entity.name.lower()) if w not in _GENERIC and len(w) >= 4]
        if any(re.search(rf"\b{re.escape(w)}\b", text) for w in distinctive):
            return Suggestion(entity.entity_id, f"it mentions {entity.name}")
    return None


def _property_entities(context) -> dict:
    real_estate = getattr(context, "real_estate", None)
    if real_estate is None:
        return {}
    return {p.property_id: p.entity_id for p in real_estate.all_properties() if p.entity_id}


def _needs_review(expense, today: date) -> bool:
    if expense.entity_id or expense.entity_reviewed or not expense.plaid_transaction_id:
        return False
    try:
        return date.fromisoformat(expense.date) >= today - timedelta(days=_REVIEW_DAYS)
    except ValueError:
        return True


def pending_review(context, today: Optional[date] = None) -> list[tuple[object, Optional[Suggestion]]]:
    """Bank charges nobody has sorted yet, newest first, each with MIA's
    best guess. Empty until the owner has a business set up."""
    budget = getattr(context, "budget", None)
    if budget is None or not budget.all_business_entities():
        return []
    today = today or date.today()
    expenses = budget.all_expenses()
    history, entities, properties = learn(expenses), budget.all_business_entities(), _property_entities(context)
    waiting = [e for e in expenses if _needs_review(e, today)]
    waiting.sort(key=lambda e: e.date, reverse=True)
    return [(e, suggest(e, history, entities, properties)) for e in waiting]


def auto_tagged(context) -> list:
    """What MIA tagged on her own and the owner hasn't looked at since."""
    budget = getattr(context, "budget", None)
    return [e for e in budget.all_expenses() if e.entity_auto] if budget is not None else []


def apply_choice(context, entry_id: str, entity_id: str) -> None:
    """The owner's decision: a business's id, or PERSONAL / "" for personal."""
    choice = "" if entity_id in (PERSONAL, "") else entity_id
    context.budget.update_expense(entry_id, entity_id=choice, entity_reviewed=True, entity_auto=False)


@dataclass
class AutoTagResult:
    tagged: list  # (expense, entity name) MIA tagged on her own
    waiting: int  # still need the owner

    def describe(self) -> str:
        parts = []
        if self.tagged:
            by_business = Counter(name for _, name in self.tagged)
            parts.append("Tagged " + ", ".join(f"{n} to {name}" for name, n in by_business.items()) + " automatically")
        if self.waiting:
            parts.append(f"{self.waiting} charge{'s' if self.waiting != 1 else ''} need{'s' if self.waiting == 1 else ''} "
                         "a business (Budget → Review Business Tags)")
        return "; ".join(parts) + "." if parts else ""


def auto_tag_new(context, today: Optional[date] = None) -> AutoTagResult:
    """After a bank sync: apply the sure suggestions, count the rest."""
    budget = getattr(context, "budget", None)
    if budget is None or not budget.all_business_entities():
        return AutoTagResult([], 0)
    names = {e.entity_id: e.name for e in budget.all_business_entities()}
    tagged, waiting = [], 0
    for expense, suggestion in pending_review(context, today):
        if suggestion is not None and suggestion.sure:
            if suggestion.entity_id == PERSONAL:
                budget.update_expense(expense.entry_id, entity_reviewed=True, entity_auto=True)
            else:
                budget.update_expense(expense.entry_id, entity_id=suggestion.entity_id, entity_reviewed=True, entity_auto=True)
                tagged.append((expense, names[suggestion.entity_id]))
        else:
            waiting += 1
    return AutoTagResult(tagged, waiting)
