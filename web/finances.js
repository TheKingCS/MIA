/*
 * finances.js — MIA's Finances screen (muse, 2026-10-05).
 *
 * The desktop program's financial depth in the concept HUD language.
 * Every number comes from Life State's finances section
 * (core/finance_summary.py, core/budget_manager.py): month totals,
 * bills due, income expected, ranked debts, net worth, monthly plan.
 * Read-only: one-tap pay/receive actions live on the engine's due
 * items, where the action contract exists — this screen never invents
 * params for MIA.propose. Honest empty states throughout (DEC-0002).
 */
(function () {
  "use strict";
  const $ = (id) => document.getElementById(id);
  const arr = (v) => (Array.isArray(v) ? v : []);
  const money = (n) =>
    "$" + Number(n || 0).toLocaleString("en-US", { maximumFractionDigits: 0 });
  const daysWord = (d) =>
    d == null ? "" : d < 0 ? Math.abs(d) + "d overdue" : d === 0 ? "today" : "in " + d + "d";
  let current = null;

  function say(text) {
    const status = $("status");
    status.replaceChildren();
    if (text) status.append(document.createTextNode(text));
  }

  function stag(status) {
    const s = document.createElement("span");
    s.className = "stag";
    s.textContent = status || "STATIC";
    return s;
  }

  function emptyState(strong, text) {
    const div = document.createElement("div");
    div.className = "empty";
    const s = document.createElement("strong");
    s.textContent = strong;
    const p = document.createElement("p");
    p.textContent = text;
    div.append(s, p);
    return div;
  }

  function statRow(label, value, hot) {
    const row = document.createElement("div");
    row.className = "stat";
    const l = document.createElement("span");
    l.className = "stat-label";
    l.textContent = label;
    const v = document.createElement("span");
    v.className = "stat-value" + (hot ? " hot" : "");
    v.textContent = value;
    row.append(l, v);
    return row;
  }

  /* ---------- status strip ---------- */
  function renderStrip(f) {
    const strip = $("strip");
    strip.replaceChildren();
    const net = f.month ? Number(f.month.net || 0) : 0;
    const bills = arr(f.bills_due).length;
    const debt = f.debts ? Number(f.debts.total || 0) : 0;
    const cells = [
      { cls: net >= 0 ? "ok" : "bad", n: money(net), t: "Month net" },
      { cls: bills ? "soon" : "ok", n: String(bills), t: "Bills due" },
      { cls: "", n: money(debt), t: "Debt total" },
    ];
    cells.forEach((c) => {
      const cell = document.createElement("div");
      cell.className = "cell " + c.cls;
      const n = document.createElement("div");
      n.className = "n";
      n.textContent = c.n;
      const t = document.createElement("div");
      t.className = "t";
      t.append(document.createTextNode(c.t), stag(f.status));
      cell.append(n, t);
      strip.append(cell);
    });
  }

  /* ---------- month card ---------- */
  function renderMonth(f) {
    const card = $("month-card");
    card.replaceChildren();
    $("month-stag").textContent = f.status || "STATIC";
    const m = f.month;
    if (!m) {
      card.append(emptyState("No month totals yet.", "The engine posts income and expenses here."));
      return;
    }
    const head = document.createElement("div");
    head.className = "mia-line";
    head.setAttribute("aria-hidden", "true");
    const dot = document.createElement("span");
    dot.className = "mia-dot";
    const name = document.createElement("span");
    name.className = "mia-name";
    name.textContent = "MIA";
    const say2 = document.createElement("span");
    say2.style.cssText = "color: var(--text-dim); font-size: var(--text-sm);";
    say2.textContent = m.label || "";
    head.append(dot, name, say2);
    card.append(head);
    card.append(statRow("Income", money(m.income)));
    card.append(statRow("Expenses", money(m.expenses)));
    card.append(statRow("Net", money(m.net), true));
  }

  /* ---------- bills + income rows ---------- */
  function moneyRow(item, sub) {
    const row = document.createElement("div");
    row.className = "row";
    const main = document.createElement("div");
    const title = document.createElement("div");
    title.className = "row-title";
    title.textContent = item.name || "";
    main.append(title);
    if (sub) {
      const s = document.createElement("div");
      s.className = "row-sub";
      s.textContent = sub;
      main.append(s);
    }
    const meta = document.createElement("div");
    meta.className = "row-meta";
    const amt = document.createElement("span");
    amt.className = "xp";
    amt.textContent = money(item.amount);
    meta.append(amt);
    row.append(main, meta);
    return row;
  }

  function renderBills(f) {
    const box = $("bills");
    box.replaceChildren();
    $("bills-stag").textContent = f.status || "STATIC";
    const bills = arr(f.bills_due);
    if (!bills.length) {
      box.append(emptyState("No bills due.", "When a bill approaches, it lands here with its amount."));
      return;
    }
    bills.forEach((b) => box.append(moneyRow(b, daysWord(b.days))));
  }

  function renderIncome(f) {
    const box = $("income");
    box.replaceChildren();
    const inc = arr(f.income_expected);
    if (!inc.length) {
      box.append(emptyState("No income expected.", "Paydays and rent land here before they arrive."));
      return;
    }
    inc.forEach((x) => box.append(moneyRow(x, daysWord(x.days))));
  }

  /* ---------- debts ---------- */
  function renderDebts(f) {
    const box = $("debts");
    box.replaceChildren();
    $("debts-stag").textContent = f.status || "STATIC";
    const debts = f.debts || {};
    const ranked = arr(debts.ranked);
    if (debts.total) {
      const total = document.createElement("div");
      total.className = "stat";
      const l = document.createElement("span");
      l.className = "stat-label";
      l.textContent = "Total debt · minimums " + money(debts.minimum_payments) + "/mo";
      const v = document.createElement("span");
      v.className = "stat-value hot";
      v.textContent = money(debts.total);
      total.append(l, v);
      box.append(total);
    }
    if (!ranked.length) {
      box.append(emptyState("No debts ranked.", "Debts show here ordered by payoff priority."));
      return;
    }
    ranked.forEach((d) => {
      const sub = [d.apr != null ? d.apr + "% APR" : null, d.reason || null]
        .filter(Boolean)
        .join(" · ");
      box.append(moneyRow({ name: d.name, amount: d.balance }, sub || ""));
    });
  }

  /* ---------- net worth ---------- */
  function renderNetWorth(f) {
    const card = $("networth");
    card.replaceChildren();
    const nw = f.net_worth;
    if (!nw || nw.total == null) {
      card.append(emptyState("No net worth snapshot.", "The engine totals assets minus debts here."));
      return;
    }
    card.append(statRow("Net worth", money(nw.total), true));
    arr(nw.sources).forEach((s) => card.append(statRow(s.label || "Source", money(s.value))));
  }

  /* ---------- monthly plan ---------- */
  function renderPlan(f) {
    const card = $("plan");
    card.replaceChildren();
    const p = f.monthly_plan;
    if (!p) {
      card.append(emptyState("No monthly plan.", "Expected income minus bills and minimums, as one number."));
      return;
    }
    card.append(statRow("Expected income", money(p.expected_income)));
    card.append(statRow("Bills", money(p.bills)));
    card.append(statRow("Debt minimums", money(p.debt_minimums)));
    card.append(statRow("Gap", money(p.gap), true));
    if (p.note) {
      const note = document.createElement("p");
      note.style.cssText = "color: var(--text-faint); font-size: var(--text-sm); margin: 8px 0 0;";
      note.textContent = p.note;
      card.append(note);
    }
  }

  /* ---------- boot ---------- */
  async function refresh() {
    try {
      current = await MIA.state();
      const f = current.finances || {};
      if (f.available === false) {
        $("strip").replaceChildren();
        ["month-card", "networth", "plan"].forEach((id) => {
          $(id).replaceChildren();
          $(id).append(emptyState("Finances aren't connected.", "Connect the money modules and this screen fills in."));
        });
        ["bills", "income", "debts"].forEach((id) => {
          $(id).replaceChildren();
        });
        say("");
        return;
      }
      renderStrip(f);
      renderMonth(f);
      renderBills(f);
      renderIncome(f);
      renderDebts(f);
      renderNetWorth(f);
      renderPlan(f);
      say("");
    } catch (e) {
      if (e && e.status === 401) {
        try { sessionStorage.removeItem("mia.token"); } catch (x) { /* private mode */ }
        location.reload();
      } else {
        say(e && e.message ? e.message : "Couldn't reach MIA.");
      }
    }
  }

  function start() {
    $("sign-in").hidden = true;
    $("app").hidden = false;
    if (MIA.demo) say("Demo: placeholder data; actions are off.");
    refresh();
    MIA.onChange(refresh);
  }

  $("app").hidden = true;
  if (!MIA.signedIn) {
    const form = $("sign-in");
    form.hidden = false;
    form.onsubmit = async (event) => {
      event.preventDefault();
      try { await MIA.signIn($("who").value.trim(), $("password").value); say(""); start(); }
      catch (e) { say(e && e.message ? e.message : "Couldn't sign in."); }
    };
    return;
  }
  start();
})();
