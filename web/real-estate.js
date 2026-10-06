/*
 * real-estate.js — MIA's Real Estate screen (muse, 2026-10-05).
 *
 * Portfolio depth from Life State's properties section
 * (core/real_estate_manager.py). Every value, mortgage, and equity
 * number is the engine's; the screen sums portfolio totals and shows
 * each property's equity share. No invented valuations.
 */
(function () {
  "use strict";
  const $ = (id) => document.getElementById(id);
  const arr = (v) => (Array.isArray(v) ? v : []);
  const money = (n) =>
    "$" + Number(n || 0).toLocaleString("en-US", { maximumFractionDigits: 0 });
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

  function xpbar(frac, labelLeft, labelRight) {
    const wrap = document.createElement("div");
    wrap.className = "xpbar";
    const track = document.createElement("div");
    track.className = "xpbar-track";
    const fill = document.createElement("div");
    fill.className = "xpbar-fill";
    fill.style.width = Math.max(0, Math.min(100, frac * 100)).toFixed(1) + "%";
    track.append(fill);
    const label = document.createElement("div");
    label.className = "xpbar-label";
    const a = document.createElement("span");
    a.textContent = labelLeft;
    const b = document.createElement("strong");
    b.textContent = labelRight;
    label.append(a, b);
    wrap.append(track, label);
    return wrap;
  }

  function renderStrip(items, status) {
    const strip = $("strip");
    strip.replaceChildren();
    const value = items.reduce((s, p) => s + Number(p.value || 0), 0);
    const equity = items.reduce((s, p) => s + Number(p.equity || 0), 0);
    const cells = [
      { cls: "ok", n: String(items.length), t: "Properties" },
      { cls: "", n: money(value), t: "Total value" },
      { cls: "soon", n: money(equity), t: "Total equity" },
    ];
    cells.forEach((c) => {
      const cell = document.createElement("div");
      cell.className = "cell " + c.cls;
      const n = document.createElement("div");
      n.className = "n";
      n.textContent = c.n;
      const t = document.createElement("div");
      t.className = "t";
      t.append(document.createTextNode(c.t), stag(status));
      cell.append(n, t);
      strip.append(cell);
    });
  }

  function renderTotals(items) {
    const card = $("totals");
    card.replaceChildren();
    const value = items.reduce((s, p) => s + Number(p.value || 0), 0);
    const mort = items.reduce((s, p) => s + Number(p.mortgage_balance || 0), 0);
    const equity = items.reduce((s, p) => s + Number(p.equity || 0), 0);
    card.append(statRow("Portfolio value", money(value), true));
    card.append(statRow("Mortgages", money(mort)));
    card.append(statRow("Equity", money(equity), true));
    if (value > 0) card.append(xpbar(equity / value, "Equity share", Math.round((equity / value) * 100) + "%"));
  }

  function propRow(p) {
    const row = document.createElement("div");
    row.className = "row";
    const main = document.createElement("div");
    const title = document.createElement("div");
    title.className = "row-title";
    title.textContent = p.name || "Property";
    main.append(title);
    const sub = document.createElement("div");
    sub.className = "row-sub";
    const bits = [p.type || null, p.mortgage_balance ? "Mortgage " + money(p.mortgage_balance) : "No mortgage"]
      .filter(Boolean)
      .join(" · ");
    sub.textContent = bits;
    main.append(sub);
    if (p.value) {
      const bar = xpbar(
        Number(p.equity || 0) / Number(p.value),
        "Equity " + money(p.equity),
        money(p.value)
      );
      bar.style.marginTop = "8px";
      main.append(bar);
    }
    const meta = document.createElement("div");
    meta.className = "row-meta";
    const amt = document.createElement("span");
    amt.className = "xp";
    amt.textContent = money(p.value);
    meta.append(amt);
    row.append(main, meta);
    return row;
  }

  async function refresh() {
    try {
      current = await MIA.state();
      const re = current.properties || {};
      const items = arr(re.items);
      $("pf-stag").textContent = re.status || "STATIC";
      renderStrip(items, re.status);
      if (!items.length) {
        $("totals").replaceChildren();
        $("totals").append(emptyState("No properties yet.", "Add a property in the desktop program and it appears here."));
        $("props").replaceChildren();
        say("");
        return;
      }
      renderTotals(items);
      const box = $("props");
      box.replaceChildren();
      items.forEach((p) => box.append(propRow(p)));
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
