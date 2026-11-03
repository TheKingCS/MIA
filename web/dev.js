/*
 * dev.js — the development dashboard (claude, 2026-11-03, DEC-0068/0070).
 * Renders MIA.dev() (core/work_dashboard.py): what's waiting for review and
 * approval, the work, the agents and whether each is on this computer, and
 * the activity, searchable. Read-only, formatting only: changes go through
 * `python -m tools.work`, and approving is Zac at the keyboard.
 */
(function () {
  "use strict";
  const { el } = MIAShell;
  const $ = (id) => document.getElementById(id);
  const section = (title, ...body) =>
    el("section", { class: "glass money-section" }, el("div", { class: "sect" }, el("h2", {}, title)), ...body);
  const when = (iso) => iso ? new Date(iso).toLocaleString(undefined, { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" }) : "";
  const STATUS = { review: "Waiting For Review", claimed: "In Progress", ready: "Ready", blocked: "Blocked", open: "Waiting" };

  function task(t) {
    const bits = [STATUS[t.status] || t.status, t.owner, t.role].filter(Boolean);
    if (t.waiting_on.length) bits.push("after " + t.waiting_on.join(", "));
    if (t.verdict) bits.push("review: " + t.verdict);
    if (t.branch) bits.push(t.branch);
    return el("li", { class: "dg-run" }, el("div", {},
      el("div", { class: "row-title" }, t.id + " · " + t.title), el("div", { class: "row-sub dim" }, bits.join(" · "))));
  }

  function event(e) {
    return el("li", { class: "dg-run" }, el("div", {},
      el("div", { class: "row-title" }, (e.task ? e.task + " · " : "") + e.action + " · " + e.who),
      el("div", { class: "row-sub dim" }, when(e.at) + (e.detail ? " · " + e.detail : ""))));
  }

  async function draw(query) {
    const p = await MIA.dev(query);
    if (!p.available) { $("panel").replaceChildren(el("p", { class: "empty" }, "The development work lives on the computer with MIA's code.")); return; }
    const s = p.summary;
    $("strip").replaceChildren(...[["review", "To Review"], ["claimed", "In Progress"], ["ready", "Ready"],
      ["blocked", "Blocked"], ["done", "Done"]].map(([k, label]) =>
      el("div", { class: "cell " + (k === "review" && s[k] ? "soon" : "ok") }, el("span", { class: "n" }, s[k]), el("span", { class: "t" }, label))));
    const search = el("input", { type: "search", placeholder: "Search the history", value: query || "", "aria-label": "Search the history" });
    search.addEventListener("change", () => draw(search.value.trim()));
    $("panel").replaceChildren(
      section("Waiting For You",
        p.queue.length ? el("ul", { class: "dg-runs" }, p.queue.map(task))
          : el("p", { class: "empty" }, "Nothing's waiting for review or approval."),
        el("p", { class: "dim" }, "Approving is yours, at the computer: python -m tools.work approve T-0000")),
      section("The Work", el("ul", { class: "dg-runs" }, p.tasks.filter((t) => t.status !== "review").map(task))),
      section("Agents", el("ul", { class: "dg-runs" }, p.agents.map((a) => el("li", { class: "dg-run" }, el("div", {},
        el("div", { class: "row-title" }, a.role), el("div", { class: "row-sub dim" },
          [a.tier, a.provider, a.here ? "on this computer" : "not on this computer"].join(" · "))))))),
      section("History", search, p.activity.length ? el("ul", { class: "dg-runs" }, p.activity.map(event))
        : el("p", { class: "empty" }, query ? "Nothing matches." : "Nothing yet.")),
      p.done.length ? section("Recently Done", el("ul", { class: "dg-runs" }, p.done.map(task))) : "");
  }

  MIAShell.start(() => draw(""));
})();
