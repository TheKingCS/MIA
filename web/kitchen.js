/*
 * kitchen.js — MIA's Kitchen screen (muse, 2026-10-05).
 *
 * Pantry, expiring food, grocery list, and recent meals from Life
 * State's kitchen section (core/kitchen_manager.py). The grocery list
 * shows its checked state as the engine reports it; this screen holds
 * no list-editing logic — that belongs to the engine's action
 * contract, which doesn't exist for these items yet.
 */
(function () {
  "use strict";
  const $ = (id) => document.getElementById(id);
  const arr = (v) => (Array.isArray(v) ? v : []);
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

  function row(title, sub, pill, pillCls) {
    const r = document.createElement("div");
    r.className = "row";
    const main = document.createElement("div");
    const t = document.createElement("div");
    t.className = "row-title";
    t.textContent = title;
    main.append(t);
    if (sub) {
      const s = document.createElement("div");
      s.className = "row-sub";
      s.textContent = sub;
      main.append(s);
    }
    const meta = document.createElement("div");
    meta.className = "row-meta";
    if (pill) {
      const w = document.createElement("span");
      w.className = "when " + (pillCls || "");
      w.textContent = pill;
      meta.append(w);
    }
    r.append(main, meta);
    return r;
  }

  async function refresh() {
    try {
      current = await MIA.state();
      const k = current.kitchen || {};
      $("exp-stag").textContent = k.status || "STATIC";

      const strip = $("strip");
      strip.replaceChildren();
      const exp = arr(k.expiring_soon).length;
      const groc = arr(k.grocery_list).length;
      const pantry = Number(k.pantry_items || 0);
      [
        { cls: "ok", n: String(pantry), t: "Pantry items" },
        { cls: exp ? "soon" : "ok", n: String(exp), t: "Expiring soon" },
        { cls: "", n: String(groc), t: "On the list" },
      ].forEach((c) => {
        const cell = document.createElement("div");
        cell.className = "cell " + c.cls;
        const n = document.createElement("div");
        n.className = "n";
        n.textContent = c.n;
        const t = document.createElement("div");
        t.className = "t";
        t.append(document.createTextNode(c.t), stag(k.status));
        cell.append(n, t);
        strip.append(cell);
      });

      const ex = $("expiring");
      ex.replaceChildren();
      const expiring = arr(k.expiring_soon);
      if (!expiring.length) {
        ex.append(emptyState("Nothing expiring.", "Food nearing its date lands here first."));
      } else {
        expiring.forEach((x) =>
          ex.append(row(x.name || "Item", null, x.days === 0 ? "today" : "in " + x.days + "d", x.days === 0 ? "today" : "soon")));
      }

      const gl = $("grocery");
      gl.replaceChildren();
      const grocery = arr(k.grocery_list);
      if (!grocery.length) {
        gl.append(emptyState("List is empty.", "The Friday grocery run starts here."));
      } else {
        grocery.forEach((g) =>
          gl.append(row(g.name || "Item", null, g.checked ? "got it" : "to get", g.checked ? "" : "soon")));
      }

      const ml = $("meals");
      ml.replaceChildren();
      const meals = arr(k.recent_meals);
      const recipes = Number(k.recipes || 0);
      if (!meals.length && !recipes) {
        ml.append(emptyState("No meals logged.", "Cook something and MIA remembers it here."));
      } else {
        if (recipes) ml.append(row(recipes + (recipes === 1 ? " recipe" : " recipes") + " saved", null, null));
        meals.forEach((m) => ml.append(row(m.recipe || "Meal", m.date || null, null)));
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
