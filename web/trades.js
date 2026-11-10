/*
 * trades.js — Trade Master (claude, 2026-11-09, DEC-0149).
 * Renders MIA.trades(item) (core/web_trades.py):
 *   - the walkthrough, when a job or diagnosis is going: the step in focus large (or the check), why, what to watch
 *     for, the hold point (checked or not), where it is in the job, and Next / Checked / Back / Stop (Yes / No for a
 *     diagnosis); a stop rule's "what to do instead" when it stopped; the result when it finished;
 *   - the job or diagnosis opened: its outline (scope, permit, hazards, what to wear, tools, materials, phases and
 *     steps, stop rules, sources), Start It and Make It a Mission;
 *   - the library by trade, each job saying whether it's confirmed or drafted.
 * Every press is a trade.* action through MIAShell.act (core/trade_actions.py): the hold points are enforced in
 * code, exactly as by voice, and each press can be undone. Formatting only.
 */
(function () {
  "use strict";
  const { el } = MIAShell;
  const $ = (id) => document.getElementById(id);
  let data = null;
  let chosen = new URLSearchParams(location.search).get("item") || "";

  const act = (kind, params) => MIAShell.act({ kind, params: params || {} }, { quick: true });
  const btn = (label, onclick, cls) => el("button", { type: "button", class: "btn " + (cls || "btn-ghost"), onclick }, label);
  const list = (title, items) => items && items.length ? el("div", { class: "tm-list" },
    el("p", { class: "pw-label" }, title), el("ul", {}, ...items.map((x) => el("li", {}, x)))) : null;

  // ---- the walkthrough
  function walk(w) {
    const done = w.status !== "working";
    const head = el("div", { class: "tm-walk-head" },
      el("p", { class: "pw-label" }, (w.kind === "diagnosis" ? "Diagnosing" : "Walking through") + " · " + w.title),
      w.progress && w.progress.of ? el("p", { class: "tm-where" }, w.progress.phase + " · step " + w.progress.step + " of " + w.progress.of) : null,
      w.progress && w.progress.of ? el("div", { class: "tm-bar", role: "progressbar", "aria-valuemin": "0", "aria-valuemax": String(w.progress.of),
        "aria-valuenow": String(w.progress.step), "aria-label": "Steps done" },
        el("span", { style: "width:" + Math.round(100 * (w.progress.step - 1) / w.progress.of) + "%" })) : null);
    if (done) {
      return el("section", { class: "glass tm-walk " + w.status, "aria-live": "polite" }, head,
        el("p", { class: "tm-step" }, w.status === "stopped" ? "Stopped" : "Done"),
        el("p", { class: w.status === "stopped" ? "tm-instead" : "tm-why" }, w.status === "stopped" ? w.stopped : w.result || w.say),
        el("div", { class: "tm-row" }, btn("Start It Again", () => act("trade.start", { item_id: w.item_id }), "btn-primary")));
    }
    const diag = w.kind === "diagnosis";
    const holdOpen = w.hold && !w.checked;
    return el("section", { class: "glass tm-walk", "aria-live": "polite" }, head,
      el("p", { class: "tm-step" }, w.step_text || w.say),
      w.why ? el("p", { class: "tm-why" }, el("b", {}, "Why: "), w.why) : null,
      w.watch ? el("p", { class: "tm-watch" }, el("b", {}, "Watch for: "), w.watch) : null,
      w.hold ? el("p", { class: "tm-hold " + (w.checked ? "ok" : "attn") }, el("b", {}, w.checked ? "Checked: " : "Before you go on: "), w.hold) : null,
      (w.phases || []).length ? el("ol", { class: "tm-phases", "aria-label": "Phases" }, ...w.phases.map((p) =>
        el("li", { class: p.state }, p.name))) : null,
      el("div", { class: "tm-row" }, ...(diag
        ? [btn("Yes", () => act("trade.answer", { answer: "yes" }), "btn-primary"), btn("No", () => act("trade.answer", { answer: "no" }), "btn-primary")]
        : [holdOpen ? btn("Checked", () => act("trade.check"), "btn-primary") : null,
          btn("Next Step", () => act("trade.next"), holdOpen ? "btn-ghost" : "btn-primary"),
          btn("Back", () => act("trade.back"))]),
        btn("Stop", () => act("trade.stop"), "btn-quiet")),
      (w.rules || []).length ? el("details", { class: "tm-rules" }, el("summary", {}, "When to stop (" + w.rules.length + ")"),
        ...w.rules.map((r) => el("p", {}, el("b", {}, r.when + ": "), r.instead))) : null,
      el("p", { class: "dim tm-say" }, "Or say “next”, “checked”, “why”, “back” or “stop”; “I smell gas” stops it at once."));
  }

  // ---- one job or diagnosis, opened
  function outline(o, live) {
    const isLive = live && live.item_id === o.id && live.status === "working";
    return el("section", { class: "glass tm-open" },
      el("p", { class: "pw-label" }, o.trade + " · " + o.kind_word),
      el("h2", {}, o.name),
      el("p", { class: "tm-status" + (o.status_word === "Confirmed" ? " ok" : "") }, o.status_word),
      el("p", {}, o.scope),
      o.permit ? el("p", { class: "tm-permit" }, el("b", {}, "Permit: "), o.permit) : null,
      o.kind === "diagnosis" ? el("p", {}, el("b", {}, "First check: "), o.first) : null,
      el("div", { class: "tm-row" },
        isLive ? null : btn(o.kind === "diagnosis" ? "Start Diagnosing" : "Start It", () => act("trade.start", { item_id: o.id }), "btn-primary"),
        o.kind !== "diagnosis" ? btn("Make It a Mission", () => act("trade.plan", { item_id: o.id })) : null),
      el("div", { class: "tm-cols" },
        list("Hazards", o.hazards), list("Wear", o.ppe), list("Tools", o.tools), list("Materials", o.materials)),
      (o.phases || []).length ? el("div", { class: "tm-outline" }, el("p", { class: "pw-label" }, o.steps + " steps"),
        ...o.phases.map((p, i) => el("details", { class: "tm-phase", open: i === 0 ? "" : null },
          el("summary", {}, (i + 1) + ". " + p.name + " · " + p.steps.length),
          el("ol", {}, ...p.steps.map((s) => el("li", {}, s.do, s.hold ? el("span", { class: "tm-holdtag" }, " hold point") : null)))))) : null,
      (o.rules || []).length ? el("div", { class: "tm-list" }, el("p", { class: "pw-label" }, "Stop if"),
        ...o.rules.map((r) => el("p", { class: "tm-rule" }, el("b", {}, r.when + ": "), r.instead))) : null,
      list("Sources", o.sources));
  }

  // ---- the library
  function shelf(groups) {
    return el("section", { class: "tm-shelf", "aria-label": "Jobs and diagnoses" }, ...groups.map((g) =>
      el("div", { class: "tm-trade" }, el("p", { class: "pw-label" }, g.name),
        el("ul", { class: "tm-items" }, ...g.items.map((it) => el("li", {},
          el("button", { type: "button", class: "glass tm-item" + (it.id === chosen ? " on" : ""), "aria-current": it.id === chosen ? "true" : null,
            onclick: () => { chosen = it.id; refresh(); } },
            el("span", { class: "tm-kind" }, it.kind_word),
            el("b", {}, it.name),
            el("span", { class: "dim" }, it.steps + (it.kind === "diagnosis" ? " checks" : " steps") + " · " + it.status_word))))))));
  }

  function paint() {
    if (!data) return;
    $("tm-sub").textContent = "Any job or diagnosis, walked through step by step: hold points checked before you go on, "
      + "and stop rules that end it when something's wrong.";
    if (!data.available) { $("panel").replaceChildren(el("p", { class: "dim" }, "Trade Master isn't on this MIA.")); return; }
    $("panel").replaceChildren(...[
      data.live ? walk(data.live) : null,
      el("div", { class: "tm-main" },
        shelf(data.library),
        data.opened ? outline(data.opened, data.live) : el("p", { class: "dim tm-pick" }, "Pick a job or a diagnosis to see it whole.")),
      el("p", { class: "dim tm-standard" }, data.standard),
    ].filter(Boolean));
  }

  async function refresh() { data = await MIA.trades(chosen); paint(); }

  MIAShell.start(refresh, { refreshOnChange: true });
})();
