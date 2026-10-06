/*
 * money.js — the Money screen (claude, 2026-10-06, DEC-0017). Renders
 * MIA.money(); every button proposes a money action and the engine decides.
 * Only formatting here (the currency symbol comes from the engine).
 */
(function () {
  "use strict";
  const { el, act, form, say } = MIAShell;
  const $ = (id) => document.getElementById(id);
  const TABS = [["overview", "Overview"], ["bills", "Bills"], ["income", "Income"], ["expenses", "Expenses"],
    ["debts", "Debts"], ["budgets", "Budgets"], ["trends", "Trends"], ["bank", "Bank"]];
  let page = null;
  let tab = (location.hash.slice(1) && TABS.some(([t]) => t === location.hash.slice(1))) ? location.hash.slice(1) : "overview";
  let strategy = "hybrid";
  let expenseFilter = "";

  const sym = () => (page && page.summary.currency_symbol) || "$";
  const fmt = (n) => (n < 0 ? "-" : "") + sym() + Math.abs(Number(n || 0)).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  const day = (iso) => {
    if (!iso) return "";
    const d = new Date(iso + "T00:00:00");
    return d.toLocaleDateString(undefined, { month: "short", day: "numeric", year: d.getFullYear() === new Date().getFullYear() ? undefined : "numeric" });
  };
  const tone = (days) => (days == null ? "" : days < 0 ? "overdue" : days === 0 ? "today" : "");

  // ------------------------------------------------------------ changes
  async function add(key, title, extra) {
    const spec = page.forms[key];
    const values = await form(title, spec.fields, extra || {});
    if (values) act({ kind: key + ".add", params: values });
  }
  async function edit(key, row) {
    const spec = page.forms[key];
    const values = await form("Edit " + spec.noun, spec.fields, row.values);
    if (values) act({ kind: key + ".edit", params: Object.assign({ [spec.id_param]: row.id }, values) });
  }
  const del = (key, row) => act({ kind: key + ".delete", params: { [page.forms[key].id_param]: row.id } });

  function buttons(...list) { return el("div", { class: "row-buttons" }, list.filter(Boolean)); }
  const btn = (label, cls, onclick) => el("button", { type: "button", class: "btn " + cls, onclick }, label);
  const editBtn = (key, row) => btn("Edit", "btn-ghost", () => edit(key, row));
  const delBtn = (key, row) => btn("Delete", "btn-ghost danger", () => del(key, row));

  function row(title, sub, amount, cls, actions) {
    return el("div", { class: "row money-row " + (cls || "") },
      el("div", {}, el("div", { class: "row-title" }, title), sub ? el("div", { class: "row-sub" }, sub) : null),
      el("div", { class: "row-meta" }, amount != null ? el("span", { class: "money-amount" }, amount) : null, actions));
  }
  function section(title, addLabel, onAdd, children, empty) {
    return el("section", { class: "glass money-section" },
      el("div", { class: "sect" }, el("h2", {}, title), onAdd ? btn(addLabel, "btn-amber", onAdd) : null),
      children.length ? el("div", { class: "rows" }, children) : el("p", { class: "dim" }, empty));
  }

  // ------------------------------------------------------------ tabs
  function overview() {
    const s = page.summary;
    const plan = (s.monthly_plan) || null;
    const nw = s.net_worth || {};
    const kids = [
      el("section", { class: "glass money-section" },
        el("div", { class: "sect" }, el("h2", {}, s.month ? s.month.label : "This month")),
        el("div", { class: "money-figures" },
          figure("Came in", fmt(s.month.income), "ok"), figure("Went out", fmt(s.month.expenses), "bad"),
          figure("Left", fmt(s.month.net), s.month.net < 0 ? "bad" : "ok"))),
    ];
    if (plan) {
      kids.push(el("section", { class: "glass money-section" },
        el("div", { class: "sect" }, el("h2", {}, "Every month, planned")),
        el("div", { class: "money-figures" },
          figure("Expected income", fmt(plan.expected_income)), figure("Bills", fmt(plan.bills)),
          figure("Debt minimums", fmt(plan.debt_minimums)), figure("Left over", fmt(plan.gap), plan.gap < 0 ? "bad" : "ok")),
        plan.note ? el("p", { class: "dim" }, plan.note) : null));
    }
    if (nw.total != null) {
      kids.push(el("section", { class: "glass money-section" },
        el("div", { class: "sect" }, el("h2", {}, "Net worth"), el("span", { class: "money-big" }, fmt(nw.total))),
        el("div", { class: "rows" }, nw.sources.map((src) => row(src.label, null, fmt(src.value)))),
        nw.manual_debts_not_in_net_worth ? el("p", { class: "dim" },
          "Debts you entered by hand (" + fmt(nw.manual_debts_not_in_net_worth) + ") aren't counted in this total.") : null));
    }
    const cats = page.spending_by_category;
    const most = cats.length ? cats[0].amount : 0;
    kids.push(section("Spending this month by category", null, null, cats.map((c) =>
      el("div", { class: "bar-row" }, el("span", {}, c.category),
        el("div", { class: "bar" }, el("div", { class: "bar-fill", style: "width:" + Math.round(100 * c.amount / most) + "%" })),
        el("span", { class: "money-amount" }, fmt(c.amount)))), "No spending logged this month yet."));
    const soon = s.bills_due.map((b) => row(b.name, b.days < 0 ? (-b.days) + " days late" : b.days === 0 ? "due today" : "due in " + b.days + " days",
      fmt(b.amount), tone(b.days)))
      .concat(s.income_expected.map((p) => row(p.name, p.days === 0 ? "payday today" : "payday in " + p.days + " days", fmt(p.amount), "income")));
    kids.push(section("The next two weeks", null, null, soon, "Nothing due in the next two weeks."));
    return kids;
  }
  function figure(label, value, cls) {
    return el("div", { class: "figure " + (cls || "") }, el("span", { class: "figure-n" }, value), el("span", { class: "figure-t" }, label));
  }

  function bills() {
    return [section("Bills", "Add bill", () => add("bill", "Add a bill"), page.bills.map((b) => row(
      b.name, [b.when, b.next_due ? "due " + day(b.next_due) : null, b.recurrence || "one time", b.category].filter(Boolean).join(" · "),
      fmt(b.amount), tone(b.days),
      buttons(b.action ? btn(b.action.label, "btn-green", () => act(b.action)) : null, editBtn("bill", b), delBtn("bill", b)))),
    "No bills yet. Add one, or tell MIA: “my electric bill is $120 on the 15th”.")];
  }

  function income() {
    return [
      section("Where it comes from", "Add income source", () => add("income_source", "Add an income source"),
        page.income_sources.map((src) => row(src.name,
          [src.when === "nothing more due" ? "received" : "next " + src.when, src.recurrence || "one time", src.category].join(" · "),
          fmt(src.amount), "",
          buttons(src.action ? btn(src.action.label, "btn-green", () => act(src.action)) : null,
            editBtn("income_source", src), delBtn("income_source", src)))),
        "No income sources yet (a paycheck, rent you collect…)."),
      section("What came in (last " + page.recent_days + " days)", "Log income",
        () => add("income", "Log income", { date: page.as_of }),
        page.income.map((i) => row(i.description || i.category, [day(i.date), i.category, i.from_bank ? "from the bank" : null]
          .filter(Boolean).join(" · "), fmt(i.amount), "", buttons(editBtn("income", i), delBtn("income", i)))),
        "Nothing logged yet."),
    ];
  }

  function expenses() {
    const words = expenseFilter.trim().toLowerCase();
    const rows = page.expenses.filter((e) => !words ||
      [e.description, e.payee, e.category].join(" ").toLowerCase().includes(words));
    const finder = el("input", { type: "search", class: "money-find", placeholder: "Find an expense…", "aria-label": "Find an expense",
      oninput: (e) => { expenseFilter = e.target.value; draw(); } });
    finder.value = expenseFilter;
    const sec = section("Expenses (last " + page.recent_days + " days)", "Log expense",
      () => add("expense", "Log an expense", { date: page.as_of }),
      rows.map((e) => row(e.description || e.payee || e.category,
        [day(e.date), e.category, e.payee && e.description ? e.payee : null, e.from_bank ? "from the bank" : null,
          e.from_bill ? "a bill" : null].filter(Boolean).join(" · "),
        fmt(e.amount), "", buttons(editBtn("expense", e), delBtn("expense", e)))),
      words ? "Nothing matches." : "No expenses logged yet.");
    sec.insertBefore(finder, sec.children[1]);
    return [sec];
  }

  function debts() {
    const d = page.debts;
    const strategies = el("div", { class: "ptabs", role: "tablist", "aria-label": "Payoff order" },
      page.strategies.map((s) => el("button", { type: "button", role: "tab", "aria-selected": String(s === d.strategy),
        onclick: () => { strategy = s; render(); } }, s)));
    const help = { avalanche: "Highest interest first: the least interest paid overall.",
      snowball: "Smallest balance first: quick wins.",
      hybrid: "Highest interest first, but a promo rate about to end jumps the queue." }[d.strategy];
    return [
      el("section", { class: "glass money-section" },
        el("div", { class: "sect" }, el("h2", {}, "Which to pay first"), btn("Add debt", "btn-amber", () => add("debt", "Add a debt"))),
        strategies, el("p", { class: "dim" }, help),
        el("div", { class: "money-figures" }, figure("Total owed", fmt(d.total), "bad"), figure("Minimums each month", fmt(d.minimum_payments))),
        d.ranked.length ? el("div", { class: "rows" }, d.ranked.map((x) => row(
          "#" + x.rank + "  " + x.name,
          [x.reason, x.apr + "% APR", "minimum " + fmt(x.minimum), x.type, x.from_bank ? "from the bank" : null].filter(Boolean).join(" · "),
          fmt(x.balance), x.promo ? "today" : "",
          buttons(btn("Record payment", "btn-green", async () => {
            const values = await form("Payment on " + x.name, page.forms.debt_payment.fields, { amount: x.minimum || "" });
            if (values) act({ kind: "debt.pay", params: { debt_id: x.id, amount: values.amount } });
          }), editBtn("debt", x), delBtn("debt", x))))) : el("p", { class: "dim" }, "No debts. 🎉")),
      d.paid_off.length ? section("Paid off", null, null, d.paid_off.map((x) => row(x.name, "paid off", null, "", buttons(delBtn("debt", x)))), "") : "",
    ];
  }

  function budgets() {
    const t = page.budget_targets;
    return [section("Monthly budgets", "Set a budget", async () => {
      const values = await form("Set a monthly budget", page.forms.budget_target.fields, {});
      if (values) act({ kind: "budget_target.set", params: values });
    }, t.map((x) => el("div", { class: "row money-row " + (x.left < 0 ? "overdue" : "") },
      el("div", {}, el("div", { class: "row-title" }, x.category),
        el("div", { class: "bar" }, el("div", { class: "bar-fill" + (x.left < 0 ? " over" : ""), style: "width:" + Math.min(100, Math.round(100 * x.spent / (x.budget || 1))) + "%" })),
        el("div", { class: "row-sub" }, fmt(x.spent) + " of " + fmt(x.budget) + " · " + (x.left < 0 ? fmt(-x.left) + " over" : fmt(x.left) + " left"))),
      el("div", { class: "row-meta" }, buttons(
        btn("Change", "btn-ghost", async () => {
          const values = await form("Monthly " + x.category + " budget", page.forms.budget_target.fields, { category: x.category, monthly_amount: x.budget });
          if (values) act({ kind: "budget_target.set", params: values });
        }),
        btn("Remove", "btn-ghost danger", () => act({ kind: "budget_target.delete", params: { category: x.category } })))))),
    "No budgets yet. Set one for a category you want to keep an eye on.")];
  }

  function trends() {
    const most = Math.max(1, ...page.trends.map((m) => Math.max(m.income, m.expenses)));
    return [el("section", { class: "glass money-section" },
      el("div", { class: "sect" }, el("h2", {}, "The last six months")),
      el("div", { class: "trend" }, page.trends.map((m) => el("div", { class: "trend-month" },
        el("div", { class: "trend-bars" },
          el("div", { class: "trend-bar in", style: "height:" + Math.round(100 * m.income / most) + "%", title: "In " + fmt(m.income) }),
          el("div", { class: "trend-bar out", style: "height:" + Math.round(100 * m.expenses / most) + "%", title: "Out " + fmt(m.expenses) })),
        el("span", { class: "trend-label" }, m.month.split(" ")[0])))),
      el("div", { class: "trend-key" }, el("span", { class: "key in" }, "came in"), el("span", { class: "key out" }, "went out")),
      el("div", { class: "rows" }, page.trends.slice().reverse().map((m) => row(m.month, "in " + fmt(m.income) + " · out " + fmt(m.expenses),
        fmt(m.net), m.net < 0 ? "overdue" : ""))))];
  }

  function bank() {
    const b = page.bank;
    const lines = b.status === "PLANNED" || !b.configured
      ? [el("p", {}, "No bank is connected on this MIA."),
        el("p", { class: "dim" }, "Connecting a bank happens on the PC app (Money → Bank Sync), because it needs your vault passphrase.")]
      : !b.unlocked
        ? [el("p", {}, "Bank sync is set up, and locked right now."),
          el("p", { class: "dim" }, "Unlock it on the PC app with your vault passphrase to see your banks and sync.")]
        : [el("div", { class: "rows" }, b.banks.map((x) => row(x.name, ["connected " + day((x.connected_at || "").slice(0, 10)),
          x.transactions ? "transactions" : null, x.investments ? "investments" : null, x.loans ? "loans" : null].filter(Boolean).join(" · ")))),
          el("p", { class: "dim" }, "Syncing needs your vault passphrase, so it runs from the PC app for now.")];
    return [el("section", { class: "glass money-section" }, el("div", { class: "sect" }, el("h2", {}, "Bank")), ...lines)];
  }

  const VIEWS = { overview, bills, income, expenses, debts, budgets, trends, bank };

  function draw() {
    const s = page.summary;
    const late = page.bills.filter((b) => b.days != null && b.days < 0).length;
    const soon = page.bills.filter((b) => b.days != null && b.days >= 0 && b.days <= 14).length;
    $("strip").replaceChildren(
      el("div", { class: "cell " + (s.month.net < 0 ? "bad" : "ok") }, el("span", { class: "n" }, fmt(s.month.net)), el("span", { class: "t" }, "left this month")),
      el("div", { class: "cell " + (late ? "bad" : "soon") }, el("span", { class: "n" }, late || soon),
        el("span", { class: "t" }, late ? "bills late" : "bills in the next 2 weeks")),
      el("div", { class: "cell" }, el("span", { class: "n" }, fmt(page.debts.total)), el("span", { class: "t" }, "owed")));
    $("tabs").replaceChildren(...TABS.map(([id, label]) => el("button", { type: "button", role: "tab", "aria-selected": String(id === tab),
      onclick: () => { tab = id; history.replaceState(null, "", "#" + id); draw(); } }, label)));
    $("panel").replaceChildren(...VIEWS[tab]());
  }

  async function render() {
    page = await MIA.money(strategy);
    if (!page.available) { say("Money isn't set up on this MIA."); return; }
    draw();
  }

  MIAShell.start(render);
})();
