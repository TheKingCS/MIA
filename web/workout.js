/*
 * workout.js — the Workout screen (claude, 2026-10-06, DEC-0017/0018).
 * Renders MIA.workout() (core/web_screens.py): log a session right on the
 * page (an exercise, reps, sets, weight, how long, notes), the latest entry,
 * today's daily mission and streak, exercises, history, progress and Personal
 * Bests (lifts and skill bests). Templates are gone (Zac, 2026-10-16): the
 * plan's training days are the routines you repeat. Every change is a
 * workout action (core/workout_actions.py). Formatting only here.
 *
 * 2026-10-14 (DEC-0020, Muse's H-0028): Today (the plan's training as
 * steps to tick, the practice timer with its "new best" moment, rest days
 * that count) and Progress ("is it working?": the sentence, the numbers,
 * the weight line) from MIA.fitness() (core/web_fitness.py). The old
 * Personal records are "Personal Bests" (Zac, 2026-10-16). My plan is plan.html.
 *
 * 2026-11-07 (DEC-0113, the design canvas): Today leads with one big Start;
 * a live session takes the whole screen in three modes, Active (one set in
 * focus, the count large with how it was counted), Rest (a draining ring)
 * and Done (planned against done), with 56 px targets. Tuck it away and a
 * bar brings it back.
 */
