/*
 * course.js — a course's labs (claude, 2026-11-25; docs/future/INTERACTIVE_LABS_PLAN.md, step 3).
 * Renders MIA.course(course, lesson) (core/lab_page.py): the course map, the lab chosen in its parts (why, steps,
 * watch for, parts, wiring, the sketch), the board, and a serial monitor. Changes go through the action contract,
 * each approved: Start This Course (path.start), Flash This Lab (esplab.flash). Read The Board (MIA.courseRead)
 * reads the board's serial output for a few seconds and checks the lab from what it said. Formatting only.
 */
(function () {
  "use strict";
  const { el } = MIAShell;
  const $ = (id) => document.getElementById(id);
  const query = new URLSearchParams(location.search);
  const course = query.get("course") || "esp32";
  let lesson = query.get("lesson") || "";
  let monitor = "";  // the board's last output, kept while the page is open

  const section = (title, ...body) =>
    el("section", { class: "glass money-section" }, el("div", { class: "sect" }, el("h2", {}, title)), ...body);
  const list = (items, ordered) => el(ordered ? "ol" : "ul", { class: "crs-list" }, items.map((t) => el("li", {}, t)));
  const checkRow = (c) => el("div", { class: "crs-check" + (c.passed ? " passed" : "") }, (c.passed ? "✓ " : "○ ") + c.what);

  // Choosing a lab: the address keeps it (so a reload or a link lands on it), and the page is read again.
  function go(id) {
    lesson = id;
    monitor = "";
    const url = new URL(location.href);
    url.searchParams.set("lesson", id);
    history.replaceState(null, "", url);
    MIAShell.refresh();
  }

  function map(page) {
    return el("div", { class: "glass crs-map" }, page.stages.map((s) => el("div", { class: "crs-stage " + s.state },
      el("div", { class: "crs-stage-head" }, (s.state === "done" ? "✓ " : "") + s.number + ". " + s.name),
      el("div", { class: "crs-stage-sub" }, s.builds),
      s.lessons.map((l) => el("button", { type: "button", class: "crs-lesson" + (l.id === page.lab.id ? " on" : ""),
        onclick: () => go(l.id), "aria-current": l.id === page.lab.id ? "page" : null }, l.title)),
      s.checks.map(checkRow))));
  }

  function wiring(lab) {
    if (!lab.wiring || !lab.wiring.length) return el("p", { class: "dim" }, "Nothing to wire for this one.");
    return el("table", { class: "crs-wiring" },
      el("thead", {}, el("tr", {}, el("th", {}, "From"), el("th", {}, "To"))),
      el("tbody", {}, lab.wiring.map(([a, b]) => el("tr", {}, el("td", {}, a), el("td", {}, b)))));
  }

  // The bench: the board found, Flash This Lab, and the serial monitor with Read The Board and what it checked.
  function bench(page) {
    const b = page.board || {};
    const lab = page.lab;
    const status = b.ready ? "Your ESP32 is on " + b.port + (b.description ? " (" + b.description + ")" : "") + "."
      : (b.missing || "Plug in your ESP32.");
    const flash = el("button", { type: "button", class: "btn btn-amber", disabled: page.started ? null : true,
      onclick: () => MIAShell.act({ kind: "esplab.flash", params: { lesson: lab.id } }) }, "Flash This Lab");
    const out = el("pre", { class: "crs-monitor", "aria-live": "polite" }, monitor || "The board's output shows here.");
    const said = el("p", { class: "dim" });
    const read = el("button", { type: "button", class: "btn btn-ghost", disabled: page.started ? null : true }, "Read The Board");
    read.onclick = async () => {
      read.disabled = true;
      read.textContent = "Reading…";
      try {
        const got = await MIA.courseRead(course, lab.id, 8);
        monitor = got.serial || "(nothing came)";
        out.textContent = monitor;
        said.textContent = got.said;
        if ((got.results || []).some((r) => r.passed)) MIAShell.refresh();
      } catch (e) {
        MIAShell.say(e.message);
      } finally {
        read.disabled = false;
        read.textContent = "Read The Board";
      }
    };
    return section("On the bench",
      el("p", { class: "dim" }, status),
      lab.secrets ? el("p", { class: "dim" }, "This lab joins your Wi-Fi: type its name and password into the lab's " +
        "src/secrets.h yourself (MIA never does), then flash it.") : null,
      el("div", { class: "row-buttons" }, flash, read),
      out, said,
      lab.checks && lab.checks.length ? el("div", { class: "crs-checks" }, lab.checks.map(checkRow)) : null);
  }

  function labPanel(page) {
    const lab = page.lab;
    const parts = [
      section(lab.title,
        lab.why ? el("p", { class: "crs-why" }, lab.why) : null,
        el("h3", {}, "Do it"), list(lab.steps, true),
        lab.watch && lab.watch.length ? el("h3", {}, "Watch for") : null,
        lab.watch && lab.watch.length ? list(lab.watch) : null),
    ];
    if (lab.code) {
      parts.push(section("Parts and wiring", list(lab.parts), wiring(lab)));
      parts.push(section("The sketch",
        el("div", { class: "row-buttons" },
          MIAShell.copyButton(lab.code, "Copy The Sketch", "btn btn-ghost btn-small"),
          MIAShell.copyButton(lab.ini, "Copy The Project Settings", "btn btn-ghost btn-small")),
        lab.libs && lab.libs.length ? el("p", { class: "dim" }, "Libraries: " + lab.libs.join(", ")) : null,
        el("pre", { class: "crs-code" }, lab.code)));
      parts.push(bench(page));
    }
    if (page.next) parts.push(section("What's next", el("p", {}, page.next)));
    return parts;
  }

  MIAShell.start(async () => {
    const page = await MIA.course(course, lesson);
    if (!page.available) {
      $("strip").replaceChildren();
      $("map").replaceChildren();
      $("panel").replaceChildren(el("p", { class: "empty" }, el("strong", {}, page.why || "This course isn't here.")));
      return;
    }
    $("icon").textContent = page.course.icon;
    $("name").textContent = page.course.name;
    $("about").textContent = page.course.about;
    document.title = page.course.name + " — MIA";
    const passed = page.stages.reduce((n, s) => n + s.checks.filter((c) => c.passed).length, 0);
    const checks = page.stages.reduce((n, s) => n + s.checks.length, 0);
    const current = (page.stages.find((s) => s.state === "current") || page.stages[page.stages.length - 1]).number;
    const cell = (cls, n, t) => el("div", { class: "cell " + cls }, el("span", { class: "n" }, n), el("span", { class: "t" }, t));
    $("strip").replaceChildren(
      cell("ok", current + "/" + page.stages.length, "Stage"),
      cell(passed ? "ok" : "soon", passed + "/" + checks, "Checks passed"),
      page.board ? cell(page.board.ready ? "ok" : "soon", page.board.ready ? "Ready" : "Not yet", "Board") : null);
    $("map").replaceChildren(map(page));
    const panel = labPanel(page);
    if (!page.started) {
      panel.unshift(el("section", { class: "glass money-section" },
        el("p", {}, "Start " + page.course.name + ": about " + page.course.minutes_a_day + " minutes a day, " +
          page.course.days_a_week + " days a week. Flashing and checks open once it's started."),
        el("div", { class: "row-buttons" }, el("button", { type: "button", class: "btn btn-amber",
          onclick: () => MIAShell.act({ kind: "path.start", params: { path: page.course.id } }) }, "Start This Course"))));
    }
    $("panel").replaceChildren(...panel);
  }, { refreshOnChange: true });
})();
