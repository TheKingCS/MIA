"""
core.web_money
================

The Money screen's data (2026-10-06, DEC-0017): everything the PC app's
Budget screen shows, assembled here so `web/` holds no logic. Served as
`/api/money`; changes go through the action kinds in core/money_actions.py.

Tabs, as on the PC: Overview (this month, the monthly plan, net worth
and its line over the last six months (core/net_worth_history.py),
spending by category), Bills, Income (sources and what came in),
Expenses (each with its business, and a filed receipt's lines:
`receipt_lines`; the bank charges waiting for a business: `_business`), Debts (payoff order and why, under avalanche / snowball /
hybrid), Budgets (monthly targets), Trends (the last six months) and
Bank (connection status only; connecting and syncing need the vault
passphrase, so they stay on the PC).

Figures come from the same functions the desktop and the phone use
(core/finance_summary.py via Life State's finances section,
BudgetManager, rank_debts), never a second
calculation. Not for a child account.
"""

from __future__ import annotations

from dataclasses import asdict
from datetime import date, timedelta
from typing import Optional

from core.logger import get_logger

log = get_logger(__name__)

TREND_MONTHS = 6
RECENT_DAYS = 90
RECENT_LIMIT = 150


REVIEW_LIMIT = 12  # charges shown to sort at once (the rest wait their turn)


def due_words(days: Optional[int]) -> str:
    """Pure logic. "today", "in 3 days", "tomorrow", "5 days late"."""
    if days is None:
        return "nothing more due"
    if days == 0:
        return "today"
    if days == 1:
        return "tomorrow"
    if days > 0:
        return f"in {days} days"
    return "1 day late" if days == -1 else f"{-days} days late"


def month_starts(today: date, count: int) -> list[date]:
    """Pure logic. The first day of this month and the `count - 1` before it, oldest first."""
    starts = [today.replace(day=1)]
    while len(starts) < count:
        starts.append((starts[-1] - timedelta(days=1)).replace(day=1))
    return list(reversed(starts))


def _values(record, item) -> dict:
    """Pure logic. A record's form values, the fields its form has, from the item."""
    data = asdict(item)
    return {f.name: data.get(f.name) for f in record.fields}


def _r(value) -> float:
    """Pure logic. A number (None as 0) rounded to cents."""
    return round(float(value or 0), 2)