(function () {
  "use strict";
  const { el, act, form } = MIAShell;
  const $ = (id) => document.getElementById(id);
  const TABS = [["today", "Today"], ["progress", "Progress"], ["log", "Log Session"], ["exercises", "Exercises"],
    ["history", "History"], ["lifts", "Personal Bests"]];
  let page = null;
  let fit = null;  // MIA.fitness() (null where fitness isn't set up)
  let tab = TABS.some(([t]) => t === location.hash.slice(1)) ? location.hash.slice(1) : null;
  const timer = { skill: null, step: "", started: 0, elapsed: 0, running: false, tick: null };  // survives a live refresh
  let draft = {};  // what's typed in the log form survives a live refresh

  const btn = (label, cls, onclick, type) => el("button", { type: type || "button", class: "btn " + cls, onclick }, label);
  const buttons = (...list) => el("div", { class: "row-buttons" }, list.filter(Boolean));
  const day = (iso) => iso ? new Date(iso + "T00:00:00").toLocaleDateString(undefined, { weekday: "short", month: "short", day: "numeric" }) : "";
  const lists = () => ({ exercises: page.exercises.map((e) => ({ id: e.id, name: e.name })) });
  const section = (title, actions, ...body) =>
    el("section", { class: "glass money-section" }, el("div", { class: "sect" }, el("h2", {}, title), actions), ...body);

  async function add(key, title) {
    const v = await form(title, page.forms[key].fields, {});
    if (v) act({ kind: key + ".add", params: v });
  }
  async function edit(key, row) {
    const spec = page.forms[key];
    const v = await form("Edit " + spec.noun, spec.fields, row.values);
    if (v) act({ kind: key + ".edit", params: Object.assign({ [spec.id_param]: row.id }, v) });
  }
  const del = (key, row) => act({ kind: key + ".delete", params: { [page.forms[key].id_param]: row.id } });

  // ------------------------------------------------------------ the inline log form (the concept's)
  function input(f) {
    const id = "log-" + f.name;
    let node;
    if (f.type === "pick") {
      node = el("select", { id, name: f.name }, el("option", { value: "" }, "Pick an exercise"),
        lists()[f.options[0]].map((x) => el("option", { value: x.id }, x.name)));
    } else if (f.type === "textarea") {
      node = el("textarea", { id, name: f.name, rows: "2", placeholder: "How did it feel?" });
    } else {
      const numeric = f.type !== "date";
      node = el("input", { id, name: f.name, type: numeric ? "number" : "date", min: numeric ? "0" : null,
        step: f.type === "int" ? "1" : numeric ? "any" : null, inputmode: numeric ? "decimal" : null });
      if (f.type === "int" && f.name === "sets") node.value = "1";
    }
    if (draft[f.name] != null) node.value = draft[f.name];
    node.addEventListener("input", () => { draft[f.name] = node.value; });
    return el("label", { class: "form-row log-" + f.name, for: id }, el("span", {}, f.label), node);
  }

  function logCard() {
    const spec = page.forms.log;
    const formNode = el("form", { class: "log-form", onsubmit: async (e) => {
      e.preventDefault();
      const params = {};
      new FormData(formNode).forEach((v, k) => { if (v !== "") params[k] = v; });
      const done = await act({ kind: "workout.log", params });
      if (done) { draft = {}; formNode.reset(); }
    } }, spec.fields.map(input),
    el("div", { class: "row-buttons" }, btn("Save session", "btn-green", null, "submit")));
    return section("Log session", null,
      page.exercises.length ? formNode
        : el("p", { class: "empty" }, el("strong", {}, "Add an exercise first."), btn("Add exercise", "btn-amber", () => add("exercise", "Add an exercise"))));
  }

  function latestCard() {
    const s = page.latest;
    return section("Latest entry", null, s
      ? el("div", { class: "latest" }, el("div", { class: "row-title" }, s.summary),
        el("div", { class: "row-sub" }, [day(s.date), s.minutes ? s.minutes + " min" : null].filter(Boolean).join(" · ")),
        s.notes ? el("p", { class: "dim" }, "“" + s.notes + "”") : null)
      : el("p", { class: "dim" }, "Nothing logged yet."));
  }

  function missionCard() {
    const list = page.daily_missions;
    if (!list.length) return null;
    return section("Daily mission", null, list.map((m) => {
      const pct = Math.min(100, Math.round((m.progress / m.target) * 100));
      return el("div", { class: "daily-mission" },
        el("div", { class: "row-title" }, (m.done ? "✓ " : "") + m.name),
        el("div", { class: "bar", role: "progressbar", "aria-valuenow": String(pct), "aria-valuemin": "0", "aria-valuemax": "100" },
          el("div", { class: "bar-fill", style: "width:" + pct + "%" })),
        el("div", { class: "row-sub" }, m.progress + " / " + m.target + (m.streak ? " · 🔥 " + m.streak + "-day streak" : "")));
    }));
  }

  function sessionRow(s) {
    return el("div", { class: "row money-row" },
      el("div", {}, el("div", { class: "row-title" }, s.template || s.summary),
        el("div", { class: "row-sub" }, [day(s.date), s.template && s.summary !== s.template ? s.summary : null, s.minutes ? s.minutes + " min" : null, s.notes]
          .filter(Boolean).join(" · "))),
      buttons(btn("Remove", "btn-ghost", () => act({ kind: "workout.delete", params: { session_id: s.id } }))));
  }

  function spark(points) {
    if (points.length < 2) return null;
    const ws = points.map((p) => p[1]);
    const max = Math.max(...ws) || 1, min = Math.min(...ws);
    const span = max - min || 1;
    const d = points.map((p, i) => (i ? "L" : "M") + (i * 100 / (points.length - 1)).toFixed(1) + " " + (36 - ((p[1] - min) / span) * 32).toFixed(1)).join(" ");
    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.setAttribute("viewBox", "0 0 100 40");
    svg.setAttribute("class", "spark");
    svg.setAttribute("aria-hidden", "true");
    const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
    path.setAttribute("d", d);
    svg.append(path);
    return svg;
  }

  // ------------------------------------------------------------ Today and Progress (DEC-0020, H-0028)
  const svgEl = (tag, attrs) => { const n = document.createElementNS("http://www.w3.org/2000/svg", tag);
    for (const [k, v] of Object.entries(attrs || {})) n.setAttribute(k, v); return n; };
  const plural = (n, w) => n + " " + w + (n === 1 ? "" : "s");
  const g = (v, unit) => v == null ? "—" : (Math.round(v * 10) / 10).toLocaleString() + (unit || "");
  const planLink = () => el("a", { class: "btn btn-ghost", href: "plan.html?from=" + encodeURIComponent("workout.html#" + tab) }, "My plan");
  // Import plan: My plan with "Paste a plan" already open (plan.js reads ?import=1).
  const importLink = () => el("a", { class: "btn btn-amber", href: "plan.html?from=" + encodeURIComponent("workout.html#" + tab) + "&import=1" }, "Import plan");
  const secs = (ms) => Math.floor(ms / 1000);
  const clock = (sec) => Math.floor(sec / 60) + ":" + String(sec % 60).padStart(2, "0");

  function celebrate(title, line) {
    const node = el("div", { class: "celebrate", role: "status" }, el("div", { class: "celebrate-card" },
      el("div", { class: "celebrate-burst", "aria-hidden": "true" }, "🏆"), el("strong", {}, title), el("span", {}, line)));
    node.addEventListener("click", () => node.remove());
    document.body.append(node);
    setTimeout(() => node.remove(), 4200);
  }

  // The practice timer: one card per skill. Start, stop, then log what it was:
  // a hold (seconds, toward a step's best) or practice time (minutes).
  function timerTick() {
    const node = document.getElementById("timer-readout");
    if (node) node.textContent = clock(secs(timer.elapsed + (timer.running ? Date.now() - timer.started : 0)));
  }
  function startStop(skill) {
    if (timer.running) {
      timer.elapsed += Date.now() - timer.started; timer.running = false; clearInterval(timer.tick);
    } else {
      if (timer.skill !== skill) timer.elapsed = 0;
      timer.skill = skill; timer.started = Date.now(); timer.running = true;
      clearInterval(timer.tick); timer.tick = setInterval(timerTick, 250);
    }
    draw();
  }
  async function logPractice(sk, mode, stepName) {
    const seconds = secs(timer.elapsed);
    const params = { skill: sk.skill, step: stepName || "" };
    if (mode === "hold") params.seconds = seconds; else params.minutes = Math.max(1, Math.round(seconds / 60));
    const step = sk.steps.find((x) => x.name === stepName);
    const best = step ? step.best_seconds : sk.best_seconds;
    const done = await act({ kind: "fitness.skill", params });
    if (!done) return;
    timer.skill = null; timer.elapsed = 0; timer.step = ""; draw();
    if (mode === "hold" && (best == null || seconds > best)) {
      celebrate("New best: " + plural(seconds, "second"), (stepName || sk.skill) + (best != null ? " · was " + best + " s" : " · your first hold"));
    }
  }

  // Reps (Muse, H-0031/H-0033): a step with a rep target is logged as a count, with or without the timer.
  async function logReps(sk, stepName) {
    const repSteps = sk.steps.filter((x) => x.target_reps);
    const v = await form("Log reps: " + sk.skill, [
      { name: "step", label: "Step", type: "choice", options: repSteps.length ? repSteps.map((x) => x.name) : [""], default: stepName || (repSteps[0] || {}).name },
      { name: "reps", label: "Reps", type: "int", required: true }]);
    if (!v) return;
    const step = sk.steps.find((x) => x.name === v.step);
    const best = step ? step.best_reps : null;
    const done = await act({ kind: "fitness.skill", params: { skill: sk.skill, step: v.step, reps: v.reps } });
    if (!done) return;
    if (timer.skill === sk.skill) { timer.skill = null; timer.elapsed = 0; timer.step = ""; draw(); }
    const n = Number(v.reps);
    if (n && (best == null || n > best)) celebrate("New best: " + plural(n, "rep"), (v.step || sk.skill) + (best != null ? " · was " + best : " · your first count"));
  }

  function skillCard(sk) {
    const mine = timer.skill === sk.skill;
    const shown = mine ? secs(timer.elapsed + (timer.running ? Date.now() - timer.started : 0)) : 0;
    const hasReps = sk.steps.some((x) => x.target_reps);
    const best = (x) => x.target_reps ? (x.best_reps ? " (best " + x.best_reps + ")" : "") : (x.best_seconds ? " (best " + x.best_seconds + " s)" : "");
    const pick = el("select", { "aria-label": "Which step", onchange: () => { timer.step = pick.value; draw(); } },
      el("option", { value: "" }, "General practice"),
      sk.steps.map((x) => el("option", { value: x.name, selected: timer.step === x.name ? true : null }, x.name + best(x))));
    const chosen = sk.steps.find((x) => x.name === (mine ? timer.step : ""));
    const minutesPct = sk.daily_minutes ? Math.min(100, Math.round((100 * sk.minutes_today) / sk.daily_minutes)) : 0;
    // After stopping: the modes that fit the chosen step (a rep step logs a count; otherwise a hold or practice time).
    const modes = chosen && chosen.target_reps
      ? [btn("Log reps", "btn-green", () => logReps(sk, chosen.name)),
         btn("Log " + plural(Math.max(1, Math.round(shown / 60)), "min") + " practice", "btn-ghost", () => logPractice(sk, "minutes", pick.value))]
      : [btn("Log a " + shown + " s hold", "btn-green", () => logPractice(sk, "hold", pick.value)),
         btn("Log " + plural(Math.max(1, Math.round(shown / 60)), "min") + " practice", "btn-ghost", () => logPractice(sk, "minutes", pick.value))];
    return el("article", { class: "glass practice-card" },
      el("div", { class: "asset-head" }, el("h3", {}, sk.skill),
        sk.best_seconds ? el("span", { class: "chip chip-ok" }, "Best hold " + sk.best_seconds + " s") : null),
      sk.daily_minutes ? el("div", { class: "row-sub" }, g(sk.minutes_today) + " of " + sk.daily_minutes + " min today",
        el("div", { class: "bar" }, el("div", { class: "bar-fill", style: "width:" + minutesPct + "%" }))) : null,
      sk.practice.length ? el("p", { class: "dim" }, sk.practice.join(" · ")) : null,
      el("div", { class: "timer-readout", id: mine ? "timer-readout" : null, "aria-live": "off" }, clock(shown)),
      el("div", { class: "row-buttons" },
        btn(mine && timer.running ? "Stop" : mine && shown ? "Keep going" : "Start", mine && timer.running ? "btn-amber" : "btn-green", () => startStop(sk.skill)),
        mine && !timer.running && shown ? btn("Clear", "btn-ghost", () => { timer.skill = null; timer.elapsed = 0; timer.step = ""; draw(); }) : null,
        hasReps && !(mine && (timer.running || shown)) ? btn("Log reps", "btn-ghost", () => logReps(sk)) : null),
      mine && !timer.running && shown ? el("div", { class: "timer-log" }, pick, el("div", { class: "row-buttons" }, modes)) : null);
  }

  function trainingCard() {
    const t = fit.today;
    if (!t.training) {
      return section(t.rest_day ? "Rest day" : "Today's training", buttons(planLink(), importLink()), el("p", { class: "rest-note" }, t.rest_day
        ? "Rest day. Recovery counts: it's part of the plan, not a miss."
        : "No training plan yet. Set your training days and what each one is in My plan, and today's workout shows up here as steps."));
    }
    const steps = t.training.steps, done = steps.filter((x) => x.done).length;
    const all = done === steps.length && steps.length;
    return section("Today: " + t.training.name, buttons(planLink(), importLink()),
      el("p", { class: "dim" }, steps.length ? done + " of " + plural(steps.length, "step") + " done" : "No steps in this day yet."),
      el("ol", { class: "train-steps" }, steps.map((x, i) => el("li", { class: x.done ? "done" : "" },
        el("button", { type: "button", class: "step-tick", "aria-pressed": String(x.done), disabled: x.done ? true : null,
          "aria-label": "Step " + (i + 1) + " done: " + x.name, onclick: () => act({ kind: "fitness.step", params: { step: i + 1 } }) }, x.done ? "✓" : String(i + 1)),
        el("span", {}, el("strong", {}, x.name),
          el("span", { class: "dim" }, " " + [x.sets && x.reps ? x.sets + " × " + x.reps : x.sets > 1 ? plural(x.sets, "set") : null, x.hold_seconds ? x.hold_seconds + " s hold" : null].filter(Boolean).join(" · ")))))),
      !fit.session && !all ? startBlock() : null,
      all ? el("span", { class: "chip chip-ok" }, "✓ Workout complete") : btn("✓ Mark Done Without a Session", "btn-ghost", () => act({ kind: "fitness.training_done", params: {} })));
  }

  // ---------------------------------------------------------------- the live session (DEC-0055)
  // core/training_session.py: the one workout going, shared with voice and the glasses. MIA counts the pace
  // here (Zac: "count the pace"): spoken where this browser can speak, a tick where it can't; the phone app can
  // hand its own voice in as window.MIAPhoneVoice.say. The count is confirmed before it's saved.
  const live = { tick: null, beat: null, count: 0, taps: 0, hidden: false };

  function sayNow(text) {
    try { if (window.MIAPhoneVoice && MIAPhoneVoice.say) { MIAPhoneVoice.say(String(text)); return; } } catch (e) { /* next */ }
    try {
      if (window.speechSynthesis) { speechSynthesis.cancel(); speechSynthesis.speak(new SpeechSynthesisUtterance(String(text))); return; }
    } catch (e) { /* next */ }
    try {  // no voice here: a short tick on each beat
      const ctx = live.audio || (live.audio = new (window.AudioContext || window.webkitAudioContext)());
      const o = ctx.createOscillator(), g = ctx.createGain();
      o.connect(g); g.connect(ctx.destination); g.gain.value = 0.08; o.start(); o.stop(ctx.currentTime + 0.06);
    } catch (e) { /* silent is fine */ }
  }

  function stopCounting() { if (live.beat) clearInterval(live.beat); live.beat = null; }

  async function confirmCount(n, counted) {
    const hold = !!n.hold_seconds;
    const v = await form(hold ? "How long did you hold it?" : "How many did you get?",
      [{ name: hold ? "seconds" : "reps", label: hold ? "Seconds" : "Reps", type: "int", required: true, options: [], default: live.count || null },
        ...(fit.child || hold ? [] : [{ name: "weight", label: "Weight (optional)", type: "amount", required: false, options: [], default: null }])], {});
    if (v) act({ kind: "training.set", params: Object.assign({ counted }, v) });
  }

  function countWithMe(n) {
    stopCounting();
    const hold = !!n.hold_seconds, goal = hold ? n.hold_seconds : (n.reps || 0), pace = hold ? 1 : (n.cadence_seconds || 2);
    live.count = 0;
    sayNow(hold ? "Hold. Go." : "Ready. Go.");
    live.beat = setInterval(() => {
      live.count += 1;
      const shown = $("count-now");
      if (shown) shown.textContent = String(live.count);
      if (!hold || live.count % 5 === 0 || (goal && live.count >= goal)) sayNow(live.count);
      if (goal && live.count >= goal) { stopCounting(); sayNow(hold ? "Time. Nice." : "That's " + goal + ". Nice."); confirmCount(n, "cadence"); }
    }, pace * 1000);
    draw();
  }

  function restTicker(s) {
    if (live.tick) clearInterval(live.tick);
    live.tick = null;
    if (s.status !== "resting" || s.rest_left == null) return;
    const ends = Date.now() + s.rest_left * 1000;
    live.tick = setInterval(async () => {
      const left = Math.max(0, Math.ceil((ends - Date.now()) / 1000)), shown = $("rest-left"), ringNode = $("rest-ring");
      if (shown) shown.textContent = Math.floor(left / 60) + ":" + String(left % 60).padStart(2, "0");
      if (ringNode) {
        const c = parseFloat(ringNode.dataset.c), total = parseFloat(ringNode.dataset.total) || 1;
        ringNode.setAttribute("stroke-dashoffset", (c * (1 - Math.max(0, Math.min(1, left / total)))).toFixed(1));
      }
      if (left === 10) sayNow("Ten seconds.");
      if (left === 0) {
        clearInterval(live.tick); live.tick = null;
        sayNow("Rest's over. " + (s.now ? s.now.name + ", set " + s.now.set + "." : ""));
        fit = await MIA.fitness().catch(() => fit);
        draw();
      }
    }, 1000);
  }

  // ---------------------------------------------------------------- the canvas's modes (DEC-0113)
  // Today shows one big Start; once a session is going, Active / Rest / Done take the whole screen: one thing in
  // focus, 56 px+ targets for sweaty hands, how each count was made beside it (never "verified").
  const HOW = { said: "Said", cadence: "MIA Pace", told: "Told", tapped: "Tapped" };
  const how = (h) => HOW[h] || "Told";

  function startBlock() {
    return el("div", { class: "wk-start" },
      el("button", { type: "button", class: "btn-big", onclick: () => act({ kind: "training.start", params: {} }) }, "▶ Start Workout"),
      el("p", { class: "dim" }, "Or say “MIA, start my workout.” She counts the pace with you, starts your rest by itself, and logs what you actually did."));
  }

  function sessionBar() {  // the session is going but its screen is tucked away
    const s = fit.session;
    return el("button", { type: "button", class: "glass wk-bar", onclick: () => { live.hidden = false; draw(); } },
      el("span", { class: "kind accent" }, s.status === "resting" ? "Resting" : s.status === "paused" ? "Paused" : "Workout Going"),
      el("span", {}, s.title), el("span", { class: "dim" }, "Open"));
  }

  function ring(left, total) {  // the rest draining; the number stays for reduced motion and screen readers
    const r = 124, c = 2 * Math.PI * r, frac = total ? Math.max(0, Math.min(1, left / total)) : 0;
    const svg = svgEl("svg", { viewBox: "0 0 280 280", class: "wk-ring", "aria-hidden": "true" });
    svg.append(svgEl("circle", { cx: 140, cy: 140, r, class: "wk-ring-track" }),
      svgEl("circle", { cx: 140, cy: 140, r, class: "wk-ring-fill", "stroke-dasharray": c.toFixed(1),
        "stroke-dashoffset": (c * (1 - frac)).toFixed(1), id: "rest-ring", "data-c": c.toFixed(1), "data-total": String(total || 0) }));
    const mm = (n) => Math.floor(n / 60) + ":" + String(n % 60).padStart(2, "0");
    return el("div", { class: "wk-ring-wrap", role: "timer", "aria-label": left + " seconds of rest left" }, svg,
      el("div", { class: "wk-ring-text" }, el("span", { class: "wk-ring-n", id: "rest-left" }, mm(left)),
        el("span", { class: "wk-label" }, "of " + mm(total || 0))));
  }

  function liveMode() {
    const s = fit.session, n = s.now || {}, resting = s.status === "resting", paused = s.status === "paused";
    const done = s.status === "complete", counting = !!live.beat;
    const clock = Math.floor(s.elapsed / 3600) + ":" + String(Math.floor(s.elapsed / 60) % 60).padStart(2, "0") + ":" + String(s.elapsed % 60).padStart(2, "0");
    const top = el("header", { class: "wk-top" },
      done || resting ? el("button", { type: "button", class: "btn btn-ghost wk-icon", "aria-label": "Hide the workout screen", onclick: () => { live.hidden = true; draw(); } }, "✕")
        : el("button", { type: "button", class: "btn btn-ghost wk-icon", "aria-label": paused ? "Resume" : "Pause",
          onclick: () => { stopCounting(); act({ kind: paused ? "training.resume" : "training.pause", params: {} }); } }, paused ? "▶" : "❚❚"),
      el("div", { class: "wk-clock" }, el("span", { class: "wk-label" }, resting ? "Rest" : done ? "Done" : paused ? "Paused" : "Session"),
        el("span", { class: "wk-mono" }, clock)),
      el("span", { class: "mia-orb", "data-state": counting || (!resting && !done && !paused) ? "listening" : "idle",
        role: "img", "aria-label": "MIA is listening for your count" }));
    if (done) {
      return el("div", { class: "wk-mode", role: "dialog", "aria-label": "Workout done" }, top,
        el("div", { class: "wk-done-head" }, el("span", { class: "wk-label ok" }, "Every Set Done"),
          el("h1", {}, s.title + ", done."),
          el("span", { class: "wk-mono dim" }, Math.round(s.elapsed / 60) + " min · " + s.steps.reduce((t, x) => t + x.done, 0) + " sets · " + s.steps.length + " exercises")),
        el("section", { class: "glass wk-table" },
          el("div", { class: "wk-table-head" }, el("span", { class: "wk-label" }, "Planned → Done"), el("span", { class: "wk-label" }, "How Counted")),
          ...s.steps.map((x) => el("div", { class: "wk-row" },
            el("div", {}, el("div", {}, x.name), el("div", { class: "wk-mono dim" }, x.target + " × " + x.sets + " → " + (x.counts.join(" · ") || (x.skipped ? "skipped" : "none")))),
            el("span", { class: "kind" }, [...new Set((x.how || []).map(how))].join(", ") || "—"))),
          s.steps.some((x) => x.counts.some((c, i) => typeof c === "number" && c < (x.target ? parseInt(x.target, 10) || 0 : 0)))
            ? el("p", { class: "dim" }, "A short set is still a set. It counts.") : null),
        el("div", { class: "wk-actions" },
          el("button", { type: "button", class: "btn-big", onclick: () => { stopCounting(); act({ kind: "training.finish", params: {} }); } }, "Finish and Log It"),
          el("p", { class: "dim" }, "XP, new bests and missions are counted when it's logged.")));
    }
    if (resting) {
      return el("div", { class: "wk-mode", role: "dialog", "aria-label": "Rest" }, top,
        ring(s.rest_left || 0, s.rest_total || s.rest_left || 0),
        n.last != null ? el("p", { class: "wk-logged" }, "Last set: " + n.last + " · counted " + how(n.last_counted).toLowerCase()) : null,
        el("section", { class: "glass wk-next" }, el("span", { class: "wk-label atmo" }, "Up Next"),
          el("h2", {}, (n.name || s.next || "") + (n.set ? " · Set " + n.set + " of " + n.sets : "")),
          el("span", { class: "wk-mono dim" }, [n.target, n.weight ? "weight " + n.weight : null].filter(Boolean).join(" · "))),
        el("div", { class: "wk-actions" },
          el("button", { type: "button", class: "btn-big", onclick: () => act({ kind: "training.skip_rest", params: {} }) }, "Skip Rest"),
          el("button", { type: "button", class: "btn-big quiet", onclick: () => act({ kind: "training.rest_more", params: {} }, { quick: true }) }, "+30 s"),
          el("p", { class: "dim" }, "A tone plays at zero. Say “skip rest” or “thirty more seconds” anytime.")));
    }
    const ex = s.steps.findIndex((x) => x.name === n.name);
    const shown = counting ? live.count : live.taps || 0;
    const goal = n.hold_seconds || n.reps || 0;
    return el("div", { class: "wk-mode", role: "dialog", "aria-label": "Active set" }, top,
      el("section", { class: "surface-focus wk-focus" },
        el("div", { class: "wk-focus-head" }, el("span", { class: "wk-label atmo" }, "Exercise " + (ex + 1) + " of " + s.steps.length),
          n.weight ? el("span", { class: "wk-label" }, "Weight " + n.weight) : null),
        el("h1", {}, n.name || ""),
        el("div", { class: "wk-sets", "aria-label": "Set " + n.set + " of " + n.sets }, ...Array.from({ length: n.sets || 0 }, (_, i) =>
          el("span", { class: i < n.set - 1 ? "done" : i === n.set - 1 ? "now" : "" }))),
        el("span", { class: "dim" }, "Set " + n.set + " of " + n.sets + " · target " + n.target),
        el("div", { class: "wk-count", "aria-live": "polite" },
          el("span", { class: "wk-count-n", id: counting ? "count-now" : null }, String(shown)),
          goal ? el("span", { class: "wk-count-of" }, "/ " + goal) : null),
        el("span", { class: "kind" }, counting ? "Counting · MIA Pace" : live.taps ? "Counted · Tapped" : n.last_counted ? "Last · " + how(n.last_counted) : "Say each number"),
        s.next ? el("p", { class: "dim wk-caption" }, "Then: " + s.next) : null),
      el("div", { class: "wk-actions" },
        el("div", { class: "wk-pair" },
          counting ? el("button", { type: "button", class: "btn-big quiet", onclick: () => { stopCounting(); confirmCount(n, "cadence"); } }, "■ Stop Count")
            : el("button", { type: "button", class: "btn-big quiet", onclick: () => countWithMe(n) }, "Count With Me"),
          el("button", { type: "button", class: "btn-big quiet", onclick: () => { stopCounting(); live.taps = (live.taps || 0) + 1; draw(); } }, "+1 Rep")),
        el("button", { type: "button", class: "btn-big wk-done", onclick: () => {
          stopCounting(); const t = live.taps; live.taps = 0;
          if (t) { live.count = t; confirmCount(n, "tapped"); } else confirmCount(n, "told");
        } }, "Set Done"),
        el("div", { class: "wk-pair" },
          el("button", { type: "button", class: "btn btn-ghost", onclick: () => act({ kind: "training.skip", params: {} }) }, "Skip Exercise"),
          el("button", { type: "button", class: "btn btn-ghost", onclick: () => { stopCounting(); act({ kind: "training.finish", params: {} }); } }, "Finish Early")),
        el("p", { class: "dim" }, "Say “twelve”, “next set”, “pause”, “make that ten” or “I'm done”, here or on the glasses.")));
  }

  function sessionCard() {
    const s = fit.session;
    if (!s) { stopCounting(); restTicker({ status: "" }); return null; }
    restTicker(s);
    return live.hidden ? sessionBar() : null;
  }

  function todayView() {
    if (!fit) return [section("Today", null, el("p", { class: "dim" }, "Training plans aren't set up on this MIA."))];
    const missions = fit.missions.filter((m) => m.kind === "training" || m.kind === "week_workouts" || m.kind.startsWith("skill:"));
    return [
      sessionCard(),
      el("div", { class: "two-up" }, trainingCard(),
        section("Missions", null, missions.length ? el("div", { class: "rows" }, missions.map((m) => el("div", { class: "row money-row" },
          el("div", {}, el("div", { class: "row-title" }, m.icon + " " + m.name), el("div", { class: "row-sub" }, m.done + " of " + m.total + (m.cadence === "weekly" ? " this week" : ""))),
          m.status === "completed" ? el("span", { class: "chip chip-ok" }, "✓ Done") : null)))
          : el("p", { class: "dim" }, "Your plan's training and practice become missions here each day."))),
      fit.today.skills.length ? el("div", { class: "asset-grid practice-grid" }, fit.today.skills.map(skillCard)) : null,
    ];
  }

  // The weight line: each weigh-in (dots) and the 7-day average (the line), one axis.
  function weightChart(series, w) {
    // Drawn at the width it's shown at, so its text stays readable on a phone.
    const W = Math.round(Math.min(640, Math.max(300, ($("panel").clientWidth || 640) - 48))), H = Math.round(W * 0.42), L = 40, R = 10, T = 12, B = 24;
    const ys = series.flatMap((p) => [p.weight, p.average]).concat(w.target != null ? [w.target] : []);
    let lo = Math.min(...ys), hi = Math.max(...ys);
    const pad = Math.max(1, (hi - lo) * 0.15); lo -= pad; hi += pad;
    const t0 = new Date(series[0].date + "T00:00:00").getTime(), t1 = new Date(series[series.length - 1].date + "T00:00:00").getTime();
    const x = (iso) => L + (t1 === t0 ? (W - L - R) / 2 : ((new Date(iso + "T00:00:00").getTime() - t0) / (t1 - t0)) * (W - L - R));
    const y = (v) => T + (1 - (v - lo) / (hi - lo)) * (H - T - B);
    const svg = svgEl("svg", { viewBox: "0 0 " + W + " " + H, class: "weight-chart", role: "img",
      "aria-label": "Weight over time: latest " + g(w.latest) + " " + w.units + ", 7-day average " + g(w.average_7d) });
    for (let i = 0; i <= 3; i++) {
      const v = lo + ((hi - lo) * i) / 3;
      svg.append(svgEl("line", { x1: L, x2: W - R, y1: y(v), y2: y(v), class: "grid" }));
      const label = svgEl("text", { x: L - 6, y: y(v) + 4, class: "axis", "text-anchor": "end" }); label.textContent = Math.round(v); svg.append(label);
    }
    [series[0], series[series.length - 1]].forEach((p, i) => {
      const label = svgEl("text", { x: x(p.date), y: H - 6, class: "axis", "text-anchor": i ? "end" : "start" });
      label.textContent = day(p.date); svg.append(label);
    });
    if (w.target != null && w.target > lo && w.target < hi) {
      svg.append(svgEl("line", { x1: L, x2: W - R, y1: y(w.target), y2: y(w.target), class: "goal" }));
      const label = svgEl("text", { x: W - R, y: y(w.target) - 5, class: "axis goal-label", "text-anchor": "end" }); label.textContent = "goal " + w.target; svg.append(label);
    }
    if (series.length > 1) svg.append(svgEl("path", { class: "avg", d: series.map((p, i) => (i ? "L" : "M") + x(p.date).toFixed(1) + " " + y(p.average).toFixed(1)).join(" ") }));
    const tip = el("div", { class: "chart-tip", hidden: true });
    series.forEach((p) => {
      const dot = svgEl("circle", { cx: x(p.date), cy: y(p.weight), r: 4, class: "dot" });
      const hit = svgEl("circle", { cx: x(p.date), cy: y(p.weight), r: 14, class: "hit", tabindex: "0" });
      const show = () => { tip.hidden = false; tip.textContent = day(p.date) + ": " + p.weight + " " + w.units + " · avg " + p.average;
        tip.style.left = (100 * x(p.date) / W) + "%"; tip.style.top = (100 * y(p.weight) / H) + "%"; dot.classList.add("on"); };
      const hide = () => { tip.hidden = true; dot.classList.remove("on"); };
      hit.addEventListener("pointerenter", show); hit.addEventListener("focus", show);
      hit.addEventListener("pointerleave", hide); hit.addEventListener("blur", hide);
      svg.append(dot, hit);
    });
    return el("div", { class: "chart-wrap" }, svg, tip,
      el("div", { class: "chart-legend" }, el("span", { class: "key key-dot" }, "Weigh-ins"), el("span", { class: "key key-line" }, "7-day average"),
        w.target != null ? el("span", { class: "key key-goal" }, "Goal") : null));
  }

  async function weighIn() {
    const w = fit.weight;
    const v = await form("Log your weight", [{ name: "weight", label: "Weight" + (w.units ? " (" + w.units + ")" : ""), type: "number", required: true },
      { name: "date", label: "Day", type: "date", default: fit.as_of }]);
    if (v) act({ kind: "fitness.weigh_in", params: v });
  }

  function weightSection() {
    const w = fit.weight;
    if (!w) return null;  // a child's page: no weight at all
    const rate = w.weekly_change;
    const chips = [["Latest", g(w.latest, " " + w.units)], ["7-day average", g(w.average_7d, " " + w.units)],
      ["Per week", rate == null ? "—" : (rate > 0 ? "+" : "") + (Math.round(rate * 100) / 100) + " " + w.units],
      ["On track for", w.on_track_for ? day(w.on_track_for) : "—"]];
    return section("Weight", buttons(btn("Log weight", "btn-amber", weighIn)),
      w.count ? el("div", { class: "nw-tiles fact-tiles weight-tiles" }, chips.map(([l, v]) => el("div", { class: "glass nw-tile" }, el("small", {}, l), el("strong", {}, v)))) : null,
      w.series.length ? weightChart(w.series, w)
        : el("p", { class: "empty" }, el("strong", {}, "Log your first weigh-in to start the line."), "Tracking starts with your first log. Nothing to catch up on."),
      w.series.length ? el("details", {}, el("summary", {}, "Every weigh-in (" + w.series.length + ")"),
        el("div", { class: "rows" }, w.series.slice().reverse().map((p) => el("div", { class: "row money-row" },
          el("div", {}, el("div", { class: "row-title" }, p.weight + " " + w.units), el("div", { class: "row-sub" }, day(p.date) + " · 7-day average " + p.average)),
          p.id ? buttons(btn("Remove", "btn-ghost", () => act({ kind: "fitness.weigh_in_delete", params: { entry_id: p.id } }))) : null)))) : null);
  }

  function proteinDays(pr, target) {
    const days = pr.days.slice(-28);
    if (!days.some((d) => d.protein_g != null)) return null;
    const max = Math.max(target || 0, ...days.map((d) => d.protein_g || 0)) || 1;
    return el("div", {}, el("h3", { class: "mini-h" }, "Protein each day" + (target ? " (goal " + target + " g)" : "")),
      el("div", { class: "day-bars", role: "img", "aria-label": "Protein each day for the last " + days.length + " days" },
        target ? el("span", { class: "day-goal", style: "bottom:" + (100 * target / max) + "%" }) : null,
        days.map((d) => el("span", { class: "day-bar" + (target && d.protein_g >= target ? " hit" : ""), style: "height:" + (100 * (d.protein_g || 0) / max) + "%",
          title: day(d.date) + ": " + (d.protein_g == null ? "nothing logged" : Math.round(d.protein_g) + " g") }))));
  }

  function progressView() {
    if (!fit) return [section("Progress", null, el("p", { class: "dim" }, "Plans aren't set up on this MIA."))];
    const pr = fit.progress, t = fit.plan.targets;
    const numbers = [
      pr.planned_workouts ? ["Workouts", pr.workouts + " of " + pr.planned_workouts] : ["Workouts", String(pr.workouts)],
      pr.planned_meals ? ["Planned meals eaten", pr.meals_eaten + " of " + pr.planned_meals] : null,
      ["Calories a day", g(pr.average_kcal) + (t.calories ? " / " + t.calories.toLocaleString() : "")],
      ["Protein a day", g(pr.average_protein_g, " g") + (t.protein_g ? " / " + t.protein_g + " g" : "")]].filter(Boolean);
    const open = (fit.milestones || []).filter((m) => !m.done_on), reached = (fit.milestones || []).filter((m) => m.done_on);
    return [
      section("Is it working?", buttons(planLink()),
        el("p", { class: "progress-sentence" }, pr.sentence),
        el("p", { class: "dim derived-note" }, "Worked out from your logs" + (pr.since ? " since " + day(pr.since) : "") + "."),
        pr.since ? el("div", { class: "nw-tiles fact-tiles" }, numbers.map(([l, v]) => el("div", { class: "glass nw-tile" }, el("small", {}, l), el("strong", {}, v)))) : null,
        proteinDays(pr, t.protein_g)),
      weightSection(),
      open.length || reached.length ? section("Milestones", null, el("div", { class: "rows" }, open.concat(reached).map((m) => el("div", { class: "row money-row" },
        el("div", {}, el("div", { class: "row-title" }, (m.done_on ? "🏆 " : "") + m.name), el("div", { class: "row-sub" }, m.done_on ? "Reached " + day(m.done_on) : (m.target || ""))),
        m.done_on ? null : buttons(btn("Reached it", "btn-green", async () => {
          if (await act({ kind: "fitness.milestone", params: { milestone_id: m.id } })) celebrate(m.name, "Milestone reached");
        })))))) : null,
    ];
  }

  const views = {
    today: todayView,
    progress: progressView,
    log: () => [el("div", { class: "two-up" }, logCard(), el("div", { class: "stack" }, latestCard(), missionCard())),
      section("Recent history", null, page.sessions.length ? el("div", { class: "rows" }, page.sessions.slice(0, 5).map(sessionRow))
        : el("p", { class: "dim" }, "Your sessions show up here."))],
    exercises: () => [section("Exercises", buttons(btn("Add exercise", "btn-amber", () => add("exercise", "Add an exercise"))),
      page.exercises.length ? el("div", { class: "rows" }, page.exercises.map((e) => el("div", { class: "row money-row" },
        el("div", {}, el("div", { class: "row-title" }, e.name),
          el("div", { class: "row-sub" }, [e.category, e.equipment, e.pr ? "Best: " + (e.pr.weight ? e.pr.weight + " × " : "") + e.pr.reps + " reps" : null]
            .filter(Boolean).join(" · "))),
        buttons(btn("Edit", "btn-ghost", () => edit("exercise", e)), btn("Delete", "btn-ghost", () => del("exercise", e))))))
        : el("p", { class: "dim" }, "No exercises yet."))],
    history: () => [section("History", null, page.sessions.length ? el("div", { class: "rows" }, page.sessions.map(sessionRow))
      : el("p", { class: "dim" }, "No sessions yet."))],
    lifts: () => {
      // Skill bests (Zac, 2026-10-16): the longest hold and most reps for each step of each skill, against its target.
      const steps = fit ? (fit.bests || []) : [];  // every step ever practiced (core/web_fitness.py skill_bests)
      const skillCard = (st) => {
        const best = st.best_seconds ? Math.round(st.best_seconds) + " s" : st.best_reps + " reps";
        const on = st.best_seconds ? st.seconds_on : st.reps_on;
        const target = st.target_seconds ? st.target_seconds + " s" : st.target_reps ? st.target_reps + " reps" : null;
        const pct = st.target_seconds ? st.best_seconds / st.target_seconds : st.target_reps ? st.best_reps / st.target_reps : null;
        return el("article", { class: "glass asset-card" },
          el("div", { class: "asset-head" }, el("h3", {}, st.step), el("span", { class: "chip" }, st.skill)),
          el("p", {}, el("strong", {}, best), target ? el("span", { class: "dim" }, " of " + target) : null,
            on ? el("span", { class: "dim" }, " · " + day(on)) : null),
          pct != null ? el("div", { class: "bar" }, el("div", { class: "bar-fill" + (pct >= 1 ? " done" : ""), style: "width:" + Math.min(100, Math.round(pct * 100)) + "%" })) : null);
      };
      const lifts = page.exercises.filter((e) => e.pr);
      return [
        section("Skill Bests", null, steps.length ? el("div", { class: "asset-grid" }, steps.map(skillCard))
          : el("p", { class: "dim" }, "Use the practice timer on Today and your longest holds and most reps show up here.")),
        section("Lifts", null, lifts.length ? el("div", { class: "asset-grid" }, lifts.map((e) => el("article", { class: "glass asset-card" },
          el("div", { class: "asset-head" }, el("h3", {}, e.name), el("span", { class: "chip chip-ok" }, "Best")),
          el("p", {}, (e.pr.weight ? e.pr.weight + " × " : "") + e.pr.reps + " reps", el("span", { class: "dim" }, " · " + day(e.pr.date))),
          spark(e.progress))))
          : el("p", { class: "dim" }, "Log a session with weight and reps and your best lifts show up here.")),
      ];
    },
  };

  function draw() {
    const s = page.stats;
    $("strip").replaceChildren(
      el("div", { class: "cell ok" }, el("span", { class: "n" }, s.this_week), el("span", { class: "t" }, "This week")),
      el("div", { class: "cell soon" }, el("span", { class: "n" }, Math.round(s.minutes_this_week)), el("span", { class: "t" }, "Minutes")),
      el("div", { class: "cell ok" }, el("span", { class: "n" }, (s.streak ? "🔥" : "") + s.streak), el("span", { class: "t" }, "Day streak")));
    $("tabs").hidden = false;
    $("tabs").replaceChildren(...TABS.map(([id, l]) =>
      el("button", { type: "button", role: "tab", "aria-selected": String(id === tab), onclick: () => { tab = id; history.replaceState(null, "", "#" + id); draw(); } }, l)));
    $("panel").replaceChildren(...views[tab]().filter(Boolean));
    // The live session takes the whole screen (the canvas's Active, Rest and Done), unless it's tucked away.
    const going = fit && fit.session && fit.session.status !== "finished";
    let mode = $("wk-mode-host");
    if (going && !live.hidden) {
      if (!mode) { mode = el("div", { id: "wk-mode-host" }); document.body.append(mode); }
      restTicker(fit.session);
      mode.replaceChildren(liveMode());
      document.body.classList.add("wk-live");
    } else {
      if (mode) mode.remove();
      document.body.classList.remove("wk-live");
    }
  }

  MIAShell.start(async () => {
    [page, fit] = await Promise.all([MIA.workout(), MIA.fitness().catch(() => null)]);
    if (fit && !fit.available) fit = null;
    if (!tab) tab = fit ? "today" : "log";
    if (!page.available) {
      $("panel").replaceChildren(el("p", { class: "empty" }, el("strong", {}, "Workouts aren't set up on this MIA."), ""));
      return;
    }
    draw();
  });
})();
