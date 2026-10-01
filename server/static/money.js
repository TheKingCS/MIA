// MIA phone app, Money view (Finance #4): turns /api/finance/summary
// (core/finance_summary.py) into titled sections of rows. Pure: no DOM,
// so it's tested under Node (tests/js/money_harness.js) against the
// real Python output. app.js draws the sections.

(function (root) {
    "use strict";

    // The person's currency (core/region.py), from the summary itself.
    let symbol = "$";

    function formatMoney(value, cents = false) {
        if (value === null || value === undefined) return "—";
        const abs = Math.abs(value).toLocaleString("en-US", {
            minimumFractionDigits: cents ? 2 : 0, maximumFractionDigits: cents ? 2 : 0,
        });
        return (value < 0 ? "-" : "") + symbol + abs;
    }

    function whenLabel(days, verb) {
        if (days < 0) return `${-days} day${days === -1 ? "" : "s"} overdue`;
        if (days === 0) return `${verb} today`;
        if (days === 1) return `${verb} tomorrow`;
        return `${verb} in ${days} days`;
    }

    function row(label, value, tone = "", sub = "") {
        return { label, value, tone, sub };
    }

    function moneySections(s) {
        symbol = (s && s.currency_symbol) || "$";
        if (!s || !s.available) {
            return [{ title: "Money", rows: [], note: "Budget isn't available on MIA's computer right now." }];
        }
        const sections = [];

        const m = s.month;
        sections.push({
            title: `This month (${m.label})`,
            rows: [
                row("Money in", formatMoney(m.income)),
                row("Money out", formatMoney(m.expenses)),
                row("Net", formatMoney(m.net), m.net < 0 ? "bad" : "good"),
            ],
        });

        const coming = [];
        for (const b of s.bills_due) {
            coming.push(row(b.name, formatMoney(b.amount), b.days < 0 ? "bad" : b.days <= 3 ? "warn" : "", whenLabel(b.days, "due")));
        }
        for (const p of s.income_expected) {
            coming.push(row(p.name, "+" + formatMoney(p.amount), "good", whenLabel(p.days, "expected")));
        }
        sections.push({ title: "Coming up (next 2 weeks)", rows: coming, note: coming.length ? "" : "No bills or paydays in the next two weeks." });

        if (s.budget_targets.length) {
            sections.push({
                title: "Budget targets",
                rows: s.budget_targets.map((t) => {
                    const pct = t.budget ? t.spent / t.budget : 0;
                    return row(t.category, `${formatMoney(t.spent)} of ${formatMoney(t.budget)}`, pct > 1 ? "bad" : pct >= 0.9 ? "warn" : "");
                }),
            });
        }

        const d = s.debts;
        sections.push({
            title: `Debts: ${formatMoney(d.total)}`,
            rows: d.ranked.map((debt, i) => row(
                `${i + 1}. ${debt.name}`, formatMoney(debt.balance), i === 0 ? "warn" : "",
                `${debt.apr}% APR${debt.bank_synced ? " · bank-synced" : ""}. ${debt.reason}`,
            )),
            note: d.ranked.length ? `Minimum payments: ${formatMoney(d.minimum_payments)}/month. Pay #1 first.` : "No debts tracked.",
        });

        const nw = s.net_worth;
        let nwNote = nw.total === null ? "Nothing to total yet: no bank sync or properties." : "";
        if (nw.manual_debts_not_in_net_worth > 0) {
            nwNote = (nwNote ? nwNote + " " : "") +
                `Debts you entered by hand (${formatMoney(nw.manual_debts_not_in_net_worth)}) aren't subtracted here; bank-synced ones already are.`;
        }
        sections.push({
            title: `Net worth: ${formatMoney(nw.total)}`,
            rows: nw.sources.map((src) => row(src.label, formatMoney(src.value), src.value < 0 ? "bad" : "")),
            note: nwNote,
        });

        if (s.builds.length) {
            sections.push({
                title: "Builds",
                rows: s.builds.map((b) => {
                    if (!b.budget) return row(b.name, formatMoney(b.spent) + " spent");
                    const over = b.remaining < 0;
                    return row(b.name, `${formatMoney(b.spent)} of ${formatMoney(b.budget)}`, over ? "bad" : "",
                        over ? `${formatMoney(-b.remaining)} over budget` : `${formatMoney(b.remaining)} left`);
                }),
            });
        }
        if (s.tools.length) {
            sections.push({
                title: "Tools & equipment",
                rows: s.tools.map((t) => row(t.name, formatMoney(t.total), "",
                    `${formatMoney(t.purchase)} to buy + ${formatMoney(t.upkeep)} since` +
                    (t.per_hour !== null ? ` · ${formatMoney(t.per_hour, true)}/hr` : ""))),
            });
        }
        return sections;
    }

    const api = { formatMoney, whenLabel, moneySections };
    if (typeof module !== "undefined" && module.exports) module.exports = api;
    else root.MIAMoney = api;
})(this);