def money_page(context, today: Optional[date] = None, strategy: str = "hybrid") -> dict:
    """The Money screen's data: the same finances summary Life State serves, this month's spending by category (largest first), bills, income, debts ranked by the chosen payoff strategy, and the rest of the budget's records, each with its form values and its one-tap action (Mark paid...), and net worth with its change this month and its line (`_net_worth_line`, which keeps today's point); each bill whether it's a subscription and when it was last said to be in use, each expense its business and its receipt's lines (`receipt_lines`), and `business` holds the charges waiting to be sorted (`_business`). Not available without a budget."""
    from core.budget_manager import (DEBT_PAYOFF_STRATEGIES, days_until_bill_due, days_until_income_due,
                                     days_until_promo_expires, next_bill_due_date, next_income_due_date, rank_debts)
    from core.context_assembler import _finances
    from core.money_actions import RECORDS, form_spec
    from core.subscriptions import is_subscription

    today = today or date.today()
    budget = getattr(context, "budget", None)
    # The same finances section Life State serves (it adds the monthly plan).
    page: dict = {"as_of": today.isoformat(), "summary": _finances(context, today), "forms": form_spec(),
                  "strategies": list(DEBT_PAYOFF_STRATEGIES)}
    if budget is None:
        page["available"] = False
        return page
    page["available"] = True
    month_start = today.replace(day=1).isoformat()

    by_category = budget.total_expenses_by_category(month_start, today.isoformat())
    page["spending_by_category"] = sorted(({"category": k, "amount": _r(v)} for k, v in by_category.items() if v),
                                          key=lambda c: -c["amount"])

    bills = []
    for bill in budget.all_bills():
        days = days_until_bill_due(bill, today)
        due = next_bill_due_date(bill)
        bills.append({"id": bill.bill_id, "name": bill.name, "amount": _r(bill.amount), "category": bill.category,
                      "recurrence": bill.recurrence, "next_due": due.isoformat() if due else None, "days": days,
                      "when": due_words(days), "last_paid": bill.last_paid_date, "notes": bill.notes,
                      "values": _values(RECORDS["bill"], bill),
                      "subscription": is_subscription(bill), "still_using_on": bill.still_using_on,
                      "action": {"kind": "bill.pay", "label": "Mark paid", "params": {"bill_id": bill.bill_id}}
                      if days is not None else None})
    page["bills"] = sorted(bills, key=lambda b: (b["days"] is None, b["days"] if b["days"] is not None else 0))

    sources = []
    for source in budget.all_income_sources():
        days = days_until_income_due(source, today)
        nxt = next_income_due_date(source)
        sources.append({"id": source.source_id, "name": source.name, "amount": _r(source.expected_amount),
                        "category": source.category, "recurrence": source.recurrence,
                        "next": nxt.isoformat() if nxt else None, "days": days, "when": due_words(days),
                        "last_received": source.last_received_date, "values": _values(RECORDS["income_source"], source),
                        "action": {"kind": "income.receive", "label": "Mark received",
                                   "params": {"source_id": source.source_id}} if days is not None else None})
    page["income_sources"] = sorted(sources, key=lambda s: (s["days"] is None, s["days"] or 0))

    since = (today - timedelta(days=RECENT_DAYS)).isoformat()

    def recent(entries, record_key, extra):
        rows = [e for e in entries if (e.date or "") >= since]
        rows.sort(key=lambda e: (e.date or "", e.created_at or ""), reverse=True)
        return [{"id": e.entry_id, "date": e.date, "amount": _r(e.amount), "category": e.category,
                 "description": e.description, "from_bank": bool(e.plaid_transaction_id),
                 "values": _values(RECORDS[record_key], e), **extra(e)} for e in rows[:RECENT_LIMIT]]

    page["income"] = recent(budget.all_income(), "income", lambda e: {})
    names = {b.entity_id: b.name for b in budget.all_business_entities()}
    page["expenses"] = recent(budget.all_expenses(), "expense",
                              lambda e: {"payee": e.payee, "from_bill": bool(e.bill_id),
                                         "business": names.get(e.entity_id, ""), "business_id": e.entity_id,
                                         "auto": e.entity_auto, "lines": receipt_lines(e.items)})
    page["business"] = _business(context, names, today)
    page["recent_days"] = RECENT_DAYS

    strategy = strategy if strategy in DEBT_PAYOFF_STRATEGIES else "hybrid"
    debts = []
    ranked = rank_debts(budget.all_debts(), today, strategy)
    for p in ranked:
        d = p.debt
        promo_days = days_until_promo_expires(d, today)
        debts.append({"id": d.debt_id, "rank": p.rank, "name": d.name, "type": d.debt_type, "balance": _r(d.balance),
                      "apr": _r(p.effective_apr), "standard_apr": _r(d.interest_rate),
                      "minimum": _r(d.minimum_payment), "reason": p.reason,
                      "promo": {"apr": d.promo_apr, "ends": d.promo_expires_date, "days_left": promo_days}
                      if d.promo_apr is not None and promo_days is not None and promo_days >= 0 else None,
                      "from_bank": bool(d.plaid_account_id), "last_payment": d.last_payment_date,
                      "values": _values(RECORDS["debt"], d),
                      "action": {"kind": "debt.pay", "label": "Record payment",
                                 "params": {"debt_id": d.debt_id, "amount": d.minimum_payment or None}}})
    paid_off = [{"id": d.debt_id, "name": d.name, "values": _values(RECORDS["debt"], d)}
                for d in budget.all_debts() if d.balance <= 0]
    page["debts"] = {"strategy": strategy, "ranked": debts, "paid_off": paid_off,
                     "total": _r(sum(d["balance"] for d in debts)),
                     "minimum_payments": _r(sum(d["minimum"] for d in debts))}

    actual = budget.total_expenses_by_category(month_start, None)
    page["budget_targets"] = sorted(
        ({"category": t.category, "budget": _r(t.monthly_amount), "spent": _r(actual.get(t.category, 0.0)),
          "left": _r(t.monthly_amount - actual.get(t.category, 0.0))} for t in budget.all_budget_targets()),
        key=lambda t: t["left"])

    trends = []
    starts = month_starts(today, TREND_MONTHS)
    for i, start in enumerate(starts):
        end = (starts[i + 1] - timedelta(days=1)) if i + 1 < len(starts) else today
        income = budget.total_income(start.isoformat(), end.isoformat())
        spent = budget.total_expenses(start.isoformat(), end.isoformat())
        trends.append({"month": start.strftime("%b %Y"), "income": _r(income), "expenses": _r(spent),
                       "net": _r(income - spent)})
    page["trends"] = trends

    page["bank"] = _bank(context)
    page["net_worth"] = _net_worth_line(context, page["summary"], today)
    return page


