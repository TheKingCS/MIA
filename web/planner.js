/*
 * planner.js — plans made together, then missions (claude, 2026-11-22, T-0060; core/project_plans.py).
 * Reads MIA.planner(): the plans (drafts and confirmed), the Library's builds (marked when Trade Master walks them),
 * the crops and the frost dates. Every change is an action (MIAShell.act): projectplan.draft for a new plan,
 * projectplan.change for a draft's size, beds, crops, frosts or a stage left out, projectplan.confirm (the project and
 * a mission a stage), projectplan.drop. Nothing is worked out here: the stages come from core. Formatting only.
 */
(function () {
  "use strict";
  const { el } = MIAShell;
  const $ = (id) => document.getElementById(id);

  function stageList(plan) {
    return el("div", { class: "sync-rows" }, plan.stages.map((s, i) => el("details", {},
      el("summary", {}, (i + 1) + ". " + s.name + " · " + s.steps.length + (s.steps.length === 1 ? " step" : " steps")),
      el("ol", {}, s.steps.map((st) => el("li", {}, st.do + (st.when ? " (" + st.when + ")" : ""),
        st.why ? el("p", { class: "dim" }, st.why) : null))),
      plan.status === "draft" ? el("button", { type: "button", class: "btn btn-ghost btn-small",
        onclick: () => MIAShell.act({ kind: "projectplan.change", params: { plan_id: plan.plan_id, leave_out: s.name } }).then(draw) },
        "Leave This Stage Out") : null)));
  }

  function planCard(plan) {
    const draft = plan.status === "draft";
    const buttons = draft ? [
      el("button", { type: "button", class: "btn btn-amber", onclick: () => MIAShell.act({ kind: "projectplan.confirm", params: { plan_id: plan.plan_id } }).then(draw) }, "Confirm"),
      plan.kind === "garden" ? el("button", { type: "button", class: "btn btn-ghost", onclick: () => gardenForm(plan) }, "Change It") : null,
      plan.kind === "build" && plan.shelf_plan ? el("button", { type: "button", class: "btn btn-ghost", onclick: () => sizeForm(plan) }, "Change The Size") : null,
      ...plan.left_out.map((s) => el("button", { type: "button", class: "btn btn-ghost btn-small",
        onclick: () => MIAShell.act({ kind: "projectplan.change", params: { plan_id: plan.plan_id, put_back: s } }).then(draw) }, "Put Back " + s)),
      el("button", { type: "button", class: "btn btn-ghost", onclick: () => MIAShell.act({ kind: "projectplan.drop", params: { plan_id: plan.plan_id } }).then(draw) }, "Let It Go"),
    ] : [el("a", { class: "btn btn-ghost", href: "missions.html" }, "Open Its Missions")];
    return el("section", { class: "glass money-section" },
      el("h2", {}, plan.title), el("p", { class: "dim" }, (plan.kind === "garden" ? "Garden" : "Build") + " · " + (draft ? "a draft: nothing is made until you confirm" : "confirmed")),
      ...plan.warnings.map((w) => el("p", { class: "plan-problem" }, w)),
      stageList(plan), el("div", { class: "row-buttons" }, buttons.filter(Boolean)));
  }

  async function sizeForm(plan) {
    const fields = plan.size_fields || [];  // the plan's own calculator's sizes (core/project_plans._size_fields)
    if (!fields.length) { MIAShell.say("This plan has no sizes to change."); return; }
    const v = await MIAShell.form("Change the size", fields.map((f) => ({ name: f.name, label: f.label + (f.unit ? " (" + f.unit + ")" : ""), type: "number", default: f.value })), {});
    if (!v) return;
    const sizes = {};
    fields.forEach((f) => { if (String(v[f.name] || "").trim()) sizes[f.name] = Number(v[f.name]); });
    await MIAShell.act({ kind: "projectplan.change", params: { plan_id: plan.plan_id, sizes } });
    draw();
  }

  // A garden: its beds ("Bed 1, 8 x 4 x 12" a line: name, length and width in feet, depth in inches), its crops
  // ("tomato in Bed 1" a line, or "lettuce in Bed 2, 8 sq ft"), and the frost dates.
  async function gardenForm(plan, data) {
    const beds = (plan && plan.beds || []).map((b) => b.name + ", " + b.length_ft + " x " + b.width_ft + (b.depth_in ? " x " + b.depth_in : "")).join("\n");
    const crops = (plan && plan.crops || []).map((c) => c.crop + (c.bed ? " in " + c.bed : "") + (c.sqft ? ", " + c.sqft + " sq ft" : "")).join("\n");
    const v = await MIAShell.form(plan ? "Change the garden" : "Plan a garden", [
      { name: "beds", label: "Beds, one a line: name, length x width in feet (x depth in inches for a raised bed)", type: "textarea", default: beds || "Bed 1, 8 x 4 x 12", required: true },
      { name: "crops", label: "Crops, one a line: the crop in a bed (and its square feet if you like). Known: " + ((data || {}).crops || []).map((c) => c.name).join(", "), type: "textarea", default: crops, required: true },
      { name: "last_frost", label: "Your average last spring frost (like April 20)", type: "text", default: (plan && plan.last_frost) || (data || {}).last_frost || "", required: true },
      { name: "first_frost", label: "Your average first fall frost (optional)", type: "text", default: (plan && plan.first_frost) || (data || {}).first_frost || "" },
    ], {});
    if (!v) return;
    const bedRows = v.beds.split("\n").map((l) => l.trim()).filter(Boolean).map((l) => {
      const [name, size] = l.includes(",") ? [l.slice(0, l.lastIndexOf(",")).trim(), l.slice(l.lastIndexOf(",") + 1)] : ["", l];
      const n = size.split(/x|×|by/i).map((s) => Number(s.trim()));
      return { name: name || undefined, length_ft: n[0], width_ft: n[1], depth_in: n[2] || 0 };
    });
    const cropRows = v.crops.split("\n").map((l) => l.trim()).filter(Boolean).map((l) => {
      const m = l.match(/^(.*?)(?:\s+in\s+(.*?))?(?:,?\s*([\d.]+)\s*(?:sq\.?\s*ft|square\s+feet))?$/i) || [l, l];
      return { crop: (m[1] || "").trim(), bed: (m[2] || "").trim(), sqft: Number(m[3] || 0) };
    });
    const params = { beds: bedRows, crops: cropRows, last_frost: v.last_frost, first_frost: v.first_frost };
    await MIAShell.act(plan ? { kind: "projectplan.change", params: Object.assign({ plan_id: plan.plan_id }, params) }
      : { kind: "projectplan.draft", params: Object.assign({ kind: "garden" }, params) });
    draw();
  }

  async function draw() {
    const data = await MIA.planner();
    if (!data.available) { $("panel").replaceChildren(el("p", { class: "empty" }, "The planner isn't on this MIA.")); return; }
    const builds = data.builds.filter((b) => b.walked).concat(data.builds.filter((b) => !b.walked));
    $("panel").replaceChildren(...[
      el("section", { class: "glass money-section" }, el("h2", {}, "Plan Something"),
        el("p", { class: "dim" }, "A build from the Library at your size, walked step by step, or a garden from your beds, crops and frost dates. You change the draft with MIA; Confirm makes the project and a mission for each stage."),
        el("div", { class: "row-buttons" },
          el("button", { type: "button", class: "btn btn-amber", onclick: () => gardenForm(null, data) }, "Plan A Garden"),
          el("select", { class: "input", "aria-label": "A build to plan", onchange: (e) => { if (e.target.value) MIAShell.act({ kind: "projectplan.draft", params: { kind: "build", shelf_plan: e.target.value } }).then(draw); } },
            el("option", { value: "" }, "Plan a build…"),
            ...builds.map((b) => el("option", { value: b.id }, b.title + (b.walked ? " (walked step by step)" : ""))))),
        el("p", { class: "dim" }, "Or say \"let's plan a 4 by 8 raised bed\" or \"plan my garden\".")),
      ...data.plans.map(planCard),
      data.sources.length ? el("p", { class: "dim" }, "Garden dates from: " + data.sources.join("; ") + ".") : null,
    ].filter(Boolean));
  }

  MIAShell.start(draw);
})();
