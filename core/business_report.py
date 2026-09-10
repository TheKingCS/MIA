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

Net Worth/Investment Holdings (2026-09-09) are household-wide figures
(Plaid/Kraken snapshots and native Real Estate equity have no entity
concept in this codebase) — see build_business_report_html()'s own
docstring for why `include_net_worth_section` is a structural opt-out,
not the same None-vs-empty gating pattern schedule_e_properties/
payees_over_threshold use. build_consolidated_business_report_html()
(2026-09-09) composes one document covering every entity/household
bucket at once, for a household running multiple LLCs.

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

# Real, stable IRS 1099-NEC threshold (years running) — a local copy,
# not an import from core.budget_manager, matching this module's own
# stated design (never touches BudgetManager directly, only already-
# fetched plain data). BudgetManager.payees_over_1099_threshold()
# already filters to this same value before this module ever sees the
# data; this copy is purely for describing the number in the caveat text.
_US_1099_NEC_THRESHOLD = 600.0


def _money(amount: float) -> str:
    return f"${amount:,.2f}"


def _money_whole(amount: float) -> str:
    """Whole-dollar formatting — used only for the portfolio table's
    Current Value/Mortgage Balance/Equity columns, which are already
    manually-entered estimates (see core/real_estate_manager.py's own
    docstring on current_value) — cents there are false precision, not
    real data, and dropping them is what actually keeps those wide
    6-7-figure columns from wrapping on a real rendered page (confirmed
    visually, not assumed)."""
    return f"${amount:,.0f}"


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

    # 2026-09-09: adding the Annual Depreciation column pushed this to 8
    # columns. Neither `nowrap` alone nor a smaller font size alone was
    # enough to stop real wrapping (confirmed via real rendered PDFs at
    # each step, not assumed) — content-based auto-sizing under real
    # space pressure still squeezed columns below what their own text
    # needed. Qt's QTextDocument HTML engine also silently ignores
    # <colgroup>/<col width=...> entirely (confirmed by a real byte-for-
    # byte-identical render before/after changing those values) — the
    # `width` attribute has to go directly on each <th> in the header
    # row instead, which Qt's renderer does honor. Also switched Current
    # Value/Mortgage Balance/Equity to whole-dollar formatting — those
    # are already manually-entered estimates (see
    # core/real_estate_manager.py's own docstring on current_value), so
    # cents there were false precision, not real data.
    html.append(_TABLE_OPEN.replace("<table ", '<table style="font-size:8pt; table-layout:fixed" '))
    html.append(
        '<tr><th width="15%">Property</th><th width="11%">Type</th>'
        '<th width="13%">Current<br>Value</th><th width="13%">Mortgage<br>Balance</th>'
        '<th width="12%">Equity</th><th width="11%">NOI</th>'
        '<th width="7%">Cap Rate</th><th width="18%">Annual<br>Depreciation</th></tr>'
    )
    total_value = total_mortgage = total_equity = total_noi = total_depreciation = 0.0
    for prop in properties:
        cap_rate = prop["cap_rate"]
        cap_rate_text = f"{cap_rate * 100:.1f}%" if cap_rate is not None else "—"
        html.append(
            f'<tr><td>{prop["name"]}</td><td>{prop["type"]}</td>'
            f'<td align="right" nowrap>{_money_whole(prop["current_value"])}</td>'
            f'<td align="right" nowrap>{_money_whole(prop["mortgage_balance"])}</td>'
            f'<td align="right" nowrap>{_money_whole(prop["equity"])}</td>'
            f'<td align="right" nowrap>{_money_whole(prop["noi"])}</td>'
            f'<td align="right" nowrap>{cap_rate_text}</td>'
            f'<td align="right" nowrap>{_money(prop["annual_depreciation"])}</td></tr>'
        )
        total_value += prop["current_value"]
        total_mortgage += prop["mortgage_balance"]
        total_equity += prop["equity"]
        total_noi += prop["noi"]
        total_depreciation += prop["annual_depreciation"]

    # Numeric cells here are deliberately NOT bold, unlike _category_table's
    # Total row — this table's narrow columns leave no headroom for bold
    # glyphs' slightly wider metrics, which was empirically found (via a
    # real rendered PDF, not assumed) to push "$280,000.00" one character
    # past the column width Qt auto-sized from the (non-bold) data row,
    # wrapping it mid-number. Bolding only the row label avoids the wrap
    # without needing an explicit column-width hack. Re-verified visually
    # after adding the Annual Depreciation column (2026-09-09) — the same
    # risk class, now with one more narrow column to fit; NOI also
    # switched to whole-dollar (a display-rounding choice for this
    # summary table only — the real IncomeEntry/ExpenseEntry data behind
    # it keeps full cent precision everywhere else in the app) once real
    # rendering showed cents were the difference between wrapping and not.
    aggregate_cap_rate_text = f"{(total_noi / total_value) * 100:.1f}%" if total_value > 0 else "—"
    html.append(
        f'<tr><td nowrap><b>Totals</b></td><td></td>'
        f'<td align="right" nowrap>{_money_whole(total_value)}</td>'
        f'<td align="right" nowrap>{_money_whole(total_mortgage)}</td>'
        f'<td align="right" nowrap>{_money_whole(total_equity)}</td>'
        f'<td align="right" nowrap>{_money_whole(total_noi)}</td>'
        f'<td align="right" nowrap>{aggregate_cap_rate_text}</td>'
        f'<td align="right" nowrap>{_money(total_depreciation)}</td></tr>'
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


# 2026-09-09: Schedule E prep view — real IRS Schedule E (Supplemental
# Income and Loss, rental real estate), Part I line structure, stable
# across recent tax years. This is real per-property income/expense
# data reorganized to match that structure, for the user/their
# accountant's reference — never a computed tax liability or a
# filing-ready form, stated directly in the rendered report itself.
_SCHEDULE_E_LINE_ORDER = [
    "Advertising", "Auto and Travel", "Cleaning and Maintenance", "Commissions",
    "Insurance", "Legal and Professional Fees", "Management Fees",
    "Mortgage Interest", "Other Interest", "Repairs", "Supplies", "Taxes",
    "Utilities", "Depreciation", "Other",
]
# Deliberately conservative, same "unmapped falls to Other" precedent
# core.plaid_manager.map_plaid_category() already established — MIA's
# household categories (Groceries/Transportation/Medical/Personal Care/
# Shopping/Bank Fees/Entertainment/Travel/Other) have no real Schedule E
# correspondence and fall to "Other" rather than a guessed line.
_CATEGORY_TO_SCHEDULE_E_LINE = {
    "Insurance": "Insurance",
    "Maintenance": "Repairs",
    "Taxes": "Taxes",
    "Utilities": "Utilities",
    # Real, honest limitation: MIA doesn't track a mortgage payment's
    # principal/interest split (see Property's own mortgage_balance —
    # a flat manually-updated number, no amortization schedule), so this
    # is the FULL Mortgage/Rent category amount, which likely includes
    # non-deductible principal. The rendered report states this
    # directly rather than silently mislabeling it as validated interest.
    "Mortgage/Rent": "Mortgage Interest",
}


def category_to_schedule_e_line(category: str) -> str:
    """Pure logic — testable without Qt."""
    return _CATEGORY_TO_SCHEDULE_E_LINE.get(category, "Other")


def _schedule_e_table(properties: list[dict]) -> str:
    """properties: list of {"name", "rents_received", "expenses_by_category":
    dict[str, float], "depreciation"}. One sub-table per property — real
    Schedule E is filed per property, not as one combined form."""
    html = ["<h2>Schedule E Summary (This Year)</h2>"]
    html.append(
        "<p><i>Real income/expense data reorganized to match IRS Schedule E's "
        "line structure, for your or your accountant's reference — this is "
        "not a computed tax liability or a filing-ready form. \"Mortgage "
        "Interest\" below is the real interest-only portion for any property "
        "with loan terms entered (see the property's own Amortization "
        "fields), and the full Mortgage/Rent category amount otherwise — "
        "which may overstate the actual deductible interest for a property "
        "without loan terms entered yet.</i></p>"
    )
    if not properties:
        html.append("<p>No Rental/Investment properties tracked.</p>")
        return "\n".join(html)

    for prop in properties:
        html.append(f'<h3>{prop["name"]}</h3>')
        html.append(_TABLE_OPEN.replace("<table ", '<table style="font-size:9pt" '))
        html.append('<tr><th width="70%">Line</th><th width="30%">Amount</th></tr>')
        html.append(
            f'<tr><td>Rents Received</td>'
            f'<td align="right" nowrap>{_money(prop["rents_received"])}</td></tr>'
        )

        line_totals: dict[str, float] = {}
        for category, amount in prop["expenses_by_category"].items():
            line = category_to_schedule_e_line(category)
            line_totals[line] = line_totals.get(line, 0.0) + amount
        line_totals["Depreciation"] = line_totals.get("Depreciation", 0.0) + prop["depreciation"]

        total_expenses = 0.0
        for line in _SCHEDULE_E_LINE_ORDER:
            amount = line_totals.get(line, 0.0)
            if amount == 0.0:
                continue  # same "don't show an untouched zero row" convention as total_expenses_by_category()
            html.append(f'<tr><td>{line}</td><td align="right" nowrap>{_money(amount)}</td></tr>')
            total_expenses += amount

        html.append(
            f'<tr><td nowrap><b>Total Expenses</b></td>'
            f'<td align="right" nowrap><b>{_money(total_expenses)}</b></td></tr>'
        )
        net = prop["rents_received"] - total_expenses
        # Standard accounting convention for a loss — this document is
        # explicitly for the user's/their accountant's reference, so a
        # real negative figure should read as "($881.82)", not "$-881.82".
        net_text = f"({_money(abs(net))})" if net < 0 else _money(net)
        html.append(
            f'<tr><td nowrap><b>Net Income (Loss)</b></td>'
            f'<td align="right" nowrap><b>{net_text}</b></td></tr>'
        )
        html.append("</table>")
    return "\n".join(html)


def _investments_table(holdings: list[dict]) -> str:
    """holdings: flattened real Plaid investment holdings across every
    connected item — {"institution_name", "security_name",
    "ticker_symbol", "quantity", "value"}. Same field-naming precedent
    as modules/budget/module.py's format_holding_row(), just plural."""
    html = ["<h2>Investment Holdings</h2>"]
    if not holdings:
        html.append("<p>No investment holdings synced.</p>")
        return "\n".join(html)

    html.append(_TABLE_OPEN)
    html.append("<tr><th>Institution</th><th>Security</th><th>Ticker</th><th>Quantity</th><th>Value</th></tr>")
    total = 0.0
    for holding in sorted(holdings, key=lambda h: h.get("value") or 0.0, reverse=True):
        value = holding.get("value")
        quantity = holding.get("quantity")
        ticker = holding.get("ticker_symbol") or "—"
        quantity_text = f"{quantity:,.4g}" if quantity is not None else "—"
        value_text = _money(value) if value is not None else "—"
        html.append(
            f'<tr><td>{holding["institution_name"]}</td><td>{holding["security_name"]}</td>'
            f'<td>{ticker}</td><td align="right" nowrap>{quantity_text}</td>'
            f'<td align="right" nowrap>{value_text}</td></tr>'
        )
        total += value or 0.0
    html.append(f'<tr><td colspan="4"><b>Total</b></td><td align="right" nowrap><b>{_money(total)}</b></td></tr>')
    html.append("</table>")
    return "\n".join(html)


def _entity_comparison_table(entities: list[dict]) -> str:
    """entities: {"label", "income_total", "expenses_total",
    "property_equity_total"} per entity/household bucket — the actual
    at-a-glance value of a consolidated multi-entity report."""
    html = ["<h2>Entity Comparison</h2>"]
    if not entities:
        html.append("<p>No entities to compare.</p>")
        return "\n".join(html)

    html.append(_TABLE_OPEN)
    html.append(
        "<tr><th>Entity</th><th>Income</th><th>Expenses</th>"
        "<th>Net Cash Flow</th><th>Property Equity</th></tr>"
    )
    total_income = total_expenses = total_equity = 0.0
    for entity in entities:
        net = entity["income_total"] - entity["expenses_total"]
        html.append(
            f'<tr><td>{entity["label"]}</td>'
            f'<td align="right" nowrap>{_money(entity["income_total"])}</td>'
            f'<td align="right" nowrap>{_money(entity["expenses_total"])}</td>'
            f'<td align="right" nowrap>{_money(net)}</td>'
            f'<td align="right" nowrap>{_money_whole(entity["property_equity_total"])}</td></tr>'
        )
        total_income += entity["income_total"]
        total_expenses += entity["expenses_total"]
        total_equity += entity["property_equity_total"]
    total_net = total_income - total_expenses
    html.append(
        f'<tr><td><b>Total (All Entities)</b></td>'
        f'<td align="right" nowrap><b>{_money(total_income)}</b></td>'
        f'<td align="right" nowrap><b>{_money(total_expenses)}</b></td>'
        f'<td align="right" nowrap><b>{_money(total_net)}</b></td>'
        f'<td align="right" nowrap><b>{_money_whole(total_equity)}</b></td></tr>'
    )
    html.append("</table>")
    return "\n".join(html)


def _payees_over_threshold_table(payees: dict[str, float], threshold: float) -> str:
    """payees: real business-tagged payment totals per payee, already
    filtered to those at/over threshold by
    core.budget_manager.BudgetManager.payees_over_1099_threshold() — a
    factual comparison against the real IRS 1099-NEC threshold, never
    a computed tax liability or a "you must file" directive."""
    html = ["<h2>1099-NEC Threshold Check (This Year)</h2>"]
    html.append(
        "<p><i>Real business-tagged payments (a property or LLC set) to a "
        f"named payee that reached or exceeded the {_money_whole(threshold)} IRS "
        "1099-NEC threshold this year — a factual comparison, not tax advice. "
        "Confirm with your accountant whether a 1099-NEC is actually required "
        "(e.g. the payee's own business structure can exempt them).</i></p>"
    )
    if not payees:
        html.append(f"<p>No payee has reached the {_money_whole(threshold)} threshold this year.</p>")
        return "\n".join(html)

    html.append(_TABLE_OPEN)
    html.append("<tr><th>Payee</th><th>Total Paid</th></tr>")
    for payee, amount in sorted(payees.items(), key=lambda item: item[1], reverse=True):
        html.append(f'<tr><td>{payee}</td><td align="right" nowrap>{_money(amount)}</td></tr>')
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
    schedule_e_properties: Optional[list[dict]] = None,
    payees_over_threshold: Optional[dict[str, float]] = None,
    net_worth_by_source: Optional[dict[str, float]] = None,
    investment_holdings: Optional[list[dict]] = None,
    include_net_worth_section: bool = True,
) -> str:
    """Pure logic — testable without Qt. properties is a list of plain
    dicts: {"name", "type", "current_value", "mortgage_balance",
    "equity", "noi", "cap_rate": Optional[float], "annual_depreciation"}.
    budget_targets should
    be passed as [] for any range other than "This Month" — see module
    docstring for why that decision belongs to the caller. entity_label
    is the selected BusinessEntity's name (or "(Unassigned)"), already
    resolved by the caller — omitted entirely from the title block when
    None (no entity filter applied), same "don't render a misleading
    empty line" convention as this module's other optional sections.

    schedule_e_properties (2026-09-09) is a list of {"name",
    "rents_received", "expenses_by_category": dict[str, float],
    "depreciation"} dicts; payees_over_threshold (2026-09-09) is a
    dict[payee, amount] from BudgetManager.payees_over_1099_threshold().
    Both are annual concepts — the caller should only ever populate
    them for "This Year". Both use an explicit None-vs-real-value
    sentinel, NOT None-vs-empty-list/dict: None means "not this range,
    omit the section entirely"; an empty list/dict means "this range
    applies, but nothing to show" and still renders the section's own
    honest empty-state message (e.g. "No Rental/Investment properties
    tracked", "No payee has reached the threshold this year") — an
    empty container is a real, meaningful answer, not "not computed".

    net_worth_by_source/investment_holdings (2026-09-09) are household-
    wide figures — Plaid/Kraken snapshots and native Real Estate equity
    have no entity concept in this codebase at all, so these are never
    scoped to whichever entity filter the caller applied to the rest of
    this report. include_net_worth_section (default True) is a
    structural opt-out, NOT the same None-vs-empty gating
    schedule_e_properties/payees_over_threshold use above — it exists
    only so build_consolidated_business_report_html() can render these
    two sections exactly once at the top of a multi-entity document
    instead of once per entity sub-report."""
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
    if include_net_worth_section:
        sections.append(_category_table(
            "Net Worth by Source", net_worth_by_source or {}, "No financial snapshots imported yet.",
        ))
        sections.append(_investments_table(investment_holdings or []))
    if budget_targets:
        sections.append(_budget_targets_table(budget_targets, actual_by_category))
    if schedule_e_properties is not None:
        sections.append(_schedule_e_table(schedule_e_properties))
    if payees_over_threshold is not None:
        sections.append(_payees_over_threshold_table(payees_over_threshold, _US_1099_NEC_THRESHOLD))

    return "\n".join(sections)


