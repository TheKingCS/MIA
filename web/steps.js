/*
 * steps.js — Step By Step (claude, 2026-11-17, UI-7; core/step_plans.py).
 * Renders MIA.stepPlans(): each open plan with every step in order. A waiting step shows its sentence, the app it
 * changes, and Do It (steps.do, which asks first), Change (steps.change, its details in a form) and Leave Out
 * (steps.drop). A step MIA can't do from a plan says why. Every button is an action, so each is undoable.
 * Formatting only: the engine decides.
 */
(function () {
  "use strict";
  const { el, act, form } = MIAShell;
  const $ = (id) => document.getElementById(id);
  const btn = (label, cls, onclick) => el("button", { type: "button", class: "btn " + cls, onclick }, label);
  const chip = (text, cls) => el("span", { class: "chip " + (cls || "") }, text);
  const STATUS = { done: ["done", "ok"], dropped: ["left out", ""], failed: ["failed", "soon"], cant: ["can't from here", "soon"] };

  async function change(plan, s) {
    const names = Object.keys(s.params);
    if (!names.length) { MIAShell.say("This step has no details to change."); return; }
    const v = await form("Change Step " + s.number, names.map((n) => ({ name: n, label: n.replace(/_/g, " "), type: "text",
      required: false, options: [], default: s.params[n] == null ? "" : String(s.params[n]) })), {});
    if (v) act({ kind: "steps.change", params: { plan_id: plan.plan_id, step_id: s.step_id, params: v } }, { quick: true });
  }

  function step(plan, s) {
    const waiting = s.status === "waiting";
    const which = { plan_id: plan.plan_id, step_id: s.step_id };
    return el("li", { class: "glass step-row" + (waiting ? "" : " step-settled") }, ...[
      el("span", { class: "step-n" }, String(s.number)),
      el("div", { class: "step-body" }, ...[
        el("p", { class: "step-text" }, s.summary),
        el("p", { class: "dim step-meta" }, [s.app, s.source && s.source !== s.summary ? "from " + s.source : "",
          waiting ? "can be undone" : ""].filter(Boolean).join(" · ")),
        s.status === "done" && s.result ? el("p", { class: "dim" }, s.result) : null,
        s.why ? el("p", { class: "dim" }, s.why) : null,
      ].filter(Boolean)),
      waiting ? el("div", { class: "row-buttons step-buttons" },
        btn(s.label || "Do It", "btn-green btn-small", () => act({ kind: "steps.do", params: which })),
        btn("Change", "btn-ghost btn-small", () => change(plan, s)),
        btn("Leave Out", "btn-quiet btn-small", () => act({ kind: "steps.drop", params: which }, { quick: true })))
        : chip(STATUS[s.status][0], STATUS[s.status][1]),
    ].filter(Boolean));
  }

  function paint(data) {
    $("steps-sub").textContent = data.open.length
      ? "Each step is one change in one app. Nothing happens until you press it, one step at a time."
      : "No plan is open. A plan lines up changes across your apps and waits for you at every step.";
    $("panel").replaceChildren(...[
      el("div", { class: "row-buttons" }, btn("Plan My Week", "btn-green", () => act({ kind: "steps.plan_week", params: {} }, { quick: true }))),
      ...data.open.map((p) => el("section", { class: "step-plan" },
        el("div", { class: "sect" }, el("h2", {}, p.title),
          btn("Drop The Rest", "btn-quiet btn-small", () => act({ kind: "steps.drop_plan", params: { plan_id: p.plan_id } }))),
        el("p", { class: "dim" }, p.waiting + (p.waiting === 1 ? " step" : " steps") + " waiting for you"),
        el("ol", { class: "step-list" }, ...p.steps.map((s) => step(p, s))))),
      data.finished.length ? el("section", { class: "step-plan" }, el("h2", {}, "Finished Lately"),
        el("ul", { class: "step-finished" }, ...data.finished.map((p) =>
          el("li", { class: "dim" }, p.title + ": " + p.done + " of " + p.steps + " done" + (p.status === "dropped" ? ", the rest left out" : ""))))) : null,
      el("p", { class: "dim shelf-say" }, "Say \"plan my week\", \"what's the plan\", \"do step 1\" or \"drop step 2\" any time. " +
        "Anything that buys, sends or can't be undone is never a step here: it's done from its own screen."),
    ].filter(Boolean));
  }

  MIAShell.start(async () => { paint(await MIA.stepPlans()); }, { refreshOnChange: true });
})();
