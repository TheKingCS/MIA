/*
 * missions.js — MIA's Missions screen (muse, 2026-10-05).
 *
 * Concept material, engine data only. Active missions are the engine's
 * due items with their real actions (Propose -> visible confirmation ->
 * Approve -> Undo, DEC-0009). Completed missions are the engine's recent
 * wins. "Invent one" goes through MIA.talk(): the assistant reads the
 * same life state and proposes — nothing is invented in this file.
 * No business logic here: no totals, no date math (DEC-0004).
 */
(function () {
  "use strict";
  const $ = (id) => document.getElementById(id);
  const arr = (v) => (Array.isArray(v) ? v : []);
  let tab = "all";

  /* ---------- status line + undo ---------- */
  function say(text, undoable) {
    const status = $("status");
    status.replaceChildren();
    if (!text) return;
    status.append(document.createTextNode(text));
    if (undoable) {
      const button = document.createElement("button");
      button.className = "btn btn-ghost";
      button.textContent = "Undo";
      button.onclick = async () => {
        try { await MIA.undo(undoable.proposal_id); say("Undone."); }
        catch (e) { say(e && e.message ? e.message : "Couldn't undo that."); }
      };
      status.append(button);
    }
  }

  /* ---------- propose -> confirm -> approve ---------- */
  function confirmWith(text) {
    return new Promise((resolve) => {
      const dialog = $("confirm");
      $("confirm-text").textContent = text;
      dialog.onclose = () => resolve(dialog.returnValue === "yes");
      $("confirm-no").onclick = () => dialog.close("no");
      $("confirm-yes").onclick = () => dialog.close("yes");
      dialog.showModal();
      $("confirm-yes").focus();
    });
  }

  async function act(action) {
    try {
      const proposal = await MIA.propose(action.kind, action.params || {});
      const ok = await confirmWith(proposal.summary + "?");
      if (!ok) { await MIA.reject(proposal.proposal_id); return; }
      const done = await MIA.approve(proposal.proposal_id);
      say(done.result || "Done.", done.undoable ? done : null);
      refresh();
    } catch (e) {
      say(e && e.message ? e.message : "That didn't go through.");
    }
  }

  /* ---------- status taxonomy tag (DEC-0007) ---------- */
  function stag(status) {
    const s = document.createElement("span");
    s.className = "stag";
    s.textContent = status || "STATIC";
    return s;
  }

  /* ---------- status strip: Tracked / Needs Attention / Next Up ---------- */
  function renderStrip(state) {
    const strip = $("strip");
    strip.replaceChildren();
    const ms = state.missions_and_skills || {};
    const items = arr(state.due && state.due.items);
    const overdue = items.filter((i) => i.when === "overdue").length;
    const today = items.filter((i) => i.when === "today").length;
    const tracked = typeof ms.active_missions === "number" ? ms.active_missions : items.length;
    const cells = [
      { cls: "ok", n: tracked, t: "Tracked" },
      { cls: "bad", n: overdue, t: "Needs Attention" },
      { cls: "soon", n: today, t: "Next Up" },
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

  /* ---------- streaks ---------- */
  function renderStreaks(state) {
    const ms = state.missions_and_skills || {};
    const streaks = arr(ms.streaks);
    $("streaks-wrap").hidden = !streaks.length;
    if (!streaks.length) return;
    $("streaks-stag").textContent = ms.status || "STATIC";
    const box = $("streaks");
    box.replaceChildren();
    streaks.forEach((s) => {
      const pill = document.createElement("span");
      pill.className = "streak-pill";
      const flame = document.createElement("span");
      flame.className = "flame";
      flame.setAttribute("aria-hidden", "true");
      flame.textContent = "🔥";
      const days = document.createElement("strong");
      days.textContent = s.days + "d";
      const name = document.createElement("span");
      name.className = "sname";
      name.textContent = s.name || "";
      pill.append(flame, days, name);
      box.append(pill);
    });
  }

  /* ---------- mission rows ---------- */
  function missionRow(item) {
    const row = document.createElement("div");
    row.className = "row";
    const main = document.createElement("div");
    const title = document.createElement("div");
    title.className = "row-title";
    title.textContent = item.title || "";
    main.append(title);
    if (item.detail) {
      const sub = document.createElement("div");
      sub.className = "row-sub";
      sub.textContent = item.detail;
      main.append(sub);
    }
    const meta = document.createElement("div");
    meta.className = "row-meta";
    if (item.when) {
      const when = document.createElement("span");
      when.className = "when " + item.when;
      when.textContent = item.when === "overdue" ? "Overdue" : item.when === "today" ? "Today" : item.when;
      meta.append(when);
    }
    if (item.action && item.action.kind) {
      const button = document.createElement("button");
      button.className = "btn btn-green";
      button.textContent = item.action.label || "Do it";
      button.onclick = () => act(item.action);
      meta.append(button);
    }
    row.append(main, meta);
    return row;
  }

  function winRow(win) {
    const row = document.createElement("div");
    row.className = "row";
    const main = document.createElement("div");
    const title = document.createElement("div");
    title.className = "row-title";
    title.textContent = win.summary || "";
    main.append(title);
    const meta = document.createElement("div");
    meta.className = "row-meta";
    const kind = document.createElement("span");
    kind.className = "when";
    kind.textContent = (win.type || "win").replace(/_/g, " ");
    meta.append(kind);
    row.append(main, meta);
    return row;
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

  function renderRows(state) {
    const box = $("rows");
    box.replaceChildren();
    $("log-stag").textContent = (state.due && state.due.status) || "STATIC";
    const items = arr(state.due && state.due.items)
      .slice()
      .sort((a, b) => (a.when === "overdue" ? -1 : 1) - (b.when === "overdue" ? -1 : 1));
    const wins = arr(state.recent_wins && state.recent_wins.latest);

    if (tab === "all" || tab === "active") {
      if (items.length) items.forEach((i) => box.append(missionRow(i)));
      else if (tab === "active") {
        box.append(emptyState("Nothing active.",
          "Ask MIA to invent a mission below — or enjoy the quiet."));
      }
    }
    if (tab === "all" || tab === "done") {
      if (wins.length) {
        if (tab === "all" && items.length) {
          const sect = document.createElement("div");
          sect.className = "sect";
          const h = document.createElement("h2");
          h.textContent = "Completed";
          sect.append(h);
          box.append(sect);
        }
        wins.forEach((w) => box.append(winRow(w)));
      } else if (tab === "done") {
        box.append(emptyState("No completions yet.",
          "Finish something and MIA will notice — that's the whole point."));
      }
    }
    if (tab === "all" && !items.length && !wins.length) {
      box.append(emptyState("No missions on the board.",
        "Ask MIA to invent one below. She reads your life state and proposes from what's actually going on."));
    }
  }

  /* ---------- tabs (every tab works) ---------- */
  function wireTabs() {
    $("tabs").querySelectorAll("button").forEach((b) => {
      b.onclick = () => {
        tab = b.dataset.tab;
        $("tabs").querySelectorAll("button").forEach((x) =>
          x.setAttribute("aria-selected", x === b ? "true" : "false"));
        if (current) renderRows(current);
      };
    });
  }

  /* ---------- invent a mission: MIA herself, via talk ---------- */
  function wireInvent() {
    const form = $("invent-form");
    const input = $("invent-input");
    const thread = $("invent-thread");
    const send = $("invent-send");
    if (MIA.demo) {
      input.disabled = true;
      send.disabled = true;
      const note = document.createElement("p");
      note.className = "dim";
      note.textContent = "Inventing is off in the demo — it needs MIA running.";
      form.append(note);
      return;
    }
    form.onsubmit = async (event) => {
      event.preventDefault();
      const focus = input.value.trim();
      const prompt = "Invent a daily mission for me based on my life state" +
        (focus ? " (focus: " + focus + ")" : "") + ".";
      const bubble = document.createElement("div");
      bubble.className = "bubble";
      bubble.textContent = "Asking MIA…";
      thread.replaceChildren(bubble);
      try {
        const data = await MIA.talk(prompt);
        bubble.textContent = data.reply_text ||
          arr(data.replies).join("\n") || "MIA didn't answer.";
      } catch (e) {
        bubble.textContent = e && e.message ? e.message : "MIA didn't answer.";
      } finally {
        refresh();
      }
    };
  }

  /* ---------- boot ---------- */
  let current = null;
  async function refresh() {
    try {
      current = await MIA.state();
      renderStrip(current);
      renderStreaks(current);
      renderRows(current);
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
    wireInvent();
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
