/*
 * workout.js — MIA's Workout screen (muse, 2026-10-05).
 *
 * Training volume from Life State's workout section
 * (core/workout_manager.py): session count, minutes, the last
 * session, and templates. The screen reports the record; logging
 * lives with the engine.
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

  async function refresh() {
    try {
      current = await MIA.state();
      const w = current.workout || {};
      $("last-stag").textContent = w.status || "STATIC";
      const days = Number(w.days || 7);

      const strip = $("strip");
      strip.replaceChildren();
      const sessions = Number(w.sessions || 0);
      [
        { cls: sessions ? "ok" : "", n: String(sessions), t: "Sessions · " + days + "d" },
        { cls: "", n: String(Number(w.minutes || 0)), t: "Minutes" },
        { cls: "", n: String(arr(w.templates).length), t: "Templates" },
      ].forEach((c) => {
        const cell = document.createElement("div");
        cell.className = "cell " + c.cls;
        const n = document.createElement("div");
        n.className = "n";
        n.textContent = c.n;
        const t = document.createElement("div");
        t.className = "t";
        t.append(document.createTextNode(c.t), stag(w.status));
        cell.append(n, t);
        strip.append(cell);
      });

      const last = $("last");
      last.replaceChildren();
      const s = w.last_session;
      if (!s) {
        last.append(emptyState("No sessions yet.", "Log a workout in the desktop program and it shows up here."));
      } else {
        const head = document.createElement("div");
        head.className = "mia-line";
        head.setAttribute("aria-hidden", "true");
        const dot = document.createElement("span");
        dot.className = "mia-dot";
        const name = document.createElement("span");
        name.className = "mia-name";
        name.textContent = "MIA";
        const sub = document.createElement("span");
        sub.style.cssText = "color: var(--text-dim); font-size: var(--text-sm);";
        sub.textContent = "last time you showed up";
        head.append(dot, name, sub);
        last.append(head);
        last.append(statRow("Template", s.template || "Session", true));
        if (s.date) last.append(statRow("Date", s.date));
        if (s.minutes != null) last.append(statRow("Minutes", String(s.minutes)));
      }

      const box = $("templates");
      box.replaceChildren();
      const templates = arr(w.templates);
      if (!templates.length) {
        box.append(emptyState("No templates.", "Workout templates live in the desktop program."));
      } else {
        templates.forEach((t) => {
          const r = document.createElement("div");
          r.className = "row";
          const main = document.createElement("div");
          const title = document.createElement("div");
          title.className = "row-title";
          title.textContent = typeof t === "string" ? t : t.name || "Template";
          main.append(title);
          r.append(main);
          box.append(r);
        });
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