def build_consolidated_business_report_html(
    range_label: str,
    start_date: Optional[str],
    end_date: Optional[str],
    generated_at: str,
    net_worth_by_source: dict[str, float],
    investment_holdings: list[dict],
    entity_comparisons: list[dict],
    entity_report_bodies: list[str],
) -> str:
    """Pure logic — testable without Qt. A single document covering
    every entity/household bucket at once — a household running
    multiple LLCs otherwise has no way to compare them side-by-side
    (the ordinary build_business_report_html() above is always scoped
    to one entity per run). entity_comparisons: {"label",
    "income_total", "expenses_total", "property_equity_total"} per
    bucket, for the top-level comparison table. entity_report_bodies:
    each a full build_business_report_html() output for one bucket
    (built with include_net_worth_section=False, since net worth has no
    entity concept and is shown here exactly once instead of once per
    bucket) — this function just concatenates them, each already
    self-identifying via its own "Entity:" title line."""
    sections = [
        "<h1>Consolidated Business Report — All Entities</h1>",
        f"<p><b>Range:</b> {range_label}<br><b>Generated:</b> {generated_at}</p>",
        _category_table("Net Worth by Source", net_worth_by_source, "No financial snapshots imported yet."),
        _investments_table(investment_holdings),
        _entity_comparison_table(entity_comparisons),
    ]
    for body in entity_report_bodies:
        sections.append('<div style="page-break-before: always;"></div>')
        sections.append(body)
    return "\n".join(sections)
