/*
 * browser.js — MIA's own browser (claude, 2026-11-07, DEC-0117). Renders MIA.browser() (core/web_browser.py): the
 * page she's on, each step waiting for your OK (its screenshot, Go ahead / Cancel on the step's own proposal), the
 * task she's learning, and the tasks you taught her (how practised, the last run, Do it / Forget through
 * MIAShell.act). Formatting only; the look is muse's.
 */
(function () {
  "use strict";
  const { el, act } = MIAShell;
  const $ = (id) => document.getElementById(id);

  const section = (title, ...body) => el("section", { class: "glass money-section" }, el("h2", {}, title), ...body);
  const btn = (text, cls, onclick) => el("button", { type: "button", class: "btn " + cls, onclick }, text);

  async function decide(step, yes) {
    if (!step.proposal_id) return;
    try {
      const done = yes ? await MIA.approve(step.proposal_id) : await MIA.reject(step.proposal_id);
      MIAShell.say(yes ? (done.result || "Done.") : "Cancelled: nothing was pressed.");
    } catch (e) { MIAShell.say(e.message); }
    draw();
  }

  async function shot(step, holder) {
    try {
      const blob = await MIA.download("/api/browser/shot?id=" + encodeURIComponent(step.id));
      holder.replaceChildren(el("img", { src: URL.createObjectURL(blob), alt: "What MIA's browser showed", class: "browser-shot" }));
    } catch (e) { holder.replaceChildren(el("p", { class: "dim" }, "The screenshot isn't there any more.")); }
  }

  function waitingCard(step) {
    const picture = el("div", {});
    if (step.shot) shot(step, picture);
    return el("div", { class: "glass inbox-card" },
      el("p", { class: "row-title" }, step.summary),  // a sentence with a web address: never title-cased
      el("p", { class: "dim" }, "Waits because " + step.why + " · " + step.site),
      picture,
      el("div", { class: "row-buttons" }, btn("Go ahead", "btn-green", () => decide(step, true)), btn("Cancel", "btn-ghost", () => decide(step, false))));
  }

  function taskRow(task) {
    const last = task.last ? (task.last.clean ? "last run finished" : "last run stopped" + (task.last.note ? ": " + task.last.note : "")) : "not run yet";
    return el("div", { class: "row money-row" },
      el("div", {},
        el("div", { class: "row-title" }, task.name + (task.state === "learned" ? " · learned" : " · practising")),
        el("div", { class: "row-sub" }, task.steps.length + " steps · " + last),
        el("details", {}, el("summary", {}, "Steps"), el("ol", {}, task.steps.map((s) => el("li", {}, s))))),
      el("div", { class: "row-buttons" },
        btn("Do it", "btn-ghost btn-small", () => act({ kind: "browser.run_task", params: { task_id: task.id } })),
        btn("Forget", "btn-ghost btn-small", () => act({ kind: "browser.forget_task", params: { task_id: task.id } }))));
  }

  async function draw() {
    const data = await MIA.browser();
    if (!data.available) {
      $("panel").replaceChildren(el("p", { class: "empty" }, "MIA's browser isn't on this device."));
      return;
    }
    $("browser-sub").textContent = data.open ? "On " + (data.open.title || data.open.url) : "Closed";
    $("panel").replaceChildren(...[
      data.waiting.length ? section("Waiting For Your OK", ...data.waiting.map(waitingCard)) : null,
      data.learning ? section("Learning", el("p", {}, "Watching you do \"" + data.learning + "\" in her window. Say \"done\" when you've finished.")) : null,
      section("Tasks You Taught Her",
        data.tasks.length ? el("div", { class: "rows" }, data.tasks.map(taskRow))
          : el("p", { class: "empty" }, "None yet. Ask MIA to open where a task starts, say \"learn this\", and do it in her window.")),
      section("How She Browses",
        el("p", { class: "dim" }, "Her own Edge window, with none of your sign-ins. She reads, searches and follows links by herself; "
          + "anything that submits, buys, sends, signs in or deletes waits here for your OK, and she never types passwords or card numbers.")),
    ].filter(Boolean));
  }

  MIAShell.start(draw);
})();
