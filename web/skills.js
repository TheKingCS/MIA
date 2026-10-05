/*
 * skills.js — MIA's Skills screen (muse, 2026-10-05).
 *
 * Evidence-backed portfolios, not decorative XP bars. Every XP number
 * comes from the engine's skill_evidence events (recent_wins.latest),
 * grouped under the engine's own trend lists (skills_growing /
 * skills_declining / skills_dormant). A skill with no evidence says so
 * honestly — no invented levels, no fake locks.
 * No business logic here: no totals beyond summing the engine's own XP
 * events, no date math (DEC-0004).
 */
(function () {
  "use strict";
  const $ = (id) => document.getElementById(id);
  const arr = (v) => (Array.isArray(v) ? v : []);
  let tab = "all";
  let current = null;

  /* ---------- status line ---------- */
  function say(text) {
    const status = $("status");
    status.replaceChildren();
    if (text) status.append(document.createTextNode(text));
  }

  /* ---------- status taxonomy tag (DEC-0007) ---------- */
  function stag(status) {
    const s = document.createElement("span");
    s.className = "stag";
    s.textContent = status || "STATIC";
    return s;
  }

  /* Parse "10 XP in organization from Plan the week" -> {xp, skill, from}.
     Returns null when the summary doesn't carry XP — the row still
     renders, just without an XP number. */
  function parseEvidence(win) {
    const m = /(\d+(?:\.\d+)?)\s*XP\s+in\s+(.+?)\s+from\s+(.+)/i.exec(win.summary || "");
    if (!m) return null;
    return { xp: parseFloat(m[1]), skill: m[2].trim().toLowerCase(), from: m[3].trim() };
  }

  function collectSkills(state) {
    const ms = state.missions_and_skills || {};
    const wins = arr(state.recent_wins && state.recent_wins.latest);
    const skills = new Map(); // name -> {trend, xp, evidence[]}
    function ensure(name, trend) {
      const key = String(name).toLowerCase();
      if (!skills.has(key)) skills.set(key, { name: String(name), trend, xp: 0, evidence: [] });
      else if (trend && !skills.get(key).trend) skills.get(key).trend = trend;
      return skills.get(key);
    }
    arr(ms.skills_growing).forEach((n) => ensure(n, "growing"));
    arr(ms.skills_declining).forEach((n) => ensure(n, "declining"));
    arr(ms.skills_dormant).forEach((n) => ensure(n, "dormant"));
    wins.forEach((w) => {
      if (w.type !== "skill_evidence") return;
      const parsed = parseEvidence(w);
      const key = parsed ? parsed.skill : null;
      const entry = key ? ensure(key, null) : null;
      if (entry) {
        if (parsed) entry.xp += parsed.xp;
        entry.evidence.push({ win: w, parsed });
      }
    });
    return { skills: [...skills.values()], status: ms.status };
  }

  /* ---------- status strip ---------- */
  function renderStrip(state) {
    const strip = $("strip");
    strip.replaceChildren();
    const ms = state.missions_and_skills || {};
    const cells = [
      { cls: "ok", n: arr(ms.skills_growing).length, t: "Growing" },
      { cls: "soon", n: arr(ms.skills_declining).length, t: "Declining" },
      { cls: "", n: arr(ms.skills_dormant).length, t: "Dormant" },
    ];
    cells.forEach((c) => {
      const cell = document.createElement("div");
      cell.className = "cell " + c.cls;
      const n = document.createElement("div");
      n.className = "n";
      n.textContent = c.n;
      const t = document.createElement("div");
      t.className = "t";
      t.append(document.createTextNode(c.t), stag(ms.status));
      cell.append(n, t);
      strip.append(cell);
    });
  }

  /* ---------- tiles ---------- */
  function tile(skill) {
    const tile = document.createElement("div");
    tile.className = "tile glass";
    const head = document.createElement("div");
    head.className = "tile-head";
    const name = document.createElement("h3");
    name.className = "tile-name";
    name.textContent = skill.name;
    head.append(name);
    if (skill.trend) {
      const trend = document.createElement("span");
      trend.className = "trend " + skill.trend;
      trend.textContent = skill.trend;
      head.append(trend);
    }
    tile.append(head);
    if (skill.xp > 0) {
      const total = document.createElement("div");
      total.className = "xp-total";
      total.append(document.createTextNode(skill.xp + " XP "));
      const small = document.createElement("small");
      small.textContent = "earned";
      total.append(small);
      tile.append(total);
    }
    if (skill.evidence.length) {
      const list = document.createElement("ul");
      list.className = "evidence";
      skill.evidence.slice(0, 3).forEach(({ win, parsed }) => {
        const li = document.createElement("li");
        if (parsed) {
          const strong = document.createElement("strong");
          strong.textContent = "+" + parsed.xp + " XP";
          li.append(strong, document.createTextNode(" — " + parsed.from));
        } else {
          li.textContent = win.summary || "";
        }
        list.append(li);
      });
      tile.append(list);
    } else {
      const p = document.createElement("p");
      p.className = "no-evidence";
      p.textContent = "No evidence yet. Complete missions and MIA records it here.";
      tile.append(p);
    }
    return tile;
  }

  function renderTiles() {
    const box = $("tiles");
    box.replaceChildren();
    const { skills, status } = collectSkills(current);
    $("tree-stag").textContent = status || "STATIC";
    const shown = skills.filter((s) => tab === "all" || s.trend === tab);
    // Growing first, then by XP — the tree reads as progress, not a ledger.
    shown.sort((a, b) => {
      const order = { growing: 0, declining: 1, dormant: 2 };
      const ao = order[a.trend] != null ? order[a.trend] : 3;
      const bo = order[b.trend] != null ? order[b.trend] : 3;
      return ao - bo || b.xp - a.xp;
    });
    if (!shown.length) {
      const div = document.createElement("div");
      div.className = "empty";
      const s = document.createElement("strong");
      s.textContent = tab === "all" ? "No skills on the tree yet." : "Nothing " + tab + " right now.";
      const p = document.createElement("p");
      p.textContent = "Skills grow when missions complete — the engine records every XP event as evidence.";
      div.append(s, p);
      box.append(div);
      return;
    }
    shown.forEach((s) => box.append(tile(s)));
  }

  /* ---------- tabs (every tab works) ---------- */
  function wireTabs() {
    $("tabs").querySelectorAll("button").forEach((b) => {
      b.onclick = () => {
        tab = b.dataset.tab;
        $("tabs").querySelectorAll("button").forEach((x) =>
          x.setAttribute("aria-selected", x === b ? "true" : "false"));
        if (current) renderTiles();
      };
    });
  }

  /* ---------- boot ---------- */
  async function refresh() {
    try {
      current = await MIA.state();
      renderStrip(current);
      renderTiles();
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
    wireTabs();
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
