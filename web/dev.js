/*
 * dev.js: the development board (claude, 2026-11-03, DEC-0068/0070).
 * Zac: "a window that makes it all easy to view and understand the workflow
 * and what is going on, what is building, who is building it." Renders
 * MIA.dev() (core/work_dashboard.py) as the flow, Up Next to Done, each card
 * opening to its reviews and timeline. Formatting only: the stages, the next
 * step and the commands are decided in core. Changes still go through
 * `python -m tools.work`, and approving is Zac at the keyboard.
 *
 * Two homes: inside MIA (dev.html, the shared frame) and its own window
 * (dev-window.html, opened by tools/dev_window.py, keyed by #key=...).
 */
(function () {
  "use strict";
  const standalone = document.body.dataset.standalone === "1";
  const $ = (id) => document.getElementById(id);
  function el(tag, attrs, ...kids) {
    const node = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs || {})) {
      if (v === false || v == null) continue;
      if (k.startsWith("on")) node.addEventListener(k.slice(2), v);
      else node.setAttribute(k, v === true ? "" : v);
    }
    for (const kid of kids.flat()) if (kid != null && kid !== "") node.append(kid.nodeType ? kid : String(kid));
    return node;
  }
  const when = (iso) => !iso ? "" : /^\d{4}-\d{2}-\d{2}$/.test(iso)  // a date alone (a decision's): no time
    ? new Date(iso + "T12:00:00").toLocaleDateString(undefined, { month: "short", day: "numeric" })
    : new Date(iso).toLocaleString(undefined, { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" });
  const ago = (iso) => {
    const m = Math.round((Date.now() - new Date(iso)) / 60000);
    return m < 1 ? "just now" : m < 60 ? m + " min ago" : m < 1440 ? Math.round(m / 60) + " h ago" : when(iso);
  };
  const COLUMNS = [
    ["next", "Up Next", "Ready to start, or waiting on another task."],
    ["building", "Building", "An agent is working on it in its own lab copy."],
    ["review", "In Review", "Other agents are checking the change."],
    ["yours", "Your Turn", "Waiting for you: approve, or settle a disagreement."],
    ["done", "Done", "Merged into the running MIA."],
  ];
  const ACTION = { loop: "worked", review: "reviewed", resolve: "answered", lesson: "taught a lesson",
    approve: "approved", claim: "claimed", note: "noted", done: "finished", move: "moved", new: "created" };
  let open = "", query = "", data = null;
  const key = new URLSearchParams(location.hash.slice(1)).get("key") || "";

  async function load() {
    if (!standalone) return MIA.dev(query);
    const r = await fetch("api/dev" + (query ? "?q=" + encodeURIComponent(query) : ""), { headers: { "X-Dev-Key": key } });
    if (!r.ok) throw new Error("The window's key didn't match. Open it again with python -m tools.dev_window.");
    return r.json();
  }

  function card(t) {
    const kids = [el("span", { class: "id" }, t.id), el("span", { class: "t" }, t.title)];
    if (t.owner && t.stage !== "next") kids.push(el("span", { class: "who" }, t.owner));
    if (t.steps.length) kids.push(el("span", { class: "dev-steps", "aria-hidden": "true" },
      t.steps.map((s) => el("span", { class: s.done ? "done" : "", title: s.step }))));
    if (t.stage === "review" || t.stage === "yours") {
      const chips = t.reviews.slice(-4).map((r) => el("span", { class: "dev-chip " + (r.verdict === "approve" ? "ok" : "bad") },
        r.provider + (r.verdict === "approve" ? " ✓" : " ✗")));
      for (let i = t.approvals.length; i < t.needed && t.stage === "review"; i++) chips.push(el("span", { class: "dev-chip wait" }, "reviewer"));
      kids.push(el("span", {}, chips));
    }
    if (t.status === "blocked") kids.push(el("span", { class: "dev-chip bad" }, "blocked"));
    if (t.next && t.stage !== "done") kids.push(el("span", { class: "nx" }, t.next));
    return el("button", { class: "dev-card", type: "button", "aria-expanded": String(open === t.id),
      onclick: () => { open = open === t.id ? "" : t.id; render(); } }, kids);
  }

  function event(e) {
    return el("li", {}, el("span", { class: "at" }, when(e.at)),
      el("span", { class: "what" }, el("b", {}, e.who), " " + (ACTION[e.action] || e.action) + (e.task && !open ? " " + e.task : ""),
        e.detail ? el("span", {}, ": " + e.detail.slice(0, 300)) : ""));
  }

  function detail(t) {
    const parts = [el("span", { class: "id" }, t.id), el("h2", {}, t.title)];
    const bits = [t.owner && "Built by " + t.owner, t.branch && "lab: " + t.branch.replace("lab/", ""),
      t.decisions.length && "decisions: " + t.decisions.join(", ")].filter(Boolean);
    if (bits.length) parts.push(el("div", { class: "dim" }, bits.join(" · ")));
    if (t.next) parts.push(el("p", { class: "nx" }, t.next));
    if (t.command) parts.push(el("div", { class: "dim" }, "In PowerShell, in the MIA folder:"),
      el("code", { class: "dev-cmd" }, ".venv\\Scripts\\" + t.command));
    if (t.reviews.length) {
      parts.push(el("h3", {}, "Reviews (" + t.approvals.length + " of " + t.needed + " approve)"));
      parts.push(...t.reviews.map((r) => el("div", { class: "dev-review " + r.verdict },
        el("div", {}, el("b", {}, r.who), " · " + r.verdict + " · " + when(r.at)), el("div", { class: "said" }, r.said))));
    }
    parts.push(el("h3", {}, "Timeline"), t.timeline.length
      ? el("ul", { class: "dev-time" }, t.timeline.slice().reverse().map(event)) : el("p", { class: "dim" }, "Nothing recorded yet."));
    const close = el("button", { class: "dev-close", type: "button", "aria-label": "Close", onclick: () => { open = ""; render(); } }, "×");
    return el("aside", { class: "dev-detail", role: "dialog", "aria-label": t.id + " " + t.title }, close, parts);
  }

  function agent(a) {
    const u = a.usage || {};
    const state = !a.here ? "not installed" : a.signed_in === false ? "needs sign-in"
      : u.state === "cooling" ? "resting until " + new Date(u.until).toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" })
      : "ready";
    const sub = [a.tier, a.provider + (a.model ? " · " + a.model : "")];
    if (a.last) sub.push("last: " + (ACTION[a.last.action] || a.last.action) + " " + (a.last.task || "") + ", " + ago(a.last.at));
    return el("li", {}, el("span", {}, a.role), el("span", { class: a.working_on.length ? "busy" : "dim" },
      a.working_on.length ? "on " + a.working_on.join(", ") : state), el("span", { class: "sub" }, sub.join(" · ")));
  }

  // Up Next is long: the ready ones first, then a few more until asked.
  const SHORT = 6;
  let showAll = false;
  const shown = (k, list) => {
    if (k !== "next") return list;
    const sorted = list.slice().sort((a, b) => (a.status === "ready" ? 0 : 1) - (b.status === "ready" ? 0 : 1));
    return showAll ? sorted : sorted.slice(0, SHORT);
  };
  const more = (k, list) => k === "next" && list.length > SHORT
    ? el("button", { class: "dev-more", type: "button", onclick: () => { showAll = !showAll; render(); } },
      showAll ? "Show fewer" : "Show all " + list.length) : "";
  document.addEventListener("keydown", (e) => { if (e.key === "Escape" && open) { open = ""; render(); } });

  // The council chat (core/council.py): written to from its own window only, which holds the key.
  const MEMBERS = ["claude", "chatgpt", "codex", "copilot", "qwen", "coder", "mia", "all"];
  let draft = "", sending = false, chatNote = "", replyTo = null;
  async function send(text) {
    if (!text.trim() || sending) return;
    sending = true; chatNote = "";
    try {
      const r = await fetch("api/council", { method: "POST", headers: { "X-Dev-Key": key, "Content-Type": "application/json" },
        body: JSON.stringify({ text, task: open, reply_to: replyTo ? replyTo.id : "" }) });
      if (!r.ok) chatNote = (await r.json().catch(() => ({}))).error || "That didn't send.";
      else { draft = ""; replyTo = null; }
    } catch (e) { chatNote = "That didn't send."; }
    sending = false;
    refresh();
  }

  // What each of Zac's messages may spend, and has (core/council_floor.py): members' answers, never MIA's.
  function cost(m, list) {
    if (m.who !== "zac" || !m.plan || !m.plan.budget) return "";
    const used = list.filter((x) => x.turn === m.id && x.kind === "answer" && x.who !== "mia").length;
    return " · " + used + " of " + m.plan.budget + " call" + (m.plan.budget === 1 ? "" : "s") +
      (m.plan.mode !== "ask" ? " · " + m.plan.mode : "");
  }

  function message(m, byId, list) {
    const to = m.reply_to && byId[m.reply_to];
    const kind = m.kind && m.kind !== "message" && m.kind !== "answer" ? " " + m.kind : "";
    const reply = el("button", { class: "dev-reply", type: "button", "aria-label": "Reply to " + m.who,
      onclick: () => { replyTo = m; render(); const b = document.querySelector(".dev-say"); if (b) b.focus(); } }, "Reply");
    return el("li", { class: "dev-msg" + (m.who === "zac" ? " mine" : "") + (m.reply_to ? " reply" : "") + kind },
      el("div", { class: "head" }, el("b", {}, m.who), " " + when(m.at) + (m.task ? " · " + m.task : "") +
        (to ? " · to " + to.who : "") + (m.kind === "summary" ? " · summary" : "") + cost(m, list),
        m.kind === "note" ? "" : reply),
      el("div", { class: "said" }, m.text));
  }

  // The Chronicle Archive (core/saga.py): what the records hold that could become the story, waiting for Zac.
  async function decide(action, ref, id) {
    try {
      const r = await fetch("api/saga", { method: "POST", headers: { "X-Dev-Key": key, "Content-Type": "application/json" },
        body: JSON.stringify({ action, ref, id }) });
      chatNote = r.ok ? "" : (await r.json().catch(() => ({}))).error || "That didn't save.";
    } catch (e) { chatNote = "That didn't save."; }
    refresh();
  }
  const stars = (n) => "★".repeat(Math.max(0, Math.min(5, n || 0)));

  // Missions (core/work_runner.py) and what the team learned (core/dev_knowledge.py): both written to only
  // from this window, which holds its key.
  async function post(path, body) {
    try {
      const r = await fetch(path, { method: "POST", headers: { "X-Dev-Key": key, "Content-Type": "application/json" },
        body: JSON.stringify(body) });
      chatNote = r.ok ? "" : (await r.json().catch(() => ({}))).error || "That didn't save.";
    } catch (e) { chatNote = "That didn't save."; }
    refresh();
  }

  function missions(p) {
    const list = p.missions || [];
    const parts = [el("h2", {}, "Missions"), el("p", {}, "Give the council a goal, the paths it may change and a budget, and it " +
      "works the mission's tasks by itself: writing with whoever has time, getting reviews, stopping at its budget or " +
      "work/STOP. It never approves: merging stays yours. Starting one spends your usage.")];
    parts.push(list.length ? el("ul", { class: "dev-agents" }, list.map((m) => el("li", {},
      el("span", {}, m.id + " · " + m.goal),
      el("span", { class: m.status === "active" ? "busy" : "dim" }, m.status + (m.running_here ? " · running here" : "")),
      el("span", { class: "sub" }, "tasks " + m.used.tasks + "/" + m.budget.tasks + " · " + m.used.hours + "/" + m.budget.hours +
        " h · calls " + m.used.calls + "/" + m.budget.calls + " · scope " + m.scope.join(", ") +
        (m.steps.length ? " · last: " + m.steps[0].what : "")),
      p.writable ? el("span", { class: "sub" }, m.status === "active"
        ? el("button", { class: "dev-chip", type: "button", onclick: () => post("api/mission", { act: "pause", id: m.id }) }, "Pause")
        : m.status !== "done" ? el("button", { class: "dev-chip ok", type: "button", onclick: () => post("api/mission", { act: "start", id: m.id }) }, "Start") : "") : "")))
      : el("p", { class: "empty" }, "No missions yet."));
    if (p.writable) {
      const goal = el("input", { class: "dev-search", placeholder: "The goal", "aria-label": "The mission's goal" });
      const scope = el("input", { class: "dev-search", placeholder: "Paths it may change, comma-separated (tests/, core/ocr.py)",
        "aria-label": "The mission's scope" });
      parts.push(goal, scope, el("button", { class: "dev-chip", type: "button", onclick: () =>
        goal.value.trim() && post("api/mission", { act: "new", goal: goal.value.trim(), scope: scope.value }) }, "New mission (paused)"),
        el("p", { class: "dim" }, "Its tasks are the ones made with --source and its id: python -m tools.work new \"...\" --source M-0001"));
    }
    return el("section", { class: "dev-col" }, parts);
  }

  // Each member's voice (core/council_voices.py): hear it, try others, keep one.
  async function hear(member, voice, note) {
    note.textContent = "Making the sample…";
    try {
      const r = await fetch("api/voice?member=" + encodeURIComponent(member) + "&voice=" + encodeURIComponent(voice),
        { headers: { "X-Dev-Key": key } });
      if (!r.ok) { note.textContent = (await r.json().catch(() => ({}))).error || "No sample."; return; }
      const audio = new Audio(URL.createObjectURL(await r.blob()));
      note.textContent = "";
      await audio.play();
    } catch (e) { note.textContent = "Couldn't play it."; }
  }

  function voices(p) {
    const all = p.voices || [];
    const parts = [el("h2", {}, "Voices"), el("p", {}, "Who sounds like whom, on the glasses and the PC. These are " +
      "placeholders until you pick each by ear. Voices named like a provider's own are refused for it.")];
    if (!all.length) parts.push(el("p", { class: "empty" }, "Kokoro isn't installed here, so there's nothing to play."));
    parts.push(el("ul", { class: "dev-agents" }, (p.members || []).map((m) => {
      const pick = el("select", { "aria-label": m.name + "'s voice" }, all.map((v) =>
        el("option", { value: v, selected: "kokoro:" + v === m.voice ? true : null }, v)));
      const note = el("span", { class: "dim" });
      return el("li", {}, el("span", {}, m.name + " · " + m.voice.replace("kokoro:", "") + (m.chosen ? " (yours)" : "")),
        el("span", { class: "dim" }, m.provider),
        el("span", { class: "sub" }, all.length && p.writable ? [pick,
          el("button", { class: "dev-chip", type: "button", onclick: () => hear(m.id, pick.value, note) }, "Play"),
          el("button", { class: "dev-chip ok", type: "button", onclick: () => post("api/voice", { member: m.id, voice: pick.value }) }, "Use this"),
          note] : m.about));
    })));
    return el("section", { class: "dev-col" }, parts);
  }

  // A bar's width set from script: the window's policy refuses inline style attributes, not this.
  function barOf(pct) {
    const bar = el("span", { class: "dev-bar" });
    bar.style.width = pct + "%";
    return bar;
  }

  // MIA's improvement loops (core/loops.py, DEC-0094): every one, its latest number, its trend, its state.
  function loopsPanel(p) {
    const list = p.loops || [];
    if (!list.length) return "";
    const mark = { ok: "ok", below: "bad", slid: "bad", thin: "", none: "", error: "bad" };
    const spark = (vals) => {
      if (vals.length < 2) return "";
      const top = Math.max(...vals), low = Math.min(...vals), span = top - low || 1;
      return el("span", { class: "dev-spark" }, vals.map((v) => { const b = el("i", {}); b.style.height = (20 + 80 * (v - low) / span) + "%"; return b; }));
    };
    return el("section", { class: "dev-col dev-chronicles" }, el("h2", {}, "Her loops",
      el("span", { class: "n" }, list.filter((l) => l.state === "below" || l.state === "slid").length + " need work")),
      el("p", {}, "Each measures something about her, every day, against a floor and against its own usual. Below its floor " +
        "or sliding, it opens a task; it never changes her by itself. These are the PC's; your own use is measured in MIA's " +
        "daily check and stays in your folder."),
      p.writable ? el("button", { class: "dev-chip", type: "button", onclick: () => post("api/loops", {}) }, "Measure now") : "",
      el("ul", { class: "dev-agents" }, list.map((l) => el("li", {},
        el("span", {}, l.id + " · " + l.what),
        el("span", { class: "dev-chip " + (mark[l.state] || "") }, l.state === "none" ? "not yet" : l.state),
        el("span", { class: "sub" }, (l.value == null ? "" : l.value + (l.unit || "") + " · ") + (l.why || l.detail || "") +
          (l.floor != null ? " · floor " + l.floor + (l.unit || "") : "") + (l.task ? " · " + l.task : ""), spark(l.trend))))));
  }

  // Night School (core/night_school.py, DEC-0100): what she studied, how she did, what her teacher taught her.
  function nightPanel(p) {
    const n = p.night || {};
    if (!n.settings) return "";
    const card = Object.entries(n.card || {});
    const c = n.choosing || {};
    const cov = n.coverage || { counts: {} };
    const last = (n.nights || [])[0];
    return el("section", { class: "dev-col dev-chronicles" }, el("h2", {}, "Night School",
      el("span", { class: "n" }, (n.nights || []).length ? "last: " + last.at.slice(0, 10) : "not yet")),
      el("p", {}, "Every night from " + n.settings.start + " for " + n.settings.hours + " hours she studies with her teacher (" +
        n.settings.teachers.join(", then ") + "): exercises with a test that fails first, graded by code; one try at real work; " +
        "and a loop drafted for something nobody watches yet. Practice never merges. Mode: " +
        (n.settings.mode === "plan" ? "the build plan" + (n.step ? ", step " + n.step.number + " (" + n.step.title + ")" : "")
          : "her own pick") + "."),
      p.writable ? el("button", { class: "dev-chip", type: "button", onclick: () => post("api/night", {}) }, "Start a night now") : "",
      last ? el("pre", { class: "dev-night" }, last.text) : el("p", { class: "dim" }, "Her first night hasn't happened yet."),
      el("ul", { class: "dev-agents" },
        el("li", {}, el("span", {}, "Choosing what to study"),
          el("span", { class: "dev-chip " + (c.ready ? "ok" : "") }, c.nights ? c.agreed + " of " + c.nights + " nights" : "not yet"),
          el("span", { class: "sub" }, c.ready ? "The evidence supports letting her choose: set \"mode\": \"self\" in work/night_school.json."
            : "How often her own pick matched her teacher's. Ten nights and a cautious rate of 60% before she chooses.")),
        el("li", {}, el("span", {}, "Her loops' reach"),
          el("span", { class: "dev-chip" }, Math.round((cov.share || 0) * 100) + "%"),
          el("span", { class: "sub" }, (cov.counts.covered || 0) + " of " + cov.total + " processes watched · " +
            (cov.counts.todo || 0) + " to do · " + (cov.counts.proposed || 0) + " proposed" +
            ((cov.next || []).length ? " · next: " + cov.next.slice(0, 4).join(", ") : ""))),
        card.map(([skill, r]) => el("li", {}, el("span", {}, skill),
          el("span", { class: "dev-chip" }, r.passed + "/" + r.lessons),
          el("span", { class: "sub" }, "lessons passed · cautious rate " + Math.round(r.bound * 100) + "%")))));
  }

  function architecture(p) {
    const a = p.architecture || {};
    if (!a.layers) return "";
    const most = Math.max(1, ...a.layers.map((l) => l.lines));
    const grown = Math.max(1, ...(a.growth.areas || []).map((x) => x[1]));
    const bars = (rows, top) => el("ul", { class: "dev-agents" }, rows.map(([label, n, sub]) => el("li", {},
      el("span", {}, label), el("span", { class: "dim" }, sub),
      el("span", { class: "sub" }, barOf(Math.max(2, Math.round(100 * n / top)))))));
    const breaks = a.layering || [];
    return el("section", { class: "dev-col dev-chronicles" }, el("h2", {}, "MIA's architecture",
      el("span", { class: "n" }, a.layers.reduce((n, l) => n + l.lines, 0).toLocaleString() + " lines")),
      el("p", {}, "Read from the code itself, nothing run: her layers, what the rest depends on most, whether the layering " +
        "rule holds, and how she's grown."),
      el("div", { class: "dev-grid2" },
        el("div", {}, el("h2", { class: "gap" }, "Layers"),
          bars(a.layers.map((l) => [l.layer, l.lines, l.files + " files · " + l.lines.toLocaleString() + " lines"]), most)),
        el("div", {}, el("h2", { class: "gap" }, "Growing, by area"),
          bars((a.growth.areas || []).map(([area, n]) => [area, n, n + " task" + (n === 1 ? "" : "s") + " done"]), grown),
          el("h2", { class: "gap" }, "What most of her depends on"),
          el("ul", { class: "dev-agents" }, (a.depended_on || []).slice(0, 6).map(([m, n]) =>
            el("li", {}, el("span", {}, m), el("span", { class: "dim" }, n + " files")))))),
      el("h2", { class: "gap" }, breaks.length ? "Where the layering rule is broken" : "The layering rule holds"),
      breaks.length ? el("ul", { class: "dev-agents" }, breaks.map((b) => el("li", {}, el("span", {}, b.file + ":" + b.line),
        el("span", { class: "dim" }, b.imports), el("span", { class: "sub" }, b.rule))))
        : el("p", { class: "dim" }, "core/ reaches neither gui/ nor modules/, and no module reaches another (" +
          (a.sanctioned || []).length + " files cross it by design: boot and module discovery)."),
      (a.docs || []).length ? el("p", { class: "dev-note" }, "The docs name files that aren't there: " +
        a.docs.map((d) => d.names + " (" + d.doc + ")").join(", ")) : "");
  }

  function independence(p) {
    const k = p.independence || { stages: [], rows: [] };
    const pct = (v) => v == null ? "—" : Math.round(v * 100) + "%";
    const parts = [el("h2", {}, "Independence"), el("p", {}, "What each member, MIA's own coder (ollama-coder) first, has " +
      "shown it can do, from the history: merges, reverts, MIA's shadow attempts, and whether reviewers' objections held. " +
      "The bound is the cautious rate: a few tries mean little. A stage past Apprentice waits for you, and grants no permission.")];
    parts.push(el("ul", { class: "dev-agents" }, k.rows.map((r) => el("li", {},
      el("span", {}, r.provider + " · " + r.skill),
      el("span", { class: r.shown >= 3 ? "busy" : "dim" }, k.stages[r.shown] + (r.proposed ? " (evidence says " + k.stages[r.stage] + ")" : "")),
      el("span", { class: "sub" }, r.passed + " of " + r.attempts + " · rate " + pct(r.rate) + " · bound " + pct(r.bound) +
        (r.recent.length ? " · " + r.recent.join(", ") : ""),
        r.proposed && p.writable ? el("button", { class: "dev-chip ok", type: "button", onclick: () =>
          post("api/ledger", { provider: r.provider, skill: r.skill, stage: r.stage }) }, "Confirm " + k.stages[r.stage]) : "")))));
    return el("section", { class: "dev-col" }, parts);
  }

  function knowledge(p) {
    const k = p.knowledge || { waiting: [], confirmed: 0, withdrawn: 0 };
    const parts = [el("h2", {}, "What the team learned", el("span", { class: "n" }, k.confirmed + " confirmed")),
      el("p", {}, "MIA's write-ups of finished work wait here until someone confirms them; only confirmed ones are " +
        "given to the agents. Her local model gets these wrong often (" + k.withdrawn + " withdrawn so far), so check each " +
        "against its sources.")];
    parts.push(k.waiting.length ? el("ul", { class: "dev-saga" }, k.waiting.map((e) => el("li", {},
      el("div", { class: "head" }, el("b", {}, e.title), " " + e.kind + " · " + e.id),
      el("div", { class: "said" }, e.body), el("div", { class: "dim src" }, e.from.join(" · ")),
      p.writable ? el("div", { class: "dev-say-row" },
        el("button", { class: "dev-chip ok", type: "button", onclick: () => post("api/knowledge", { act: "confirm", id: e.id }) }, "Right"),
        el("button", { class: "dev-chip", type: "button", onclick: () => post("api/knowledge", { act: "withdraw", id: e.id,
          why: prompt("What's wrong with it?") || "not right" }) }, "Wrong")) : "")))
      : el("p", { class: "empty" }, "Nothing waiting."));
    return el("section", { class: "dev-col dev-chronicles" }, parts);
  }

  function chronicles(p) {
    const s = p.saga || { waiting: 0, candidates: [], events: [] };
    const parts = [el("h2", {}, "The Chronicles", el("span", { class: "n" }, s.waiting + " waiting")),
      el("p", {}, "What really happened that could become the story, found by rules in the records. Nothing joins the " +
        "series until you say so. Private keeps it in the archive but out of the comic. In the Council, " +
        "\"remember this for the Chronicles: …\" adds one yourself.")];
    if (s.candidates.length) parts.push(el("ul", { class: "dev-saga" }, s.candidates.map((c) => el("li", {},
      el("div", { class: "head" }, el("b", {}, c.title), " " + c.category + " · " + stars(c.significance) + " · " + when(c.at)),
      el("div", { class: "said" }, c.summary),
      el("div", { class: "dim src" }, c.sources.join(" · ")),
      p.writable ? el("div", { class: "dev-say-row" },
        el("button", { class: "dev-chip ok", type: "button", onclick: () => decide("accept", c.ref) }, "For the series"),
        el("button", { class: "dev-chip", type: "button", onclick: () => decide("private", c.ref) }, "Keep private"),
        el("button", { class: "dev-chip", type: "button", onclick: () => decide("drop", c.ref) }, "Drop")) : ""))));
    else parts.push(el("p", { class: "empty" }, "Nothing waiting."));
    if (s.events.length) parts.push(el("h2", { class: "gap" }, "In the archive"), el("ul", { class: "dev-agents" },
      s.events.map((e) => el("li", {}, el("span", {}, e.id + " · " + e.title),
        el("span", { class: "dim" }, e.privacy === "series" ? "for the series" : "private"),
        el("span", { class: "sub" }, e.category + " · " + stars(e.significance) + " · " + when(e.at))))));
    return el("section", { class: "dev-col dev-chronicles" }, parts);
  }

  function council(p) {
    const list = p.council || [];
    const byId = Object.fromEntries(list.map((m) => [m.id, m]));
    const asking = (p.asking || []).map((n) => el("li", { class: "dev-msg thinking" }, n + " is answering…"));
    const log = el("ul", { class: "dev-chat", "aria-live": "polite" },
      list.length ? list.map((m) => message(m, byId, list)) : el("li", { class: "empty" }, "Nobody's said anything yet."), asking);
    const parts = [el("h2", {}, "Council"), el("p", {},
      "@name asks one member; name two and say \"debate\" for two rounds; \"discuss\" or @all asks everyone here. " +
      "Members can ask each other one question at a time, and MIA only passes it on if the turn's budget allows " +
      "and she can't answer it herself. \"budget 4\" sets it; \"stop\" ends it. Nothing said here approves anything."), log];
    if (p.writable) {
      if (replyTo) parts.push(el("p", { class: "dev-replying" }, "Replying to " + replyTo.who + ": " + replyTo.text.slice(0, 80) + " ",
        el("button", { class: "dev-reply", type: "button", onclick: () => { replyTo = null; render(); } }, "Cancel")));
      const box = el("textarea", { class: "dev-say", rows: "3", placeholder: open ? "About " + open + "…" : "Message the council",
        "aria-label": "Message the council" });
      box.value = draft;
      box.addEventListener("input", () => { draft = box.value; });
      box.addEventListener("keydown", (e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(box.value); } });
      parts.push(box, el("div", { class: "dev-say-row" },
        MEMBERS.map((n) => el("button", { class: "dev-chip", type: "button", onclick: () => {
          draft = (box.value.trim() + " @" + n + " ").trimStart(); box.value = draft; box.focus(); } }, "@" + n)),
        el("button", { class: "dev-send", type: "button", disabled: sending, onclick: () => send(box.value) }, sending ? "Sending…" : "Send")));
      if (chatNote) parts.push(el("p", { class: "dev-note" }, chatNote));
    } else parts.push(el("p", { class: "dim" }, "Write to the council from the MIA Development window on the computer."));
    return el("section", { class: "dev-col dev-council" }, parts);
  }

  let chatAtBottom = true, chatSeen = false;
  // Her Development Evolution Timeline (core/dev_evolution.py, T-0023, DEC-0071): totals, then month by month what
  // was decided, committed, finished and made (capabilities, tools, screens), bugs found and fixed, lab work merged or
  // undone, and the latest approved decisions as milestones. Counted from the shared history; formatting only here.
  function evolutionPanel(p) {
    const ev = p.evolution;
    if (!ev || !(ev.months || []).length) return "";
    const t = ev.totals || {};
    const LABELS = [["decisions", "Decisions"], ["commits", "Commits"], ["tasks_done", "Tasks done"], ["capabilities", "Capabilities"],
      ["tools", "Tools"], ["screens", "Screens"], ["bugs_found", "Bugs found"], ["bugs_fixed", "Bugs fixed"], ["merged", "Lab merged"], ["undone", "Undone"]];
    const top = Math.max(1, ...ev.months.map((m) => m.commits + m.tasks_done));
    return el("section", { class: "dev-col dev-evolution", "aria-label": "Her evolution" },
      el("h2", {}, "Her evolution", el("span", { class: "n" }, ev.months.length + (ev.months.length === 1 ? " month" : " months"))),
      el("p", {}, "How she's grown, counted from the shared history: never estimated."),
      el("div", { class: "dev-evo-totals" }, LABELS.filter(([k]) => t[k]).map(([k, label]) =>
        el("div", { class: "dev-evo-total" }, el("b", {}, String(t[k])), el("span", { class: "dim" }, label)))),
      el("ul", { class: "dev-agents dev-evo-months" }, ev.months.slice().reverse().map((m) => {
        const bar = barOf(Math.round(100 * (m.commits + m.tasks_done) / top));
        return el("li", {},
          el("span", {}, new Date(m.month + "-15T12:00:00").toLocaleDateString(undefined, { month: "long", year: "numeric" })),
          el("span", { class: "dim" }, LABELS.filter(([k]) => m[k]).map(([k, label]) => m[k] + " " + label.toLowerCase()).join(" · ") || "quiet"),
          el("span", { class: "sub" }, bar,
            m.new_parts.length ? el("span", { class: "dim" }, " New: " + m.new_parts.slice(0, 6).join(", ") + (m.new_parts.length > 6 ? "…" : "")) : ""));
      })),
      (ev.milestones || []).length ? [el("h2", { class: "gap" }, "Milestones"),
        el("ul", { class: "dev-agents" }, ev.milestones.slice().reverse().map((ms) =>
          el("li", {}, el("span", {}, ms.ref + " · " + ms.title), el("span", { class: "dim" }, when(ms.at)))))] : "");
  }

  // Disagreements still open (core/disagreements.py, T-0022, DEC-0071 point 3): decisions, designs and tasks in
  // review, Zac's first, each with who raised it, what they said, the answer, whose move it is and, when it's Zac's,
  // the command that settles it (settling stays at the keyboard, like approving).
  function disagreementsPanel(p) {
    const list = p.disagreements || [];
    if (!list.length) return "";
    const yours = list.filter((d) => d.status === "zac").length;
    return el("section", { class: "dev-col dev-disagree", "aria-label": "Open disagreements" },
      el("h2", {}, "Open disagreements", el("span", { class: "n" }, yours ? yours + " yours" : String(list.length))),
      el("p", {}, "A disagreement is answered, never dropped. When they still disagree after an answer, it's yours to decide."),
      el("ul", { class: "dev-agents" }, list.map((d) => el("li", { class: d.status === "zac" ? "yours" : "" },
        el("span", {}, d.subject + " · " + d.kind),
        el("span", { class: "dev-chip " + (d.status === "zac" ? "attn" : "") }, d.status === "zac" ? "your call" : d.status === "answered" ? "answered" : "open"),
        el("span", { class: "sub" }, (d.raised_by.length ? d.raised_by.join(", ") + ": " : "") + (d.why[d.why.length - 1] || ""),
          d.answer ? el("span", { class: "dev-answer" }, " Answer: " + d.answer) : "",
          el("span", { class: "dim" }, " " + d.next + (d.at ? " · " + when(d.at) : "")),
          d.command ? el("code", { class: "dev-cmd" }, d.command) : "")))));
  }

  function render() {
    const p = data;
    const panel = $("panel");
    const kept = document.querySelector(".dev-detail");
    const scrolled = kept ? kept.scrollTop : 0;
    // Zac, 2026-11-06 (to the council): the page kept scrolling itself to the top. Replacing the panel empties
    // the page for a moment, so the browser jumped up; keep where the page was, and put it back after.
    const pageY = window.scrollY;
    if (panel.firstChild) panel.style.minHeight = panel.offsetHeight + "px";
    const said = document.activeElement && document.activeElement.classList.contains("dev-say") ? document.activeElement : null;
    const caret = said ? [said.selectionStart, said.selectionEnd] : null;
    if (!p.available) { panel.style.minHeight = ""; panel.replaceChildren(el("p", { class: "empty" }, "The development work lives on the computer with MIA's code.")); return; }
    const all = Object.values(p.board).flat();
    const chosen = all.find((t) => t.id === open);
    const latest = p.latest;
    const live = latest && Date.now() - new Date(latest.at) < 15 * 60000;
    const search = el("input", { class: "dev-search", type: "search", placeholder: "Search everything that happened",
      value: query, "aria-label": "Search the history" });
    search.addEventListener("change", () => { query = search.value.trim(); refresh(); });
    const lessons = Object.entries(p.lessons || {});
    panel.replaceChildren(
      el("div", { class: "dev-now" + (live ? " live" : "") }, el("span", { class: "pulse" }),
        latest ? el("span", {}, (live ? "Now: " : "Last: ") + latest.who + " " + (ACTION[latest.action] || latest.action) +
          (latest.task ? " " + latest.task : "") + ", " + ago(latest.at)) : "Nothing has happened yet."),
      el("div", { class: "dev-flow" }, COLUMNS.map(([k, name, about]) => el("section", { class: "dev-col " + k, "aria-label": name },
        el("h2", {}, name, el("span", { class: "n" }, p.board[k].length)), el("p", {}, about),
        p.board[k].length ? shown(k, p.board[k]).map(card) : el("p", { class: "empty" }, k === "yours" ? "Nothing needs you." : "None."),
        more(k, p.board[k])))),
      disagreementsPanel(p),
      chosen ? detail(chosen) : "",
      el("div", { class: "dev-grid2" }, council(p),
        el("section", { class: "dev-col" }, el("h2", {}, "Who's on the team"),
          el("p", {}, "Each agent, the account it signs in with, and what it's doing."),
          el("ul", { class: "dev-agents" }, p.agents.map(agent)),
          lessons.length ? [el("h2", { class: "gap" }, "What the reviewers have learned"),
            el("ul", { class: "dev-agents" }, lessons.map(([prov, list]) => el("li", {}, el("span", {}, prov),
              el("span", { class: "dim" }, list.length + " lesson" + (list.length === 1 ? "" : "s")),
              el("span", { class: "sub" }, list.slice(-3).map((l) => l.lesson).join(" · ")))))] : "")),
      el("div", { class: "dev-grid2" }, missions(p), voices(p)),
      el("div", { class: "dev-grid2" }, independence(p), knowledge(p)),
      el("div", { class: "dev-grid2" }, nightPanel(p), loopsPanel(p)),
      evolutionPanel(p),
      architecture(p),
      chronicles(p),
      el("section", { class: "dev-col dev-history" }, el("h2", {}, "Everything that happened"), search,
        p.activity.length ? el("ul", { class: "dev-time" }, p.activity.map(event))
          : el("p", { class: "empty" }, query ? "Nothing matches." : "Nothing yet.")));
    const drawer = document.querySelector(".dev-detail");
    if (drawer && kept) drawer.scrollTop = scrolled;
    const chat = document.querySelector(".dev-chat");
    if (chat && (chatAtBottom || !chatSeen)) chat.scrollTop = chat.scrollHeight;
    chatSeen = true;
    const box = document.querySelector(".dev-say");
    if (box && caret) { box.focus({ preventScroll: true }); box.setSelectionRange(caret[0], caret[1]); }
    panel.style.minHeight = "";
    window.scrollTo(0, pageY);
    if (chat) chat.addEventListener("scroll", () => { chatAtBottom = chat.scrollHeight - chat.scrollTop - chat.clientHeight < 40; });
  }

  async function refresh() {
    try { data = await load(); render(); }
    catch (e) { $("panel").replaceChildren(el("p", { class: "empty" }, e.message || "Couldn't read the work.")); }
  }

  // While it's open and showing, keep it current (nothing to re-read when hidden).
  // Not while someone's typing (a re-draw would take their place), and sooner while a member is answering.
  let ticks = 0;
  setInterval(() => {
    ticks += 1;
    const typing = document.querySelector(".dev-search:focus");
    const waiting = data && (data.asking || []).length;
    if (document.visibilityState === "visible" && !typing && (waiting || ticks % 5 === 0)) refresh();
  }, 2000);
  if (standalone) refresh();
  else MIAShell.start(refresh);
})();
