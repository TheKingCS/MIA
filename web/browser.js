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

  // Driving her browser from here (2026-11-07): an address bar, a live picture, Back / Close, and teaching.
  async function run(action) {
    await act(action, { quick: true });
    draw();
  }

  // The live view (2026-11-07): her browser lives inside MIA; a frame about once a second while it's open, and the
  // person works it from the picture. Clicks land where they're made; typing, keys and scrolling go to the page.
  let live = null;  // {img, size, title, url}: the picture on the page now
  let frameTimer = null, frames = 0, lastState = "";

  async function nextFrame() {
    frameTimer = null;
    if (!live || !document.body.contains(live.img)) return;
    if (!document.hidden) {
      try {
        const blob = await MIA.download("/api/browser/frame?t=" + Date.now());
        const old = live.img.src;
        live.img.src = URL.createObjectURL(blob);
        if (old && old.startsWith("blob:")) URL.revokeObjectURL(old);
      } catch (e) { /* closed or busy: try again */ }
      if (++frames % 5 === 0) {  // every few seconds: something waiting for an OK, or the page she's on, changed?
        try {
          const data = await MIA.browser();
          const state = JSON.stringify([data.open && data.open.url, data.learning, data.waiting.length, data.tasks.length]);
          if (state !== lastState) { lastState = state; draw(); return; }
        } catch (e) { /* keep showing */ }
      }
    }
    frameTimer = setTimeout(nextFrame, 800);
  }

  async function send(body) {
    try {
      const where = await MIA.browserInput(body);
      if (live) { live.title.textContent = where.title || where.url; live.url.textContent = where.url; }
    } catch (e) { MIAShell.say(e.message); }
    if (frameTimer) { clearTimeout(frameTimer); }
    nextFrame();
  }

  function liveView(data) {
    const img = el("img", { class: "browser-shot browser-live", alt: "MIA's browser, live. Click to click there.",
      title: "Click here to click on the page; scroll to scroll it" });
    const size = data.size || { width: 1280, height: 800 };
    const spot = (e) => {
      const box = img.getBoundingClientRect();
      return { x: Math.round((e.clientX - box.left) / box.width * size.width),
        y: Math.round((e.clientY - box.top) / box.height * size.height) };
    };
    img.addEventListener("click", (e) => send(Object.assign({ kind: "click" }, spot(e))));
    img.addEventListener("wheel", (e) => { e.preventDefault(); send(Object.assign({ kind: "scroll", dy: e.deltaY }, spot(e))); }, { passive: false });
    const typed = el("input", { type: "text", class: "input", placeholder: "Type into the page (click a box in the picture first)", autocomplete: "off" });
    const typing = el("form", { class: "form-row", onsubmit: (e) => {
      e.preventDefault();
      if (typed.value) { send({ kind: "type", text: typed.value }); typed.value = ""; }
    } }, typed, el("button", { type: "submit", class: "btn btn-ghost" }, "Type"));
    const keys = el("div", { class: "row-buttons" }, ["Enter", "Tab", "Backspace", "Escape", "PageDown", "PageUp"].map((k) =>
      btn(k === "PageDown" ? "Page down" : k === "PageUp" ? "Page up" : k, "btn-ghost btn-small", () => send({ kind: "key", key: k }))));
    const title = el("p", { class: "row-title" }, data.open.title || data.open.url);
    const url = el("p", { class: "dim" }, data.open.url);
    live = { img, size, title, url };
    lastState = JSON.stringify([data.open && data.open.url, data.learning, data.waiting.length, data.tasks.length]);
    if (frameTimer) clearTimeout(frameTimer);
    nextFrame();
    return [title, url, img, typing, keys];
  }

  function controls(data) {
    const address = el("input", { type: "text", class: "input", placeholder: "A website (county.gov) or what to search for",
      autocomplete: "off", "aria-label": "Website or search" });
    const bar = el("form", { class: "form-row", onsubmit: (e) => {
      e.preventDefault();
      if (address.value.trim()) run({ kind: "browser.open", params: { target: address.value.trim() } });
    } }, address, el("button", { type: "submit", class: "btn btn-green" }, "Open"));
    if (!data.open) {
      return section("Her Browser", bar,
        el("p", { class: "dim" }, "Closed. Open a website or search above and it shows here, live: click on it to "
          + "click, scroll to scroll, type in the box under it. She works in the same view."));
    }
    const name = el("input", { type: "text", class: "input", placeholder: "Name a task to teach her from here", autocomplete: "off" });
    const teach = data.learning
      ? el("div", { class: "row-buttons" },
        el("p", {}, "Watching you do \"" + data.learning + "\": do it in the picture above, then keep it."),
        btn("Done, keep it", "btn-green", () => run({ kind: "browser.learn_done", params: {} })))
      : el("form", { class: "form-row", onsubmit: (e) => {
        e.preventDefault();
        if (name.value.trim()) run({ kind: "browser.learn", params: { name: name.value.trim() } });
      } }, name, el("button", { type: "submit", class: "btn btn-ghost" }, "Learn a task"));
    return section("Her Browser", bar,
      ...liveView(data),
      el("div", { class: "row-buttons" },
        btn("Back", "btn-ghost btn-small", () => run({ kind: "browser.back", params: {} })),
        btn("Ask MIA about this page", "btn-ghost btn-small", () => MIAShell.talk(true, "Read the page and tell me what's on it")),
        btn("Close", "btn-ghost btn-small", () => run({ kind: "browser.close", params: {} }))),
      teach);
  }

  async function draw() {
    const data = await MIA.browser();
    if (!data.available) {
      $("panel").replaceChildren(el("p", { class: "empty" }, "MIA's browser isn't on this device."));
      return;
    }
    $("browser-sub").textContent = data.open ? "On " + (data.open.title || data.open.url) : "Closed";
    $("panel").replaceChildren(...[
      controls(data),
      data.waiting.length ? section("Waiting For Your OK", ...data.waiting.map(waitingCard)) : null,
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
