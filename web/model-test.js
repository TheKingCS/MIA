/*
 * model-test.js — the model test (claude, 2026-10-07, DEC-0019,
 * docs/PHONE_MODEL_TEST.md). Renders MIA.modelTest() (core/local_model.py):
 * each small model with Download / Start / Delete, the running model, a
 * test run's progress, and each model's last results: how often it picked
 * MIA's right tool, and how fast it read and answered. Checks again every
 * two seconds while something is going on. Keeps the screen awake during a
 * download or a test where the phone allows it.
 */
(function () {
  "use strict";
  const { el, say } = MIAShell;
  const $ = (id) => document.getElementById(id);
  let page = null;
  let timer = null;
  let awake = null;

  const section = (title, ...body) => el("section", { class: "glass money-section" }, el("div", { class: "sect" }, el("h2", {}, title)), ...body);
  const fact = (label, value) => el("div", { class: "acct-fact" }, el("span", { class: "dim" }, label), el("strong", {}, value));
  const gb = (mb) => (mb / 1000).toFixed(1) + " GB";
  const pct = (a, b) => (b ? Math.round((100 * a) / b) : 0) + "%";

  async function step(name, body) {
    try { page = await MIA.modelStep(name, body); draw(); } catch (e) { say(e.message); }
  }

  function busy() {
    const d = page.download, r = page.run;
    return (d.model_id && !d.finished) || page.server.state === "starting" || (r.model_id && !r.finished);
  }

  async function keepAwake(on) {
    try {
      if (on && !awake && navigator.wakeLock) awake = await navigator.wakeLock.request("screen");
      if (!on && awake) { await awake.release(); awake = null; }
    } catch (e) { /* not allowed here; the phone may dim */ }
  }

  function results(r) {
    if (!r) return el("p", { class: "dim" }, "Not tested yet.");
    return el("div", {},
      fact("Picked the right tool", r.passed + " of " + r.done + " (" + pct(r.passed, r.done) + ")"),
      fact("Typical answer took", r.median_seconds != null ? r.median_seconds + " s" : "—"),
      fact("Reading speed", r.read_per_second != null ? r.read_per_second + " tokens/s" : "—"),
      fact("Writing speed", r.write_per_second != null ? r.write_per_second + " tokens/s" : "—"),
      fact("Loading the model", r.load_seconds != null ? r.load_seconds + " s" : "—"),
      el("details", {}, el("summary", {}, "Every case (" + r.when + ")"),
        el("div", { class: "rows" }, r.results.map((c) => el("div", { class: "row" },
          el("div", {}, el("div", { class: "row-title" }, (c.ok ? "✅ " : "❌ ") + c.prompt),
            el("div", { class: "row-sub" }, c.detail + " · " + c.seconds + " s" + (c.error ? " · " + c.error : "")) ))))));
  }

  function model(m) {
    const d = page.download, server = page.server;
    const downloading = d.model_id === m.id && !d.finished;
    const running = server.model_id === m.id && server.state !== "stopped";
    const buttons = [];
    if (!m.downloaded && !downloading) {
      buttons.push(el("button", { type: "button", class: "btn btn-green", onclick: () => step("download", { model: m.id }) },
        m.partial_mb ? "Carry on downloading" : "Download (" + gb(m.size_mb) + ")"));
    }
    if (m.downloaded && !running) buttons.push(el("button", { type: "button", class: "btn btn-green", onclick: () => step("start", { model: m.id }) }, "Start"));
    if (running) buttons.push(el("button", { type: "button", class: "btn btn-ghost", onclick: () => step("stop") }, "Stop"));
    if ((m.downloaded || m.partial_mb) && !downloading) {
      buttons.push(el("button", { type: "button", class: "btn btn-ghost", onclick: () => {
        if (confirm("Delete " + m.name + " from this phone?")) step("delete", { model: m.id });
      } }, "Delete"));
    }
    let state = null;
    if (downloading) {
      state = el("div", {}, el("p", {}, "Downloading: " + d.done_mb + " of " + d.total_mb + " MB"),
        el("div", { class: "xpbar" }, el("div", { class: "xpbar-track" }, el("div", { class: "xpbar-fill", style: "width:" + pct(d.done_mb, d.total_mb) }))));
    } else if (d.model_id === m.id && d.error) {
      state = el("p", { class: "dim" }, d.error);
    } else if (running) {
      state = el("p", {}, server.state === "starting" ? "Loading into memory…" : server.state === "ready"
        ? "Running (loaded in " + server.load_seconds + " s). Talk uses this model now." : server.error);
    }
    return section(m.name, el("p", { class: "dim" }, m.about), state,
      el("div", { class: "acct-actions" }, buttons), el("h3", {}, "Last test"), results(m.results));
  }

  function runner() {
    const r = page.run, server = page.server;
    if (server.state !== "ready") {
      return section("Run the test", el("p", { class: "dim" }, "Download a model and tap Start. Then the test asks it the things people say to MIA and checks that it picks the right tool."));
    }
    if (r.model_id && !r.finished) {
      return section("Testing…",
        el("p", {}, r.done + " of " + r.total + " done, " + r.passed + " right" + (r.median_seconds != null ? " · typical " + r.median_seconds + " s each" : "")),
        el("div", { class: "xpbar" }, el("div", { class: "xpbar-track" }, el("div", { class: "xpbar-fill", style: "width:" + pct(r.done, r.total) }))),
        el("p", { class: "dim" }, "Keep MIA open while it runs."),
        el("div", { class: "acct-actions" }, el("button", { type: "button", class: "btn btn-ghost", onclick: () => step("cancel") }, "Stop the test")));
    }
    return section("Run the test",
      el("p", { class: "dim" }, "A quick test takes a few minutes; the full one maybe half an hour. Keep MIA open and the phone plugged in if you can."),
      el("div", { class: "acct-actions" },
        el("button", { type: "button", class: "btn btn-green", onclick: () => step("run", { count: page.quick }) }, "Quick test (" + page.quick + ")"),
        el("button", { type: "button", class: "btn btn-ghost", onclick: () => step("run", { count: page.full }) }, "Full test (" + page.full + ")")));
  }

  function draw() {
    if (!page.available) {
      $("panel").replaceChildren(el("p", { class: "empty" }, el("strong", {}, "The model test runs in MIA's phone app."), ""));
      return;
    }
    $("panel").replaceChildren(runner(), ...page.models.map(model));
    clearTimeout(timer);
    keepAwake(busy());
    if (busy()) timer = setTimeout(async () => { try { page = await MIA.modelTest(); draw(); } catch (e) { say(e.message); } }, 2000);
  }

  MIAShell.start(async () => {
    page = await MIA.modelTest();
    draw();
  }, { refreshOnChange: false });
})();