def receipt_lines(items: list) -> list[str]:
    """What a filed receipt's lines say (core/inbox_classify.receipt_items: description, amount, quantity), each as
    "Deck screws ×2 · $18.40" in the person's currency; [] for an expense without them."""
    from core.region import money

    out = []
    for item in items or []:
        qty = item.get("quantity")
        text = str(item.get("description") or "an item") + (f" ×{qty:g}" if isinstance(qty, (int, float)) and qty not in (0, 1) else "")
        amount = item.get("amount")
        out.append(text + (f" · {money(float(amount))}" if isinstance(amount, (int, float)) else ""))
    return out


def _business(context, names: dict, today: date) -> dict:
    """The business tags (core/business_tagging.py) for the Money screen: your businesses (plus Personal) to sort a
    charge to, the bank charges still waiting with MIA's guess and why, and how many MIA sorted on her own. Empty
    lists until a business is set up."""
    from core.business_tagging import PERSONAL, auto_tagged, pending_review

    if not names:
        return {"choices": [], "review": [], "auto": 0}
    review = []
    for e, guess in pending_review(context, today)[:REVIEW_LIMIT]:
        review.append({"id": e.entry_id, "date": e.date, "amount": _r(e.amount), "payee": e.payee or e.description,
                       "guess": {"id": guess.entity_id, "name": "Personal" if guess.entity_id == PERSONAL
                                 else names.get(guess.entity_id, ""), "why": guess.reason} if guess else None})
    return {"choices": [{"id": i, "name": n} for i, n in names.items()] + [{"id": PERSONAL, "name": "Personal"}],
            "review": review, "waiting": len(pending_review(context, today)), "auto": len(auto_tagged(context))}


def _net_worth_line(context, summary: dict, today: date) -> dict:
    """Net worth for the Overview's line (core/net_worth_history.py): today's total is kept (written only when it's
    new or changed), then the change this month and the last six months' points. The line is empty without the
    history store; the change is None until there's an earlier point to compare with."""
    from core import net_worth_history

    total = (summary.get("net_worth") or {}).get("total")
    history = getattr(context, "net_worth", None)
    if history is None:
        return {"total": total, "month_change": None, "line": []}
    try:
        history.note(total, today)
    except OSError:
        log.exception("Couldn't keep today's net worth point.")
    return {"total": total, **history.summary(today)}


def _bank(context) -> dict:
    """Connection facts only: never tokens, never the vault."""
    plaid = getattr(context, "plaid", None)
    if plaid is None:
        return {"status": "PLANNED", "configured": False, "unlocked": False, "banks": []}
    try:
        configured, unlocked = bool(plaid.is_configured()), bool(plaid.is_unlocked())
        banks = [{"name": i.institution_name, "connected_at": i.connected_at,
                  "transactions": i.transactions_enabled, "investments": i.investments_enabled,
                  "loans": i.liabilities_enabled} for i in plaid.connected_items()] if unlocked else []
    except Exception:
        log.exception("Couldn't read the bank connection status.")
        return {"status": "REAL", "configured": False, "unlocked": False, "banks": [], "error": True}
    return {"status": "REAL", "configured": configured, "unlocked": unlocked, "banks": banks}
