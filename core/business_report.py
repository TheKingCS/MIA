"""
core.business_report
=======================

Pure, Qt-free composition of a household + real estate "Business
Report" HTML document — 2026-09-08, at the user's explicit request:
"I want this to be something I can do business reports with my wife
from." Same split as core/budget_nudges.py: this module never touches
BudgetManager/RealEstateManager or Qt directly, only already-fetched
plain data (dicts/lists/primitives) in, a complete HTML string out,
ready for QTextDocument.setHtml() — modules/budget/module.py is the
thin "fetch from context, call this, render via QPrinter" wrapper.

Budget Targets vs. Actual is only meaningful for a "This Month" range
(BudgetTarget.monthly_amount has no yearly-aggregation concept, per its
own docstring in core/budget_manager.py) — the caller passes
budget_targets=[] for any other range rather than this module guessing
from range_label, keeping the "when to include this section" decision
in one place (the caller, which already knows the selected range).
"""

from __future__ import annotations

from typing import Optional

_TABLE_OPEN = '<table border="1" cellspacing="0" cellpadding="4" width="100%" style="border-collapse:collapse">'


def _money(amount: float) -> str:
    return f"${amount:,.2f}"


def _category_table(title: str, totals: dict[str, float], empty_message: str) -> str:
    """One <h2> heading + a Category/Amount table sorted descending by
    amount, with a Total row — or a plain empty-state line instead of a
    silently-dropped section when there's nothing to show."""
    html = [f"<h2>{title}</h2>"]
    if not totals:
        html.append(f"<p>{empty_message}</p>")
        return "\n".join(html)

    rows = sorted(totals.items(), key=lambda item: item[1], reverse=True)
    html.append(_TABLE_OPEN)
    html.append("<tr><th>Category</th><th>Amount</th></tr>")
    for category, amount in rows:
        html.append(f'<tr><td>{category}</td><td align="right" nowrap>{_money(amount)}</td></tr>')
    total = sum(totals.values())
    html.append(f'<tr><td><b>Total</b></td><td align="right" nowrap><b>{_money(total)}</b></td></tr>')
    html.append("</table>")
    return "\n".join(html)


def _portfolio_table(properties: list[dict]) -> str:
    html = ["<h2>Real Estate Portfolio</h2>"]
    if not properties:
        html.append("<p>No properties tracked.</p>")
        return "\n".join(html)

    html.append(_TABLE_OPEN)
    html.append(
        "<tr><th>Property</th><th>Type</th><th>Current Value</th><th>Mortgage Balance</th>"
        "<th>Equity</th><th>NOI</th><th>Cap Rate</th></tr>"
    )
    total_value = total_mortgage = total_equity = total_noi = 0.0
    for prop in properties:
        cap_rate = prop["cap_rate"]
        cap_rate_text = f"{cap_rate * 100:.1f}%" if cap_rate is not None else "—"
        html.append(
            f'<tr><td>{prop["name"]}</td><td>{prop["type"]}</td>'
            f'<td align="right" nowrap>{_money(prop["current_value"])}</td>'
            f'<td align="right" nowrap>{_money(prop["mortgage_balance"])}</td>'
            f'<td align="right" nowrap>{_money(prop["equity"])}</td>'
            f'<td align="right" nowrap>{_money(prop["noi"])}</td>'
            f'<td align="right" nowrap>{cap_rate_text}</td></tr>'
        )
        total_value += prop["current_value"]
        total_mortgage += prop["mortgage_balance"]
        total_equity += prop["equity"]
        total_noi += prop["noi"]

    # Numeric cells here are deliberately NOT bold, unlike _category_table's
    # Total row — this table's 7 narrow columns leave no headroom for bold
    # glyphs' slightly wider metrics, which was empirically found (via a
    # real rendered PDF, not assumed) to push "$280,000.00" one character
    # past the column width Qt auto-sized from the (non-bold) data row,
    # wrapping it mid-number. Bolding only the row label avoids the wrap
    # without needing an explicit column-width hack.
    aggregate_cap_rate_text = f"{(total_noi / total_value) * 100:.1f}%" if total_value > 0 else "—"
    html.append(
        f'<tr><td nowrap><b>Totals</b></td><td></td>'
        f'<td align="right" nowrap>{_money(total_value)}</td>'
        f'<td align="right" nowrap>{_money(total_mortgage)}</td>'
        f'<td align="right" nowrap>{_money(total_equity)}</td>'
        f'<td align="right" nowrap>{_money(total_noi)}</td>'
        f'<td align="right" nowrap>{aggregate_cap_rate_text}</td></tr>'
    )
    html.append("</table>")
    return "\n".join(html)


def _budget_targets_table(budget_targets: list, actual_by_category: dict[str, float]) -> str:
    html = ["<h2>Budget Targets vs. Actual (This Month)</h2>"]
    if not budget_targets:
        html.append("<p>No budget targets set.</p>")
        return "\n".join(html)

    html.append(_TABLE_OPEN)
    html.append("<tr><th>Category</th><th>Planned</th><th>Actual</th></tr>")
    for target in budget_targets:
        actual = actual_by_category.get(target.category, 0.0)
        html.append(
            f'<tr><td>{target.category}</td>'
            f'<td align="right" nowrap>{_money(target.monthly_amount)}</td>'
            f'<td align="right" nowrap>{_money(actual)}</td></tr>'
        )
    html.append("</table>")
    return "\n".join(html)


def build_business_report_html(
    range_label: str,
    start_date: Optional[str],
    end_date: Optional[str],
    income_total: float,
    expenses_total: float,
    tax_income_total: float,
    tax_expenses_total: float,
    income_by_category: dict[str, float],
    expenses_by_category: dict[str, float],
    budget_targets: list,
    actual_by_category: dict[str, float],
    properties: list[dict],
    generated_at: str,
    entity_label: Optional[str] = None,
) -> str:
    """Pure logic — testable without Qt. properties is a list of plain
    dicts: {"name", "type", "current_value", "mortgage_balance",
    "equity", "noi", "cap_rate": Optional[float]}. budget_targets should
    be passed as [] for any range other than "This Month" — see module
    docstring for why that decision belongs to the caller. entity_label
    is the selected BusinessEntity's name (or "(Unassigned)"), already
    resolved by the caller — omitted entirely from the title block when
    None (no entity filter applied), same "don't render a misleading
    empty line" convention as this module's other optional sections."""
    net_cash_flow = income_total - expenses_total

    title_line = f"<p><b>Range:</b> {range_label}"
    if entity_label:
        title_line += f"<br><b>Entity:</b> {entity_label}"
    title_line += f"<br><b>Generated:</b> {generated_at}</p>"

    sections = [
        "<h1>Business Report</h1>",
        title_line,
        "<h2>Household Finance Summary</h2>",
        "<p>"
        f"Total Income: {_money(income_total)}<br>"
        f"Total Expenses: {_money(expenses_total)}<br>"
        f"Net Cash Flow: {_money(net_cash_flow)}<br>"
        f"Tax-Relevant Income: {_money(tax_income_total)}<br>"
        f"Tax-Relevant (Deductible) Expenses: {_money(tax_expenses_total)}"
        "</p>",
        _category_table("Income by Category", income_by_category, "No income recorded for this range."),
        _category_table("Expenses by Category", expenses_by_category, "No expenses recorded for this range."),
        _portfolio_table(properties),
    ]
    if budget_targets:
        sections.append(_budget_targets_table(budget_targets, actual_by_category))

    return "\n".join(sections)
