/*
 * garage.js — MIA's Garage screen (muse, 2026-10-05).
 *
 * Vehicles and equipment from Life State's assets section
 * (core/maintenance_manager.py, core/ownership.py). "Needs work" leads
 * with anything overdue or due soon; every asset shows its next task.
 * The engine's maintenance actions live on due items — this screen
 * displays, never invents, the action contract.
 */
(function () {
  "use strict";
  const $ = (id) => document.getElementById(id);
  const arr = (v) => (Array.isArray(v) ? v : []);
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

  function assetRow(a) {
    const row = document.createElement("div");
    row.className = "row";
    const main = document.createElement("div");
    const title = document.createElement("div");
    title.className = "row-title";
    title.textContent = a.name || "Asset";
    main.append(title);
    const bits = [];
    if (a.category) bits.push(a.category);
    if (a.next_task && a.next_task.title) {
      bits.push(a.next_task.title + (a.next_task.days != null ? " — " + daysWord(a.next_task.days) : ""));
    }
    const sub = document.createElement("div");
    sub.className = "row-sub";
    sub.textContent = bits.join(" · ");
    main.append(sub);
    const meta = document.createElement("div");
    meta.className = "row-meta";
    const od = Number(a.tasks_overdue || 0);
    const soon = Number(a.tasks_due_soon || 0);
    if (od > 0) {
      const w = document.createElement("span");
      w.className = "when overdue";
      w.textContent = od + " overdue";
      meta.append(w);
    } else if (soon > 0) {
      const w = document.createElement("span");
      w.className = "when today";
      w.textContent = soon + " due soon";
      meta.append(w);
    } else {
      const w = document.createElement("span");
      w.className = "when";
      w.textContent = "healthy";
      meta.append(w);
    }
    row.append(main, meta);
    return row;
  }

  async function refresh() {
    try {
      current = await MIA.state();
      const g = current.assets || {};
      const items = arr(g.items);
      $("work-stag").textContent = g.status || "STATIC";

      const strip = $("strip");
      strip.replaceChildren();
      const od = items.reduce((s, a) => s + Number(a.tasks_overdue || 0), 0);
      const soon = items.reduce((s, a) => s + Number(a.tasks_due_soon || 0), 0);
      [
        { cls: "ok", n: String(items.length), t: "Assets" },
        { cls: od ? "bad" : "ok", n: String(od), t: "Overdue" },
        { cls: soon ? "soon" : "ok", n: String(soon), t: "Due soon" },
      ].forEach((c) => {
        const cell = document.createElement("div");
        cell.className = "cell " + c.cls;
        const n = document.createElement("div");
        n.className = "n";
        n.textContent = c.n;
        const t = document.createElement("div");
        t.className = "t";
        t.append(document.createTextNode(c.t), stag(g.status));
        cell.append(n, t);
        strip.append(cell);
      });

      const needy = items.filter((a) => Number(a.tasks_overdue || 0) > 0 || Number(a.tasks_due_soon || 0) > 0);
      const nw = $("needs-work");
      nw.replaceChildren();
      if (!needy.length) {
        nw.append(emptyState("Nothing needs work.", "Overdue and upcoming maintenance lands here."));
      } else {
        needy.forEach((a) => nw.append(assetRow(a)));
      }

      const box = $("assets");
      box.replaceChildren();
      if (!items.length) {
        box.append(emptyState("No assets yet.", "Add vehicles and equipment in the desktop program."));
      } else {
        items.forEach((a) => box.append(assetRow(a)));
      }
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
