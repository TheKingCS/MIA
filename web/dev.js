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
  const when = (iso) => iso ? new Date(iso).toLocaleString(undefined,
    { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" }) : "";
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
    const state = !a.here ? "not installed" : a.signed_in === false ? "needs sign-in" : "ready";
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

  function render() {
    const p = data;
    const panel = $("panel");
    const kept = document.querySelector(".dev-detail");
    const scrolled = kept ? kept.scrollTop : 0;
    if (!p.available) { panel.replaceChildren(el("p", { class: "empty" }, "The development work lives on the computer with MIA's code.")); return; }
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
      chosen ? detail(chosen) : "",
      el("div", { class: "dev-grid2" },
        el("section", { class: "dev-col" }, el("h2", {}, "Who's on the team"),
          el("p", {}, "Each agent, the account it signs in with, and what it's doing."),
          el("ul", { class: "dev-agents" }, p.agents.map(agent)),
          lessons.length ? [el("h2", { class: "gap" }, "What the reviewers have learned"),
            el("ul", { class: "dev-agents" }, lessons.map(([prov, list]) => el("li", {}, el("span", {}, prov),
              el("span", { class: "dim" }, list.length + " lesson" + (list.length === 1 ? "" : "s")),
              el("span", { class: "sub" }, list.slice(-3).map((l) => l.lesson).join(" · ")))))] : ""),
        el("section", { class: "dev-col" }, el("h2", {}, "Everything that happened"), search,
          p.activity.length ? el("ul", { class: "dev-time" }, p.activity.map(event))
            : el("p", { class: "empty" }, query ? "Nothing matches." : "Nothing yet."))));
    const drawer = document.querySelector(".dev-detail");
    if (drawer && kept) drawer.scrollTop = scrolled;
  }

  async function refresh() {
    try { data = await load(); render(); }
    catch (e) { $("panel").replaceChildren(el("p", { class: "empty" }, e.message || "Couldn't read the work.")); }
  }

  // While it's open and showing, keep it current (nothing to re-read when hidden).
  setInterval(() => { if (document.visibilityState === "visible" && !document.querySelector(".dev-search:focus")) refresh(); }, 10000);
  if (standalone) refresh();
  else MIAShell.start(refresh);
})();
