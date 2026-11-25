/*
 * course.js — a course's labs (claude, 2026-11-25; docs/future/INTERACTIVE_LABS_PLAN.md, step 3).
 * Renders MIA.course(course, lesson) (core/lab_page.py): the course map, the lab chosen in its parts (why, steps,
 * watch for, parts, wiring, the sketch), the board, and a serial monitor. Changes go through the action contract,
 * each approved: Start This Course (path.start), Flash This Lab (esplab.flash). Read The Board (MIA.courseRead)
 * reads the board's serial output for a few seconds and checks the lab from what it said. The Simulator section,
 * building along with MIA, is web/labsim.js. A course with scenario drills (core/drills.py) shows them as Drills.
 * Formatting only.
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
  // replaceChildren with the nulls left out (the DOM's own writes a null as the text "null"; el() skips them).
  const fill = (node, ...kids) => node.replaceChildren(...kids.flat().filter((k) => k != null));
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
      if (lab.circuit && window.MIALabSim) parts.push(MIALabSim.render(course, lab));
      parts.push(section("The sketch",
        el("div", { class: "row-buttons" },
          MIAShell.copyButton(lab.code, "Copy The Sketch", "btn btn-ghost btn-small"),
          MIAShell.copyButton(lab.ini, "Copy The Project Settings", "btn btn-ghost btn-small")),
        lab.libs && lab.libs.length ? el("p", { class: "dim" }, "Libraries: " + lab.libs.join(", ")) : null,
        el("pre", { class: "crs-code" }, lab.code)));
      parts.push(bench(page));
    }
    if (page.drills && page.drills.length) parts.push(drills(page.drills));
    if (page.next) parts.push(section("What's next", el("p", {}, page.next)));
    return parts;
  }

  // Drills (core/drills.py): a situation and its decisions in order; a pick shows its verdict and why (core's), then
  // the next question; at the end, how many were the best call. Practice only: nothing is kept.
  function drills(list) {
    const box = el("div", { class: "drill-box" });
    const verdictWord = { best: "Right.", fine: "Close.", wrong: "Not that one." };
    function run(d) {
      let n = 0, right = 0;
      function ask() {
        const q = d.questions[n];
        const feedback = el("div", { class: "drill-feedback", "aria-live": "polite" });
        const next = el("button", { type: "button", class: "btn btn-amber", hidden: true }, n + 1 < d.questions.length ? "Next Question" : "See How It Went");
        const buttons = q.choices.map((c, i) => el("button", { type: "button", class: "drill-choice", onclick: () => {
          buttons.forEach((b, j) => { b.disabled = true; b.classList.add(q.choices[j].verdict); });
          buttons[i].classList.add("picked");
          if (c.verdict === "best") right += 1;
          const best = q.choices.find((x) => x.verdict === "best");
          fill(feedback, el("p", { class: "drill-" + c.verdict }, el("strong", {}, verdictWord[c.verdict] + " "), c.why),
            c.verdict === "best" ? null : el("p", { class: "dim" }, "Best: " + best.text + ". " + best.why));
          next.hidden = false;
          next.focus();
        } }, "ABCD"[i] + ") " + c.text));
        next.onclick = () => { n += 1; if (n < d.questions.length) ask(); else done(); };
        fill(box, el("h3", {}, d.title), n === 0 ? el("p", {}, d.situation) : null,
          el("p", { class: "dim" }, "Question " + (n + 1) + " of " + d.questions.length),
          el("p", { class: "drill-ask" }, q.ask), el("div", { class: "drill-choices" }, buttons), feedback,
          el("div", { class: "row-buttons" }, next));
      }
      function done() {
        const all = right === d.questions.length;
        fill(box, el("h3", {}, d.title),
          el("p", {}, all ? "Every call the best one." : right + " of " + d.questions.length + " best: the lesson behind it is worth a read again."),
          el("p", { class: "dim" }, "A drill is practice; the real thing is the course's own check."),
          el("div", { class: "row-buttons" }, el("button", { type: "button", class: "btn btn-ghost", onclick: pickOne }, "Another Drill")));
      }
      ask();
    }
    function pickOne() {
      box.replaceChildren(el("div", { class: "drill-list" }, list.map((d) => el("button", { type: "button", class: "glass cl-subject drill-pick", onclick: () => run(d) },
        el("span", {}, d.title), el("span", { class: "cl-n" }, d.questions.length + " decisions")))));
    }
    pickOne();
    return section("Drills", el("p", { class: "dim" }, "Practise the decisions before you need them: a situation, " +
      "a few calls in order, each judged with why. Or by voice: \"give me a survival drill\"."), box);
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
    fill($("strip"),
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
    fill($("panel"), panel);
  }, { refreshOnChange: true });
})();
