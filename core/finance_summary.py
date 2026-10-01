"""
core.finance_summary
=======================

Finance #4 (2026-09-28): "money on your phone". One read-only snapshot
of the owner's finances, as plain JSON-ready data, served by
server/app.py's /api/finance/summary to the phone web app and the
Android app.

**The same numbers as the desktop, never a second calculation.** Every
figure comes from the function the desktop already uses: month totals
from BudgetManager, bills and paydays from days_until_bill_due()/
days_until_income_due(), debt order from rank_debts() (hybrid, the
Debts tab's default), builds and tools from core/homestead_costs.py,
and net worth by the exact rule Home's Net Worth widget follows (each
imported snapshot's summary.total_value plus the Real Estate module's
property equity).

**One honesty detail about debts and net worth.** Bank-synced debts are
already subtracted inside their bank's snapshot (Plaid's own
assets-minus-liabilities total), but debts entered by hand are not part
of any snapshot. Rather than silently leaving them out or risk
subtracting a synced one twice, the summary reports them separately as
`manual_debts_not_in_net_worth`, and the phone labels them.

Read-only by design: nothing here changes a record. The phone still
changes money through MIA ("I paid the electric bill").
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from core.budget_manager import days_until_bill_due, days_until_income_due, rank_debts
from core.homestead_costs import all_build_costs, all_tool_costs
from core.region import currency_symbol_for

UPCOMING_DAYS = 14


def _r(value: float) -> float:
    return round(float(value), 2)


def _net_worth(context) -> dict:
    contributions: list[dict] = []
    finance = getattr(context, "finance", None)
    if finance is not None:
        for snapshot in finance.all_latest_snapshots():
            total_value = snapshot.data.get("summary", {}).get("total_value")
            if total_value is None:
                continue
            contributions.append({"label": snapshot.data.get("institution_name") or snapshot.source, "value": _r(total_value)})
    real_estate = getattr(context, "real_estate", None)
    if real_estate is not None:
        from core.real_estate_manager import equity

        properties = real_estate.all_properties()
        if properties:
            contributions.append({"label": "Property equity", "value": _r(sum(equity(p) for p in properties))})
    total = _r(sum(c["value"] for c in contributions)) if contributions else None
    return {"total": total, "sources": contributions}


def build_finance_summary(context, today: Optional[date] = None) -> dict:
    today = today or date.today()
    budget = getattr(context, "budget", None)
    summary: dict = {"generated_at": datetime.now().isoformat(timespec="seconds"), "as_of": today.isoformat(),
                     "currency_symbol": currency_symbol_for(context)}
    if budget is None:
        summary["available"] = False
        return summary
    summary["available"] = True

    month_start = today.replace(day=1).isoformat()
    income = budget.total_income(month_start, today.isoformat())
    expenses = budget.total_expenses(month_start, today.isoformat())
    summary["month"] = {
        "label": today.strftime("%B %Y"),
        "income": _r(income), "expenses": _r(expenses), "net": _r(income - expenses),
    }

    bills = []
    for bill in budget.all_bills():
        days = days_until_bill_due(bill, today)
        if days is not None and days <= UPCOMING_DAYS:
            bills.append({"name": bill.name, "amount": _r(bill.amount), "days": days})
    summary["bills_due"] = sorted(bills, key=lambda b: b["days"])

    paydays = []
    for source in budget.all_income_sources():
        days = days_until_income_due(source, today)
        if days is not None and days <= UPCOMING_DAYS:
            paydays.append({"name": source.name, "amount": _r(source.expected_amount), "days": days})
    summary["income_expected"] = sorted(paydays, key=lambda p: p["days"])

    targets = []
    actual = budget.total_expenses_by_category(month_start, None)
    for target in budget.all_budget_targets():
        spent = actual.get(target.category, 0.0)
        targets.append({"category": target.category, "budget": _r(target.monthly_amount), "spent": _r(spent)})
    summary["budget_targets"] = sorted(targets, key=lambda t: -(t["spent"] / t["budget"] if t["budget"] else 0))

    ranked = rank_debts(budget.all_debts(), today, "hybrid")
    summary["debts"] = {
        "total": _r(sum(p.debt.balance for p in ranked)),
        "minimum_payments": _r(sum(p.debt.minimum_payment for p in ranked)),
        "ranked": [
            {"name": p.debt.name, "balance": _r(p.debt.balance), "apr": _r(p.effective_apr),
             "bank_synced": bool(p.debt.plaid_account_id), "reason": p.reason}
            for p in ranked
        ],
    }

    net_worth = _net_worth(context)
    manual = [p.debt for p in ranked if not p.debt.plaid_account_id]
    net_worth["manual_debts_not_in_net_worth"] = _r(sum(d.balance for d in manual))
    summary["net_worth"] = net_worth

    summary["builds"] = [
        {"name": c.name, "spent": c.spent, "budget": c.budget, "remaining": c.remaining, "status": c.status}
        for c in all_build_costs(context)
    ] if getattr(context, "projects", None) is not None else []
    summary["tools"] = [
        {"name": c.name, "total": c.total, "purchase": c.purchase_price, "upkeep": c.upkeep, "per_hour": c.cost_per_hour}
        for c in all_tool_costs(context)[:8]
    ] if getattr(context, "maintenance", None) is not None else []
    return summary
