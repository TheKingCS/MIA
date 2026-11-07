/*
 * guitar.js — a learning path (claude, 2026-11-07, DEC-0111, DEC-0112): guitar
 * by default, any path with ?path=<id>.
 * Renders MIA.guitar() (core/guitar.py): the stage, this week against the
 * plan, the streak, the bests, what to work on next, and each open check.
 * A check MIA hears gets a Record button: a few seconds from the microphone,
 * made into a 16-bit mono WAV here (the engine reads WAV), sent to
 * MIA.guitarListen(); what she heard is shown under it. Tuning goes one
 * string at a time. A check passed from the person's records (recorded) says
 * so. Nothing is kept but the result. Formatting only; the
 * look is muse's.
 */
(function () {
  "use strict";
  const { el } = MIAShell;
  const $ = (id) => document.getElementById(id);
  const SECONDS = 3;
  const PATH = new URLSearchParams(location.search).get("path") || "guitar";  // any learning path (DEC-0112)

  // Float samples to a 16-bit mono WAV file.
  function wav(samples, rate) {
    const data = new DataView(new ArrayBuffer(44 + samples.length * 2));
    const text = (at, s) => { for (let i = 0; i < s.length; i++) data.setUint8(at + i, s.charCodeAt(i)); };
    text(0, "RIFF"); data.setUint32(4, 36 + samples.length * 2, true); text(8, "WAVE"); text(12, "fmt ");
    data.setUint32(16, 16, true); data.setUint16(20, 1, true); data.setUint16(22, 1, true);
    data.setUint32(24, rate, true); data.setUint32(28, rate * 2, true); data.setUint16(32, 2, true);
    data.setUint16(34, 16, true); text(36, "data"); data.setUint32(40, samples.length * 2, true);
    for (let i = 0; i < samples.length; i++) {
      const s = Math.max(-1, Math.min(1, samples[i]));
      data.setInt16(44 + i * 2, s < 0 ? s * 0x8000 : s * 0x7fff, true);
    }
    return new File([data], "take.wav", { type: "audio/wav" });
  }

  // A few seconds from the microphone, decoded to samples.
  async function record() {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: false, noiseSuppression: false } });
    const recorder = new MediaRecorder(stream);
    const parts = [];
    recorder.ondataavailable = (e) => parts.push(e.data);
    const stopped = new Promise((done) => { recorder.onstop = done; });
    recorder.start();
    await new Promise((r) => setTimeout(r, SECONDS * 1000));
    recorder.stop();
    await stopped;
    stream.getTracks().forEach((t) => t.stop());
    const audio = new AudioContext();
    const decoded = await audio.decodeAudioData(await new Blob(parts).arrayBuffer());
    audio.close();
    return wav(decoded.getChannelData(0), decoded.sampleRate);
  }

  function heardRow(check) {
    const said = el("p", { class: "dim" }, check.how === "heard_tuning"
      ? "Press a string's button, then pluck that open string and let it ring. 6 is the low E."
      : "Press Record, then strum it and let it ring.");
    const go = async (string) => {
      said.textContent = "Listening for " + SECONDS + " seconds…";
      try {
        const got = await MIA.guitarListen(check.id, await record(), string, PATH);
        said.textContent = got.said;
        if (got.passed) setTimeout(load, 1500);
      } catch (e) {
        said.textContent = e.message || "I couldn't hear that. Try again a little closer.";
      }
    };
    const buttons = check.how === "heard_tuning"
      ? [6, 5, 4, 3, 2, 1].map((n) => el("button", { type: "button", class: "btn btn-small btn-ghost", onclick: () => go(n) },
          "String " + n))
      : [el("button", { type: "button", class: "btn btn-small btn-amber", onclick: () => go(null) }, "Record")];
    return el("div", { class: "sync-row" }, el("div", {}, el("p", {}, check.what), el("div", { class: "row-buttons" }, buttons), said));
  }

  function plainRow(check) {
    return el("div", { class: "sync-row" }, el("div", {}, el("p", {}, check.what),
      el("p", { class: "dim" }, check.how === "counted" ? "Time yourself, then tell MIA the number."
        : check.how === "recorded" ? "MIA passes this from your own records when they reach the mark."
        : "Tell MIA when you've done it.")));
  }

  // The design canvas's path screen (DEC-0113): the stage and its rail, this week against the plan, the streak and
  // the best, what to work on next with the homework, every check of the stage (passed or open, and who verifies
  // it; the ones MIA hears can be recorded here), then Log Practice and Tune.
  function checkRow(c, open) {
    const row = open && c.how.startsWith("heard") ? heardRow(open) : null;
    return el("div", { class: "gp-check" + (c.passed ? " passed" : ""), id: "check-" + c.id },
      el("div", { class: "gp-check-head" }, el("span", { class: "gp-what" }, c.what), el("span", { class: "gp-state" }, c.state)),
      row ? row.querySelector(".row-buttons") : null, row ? row.querySelector("p.dim") : null);
  }
  function paint(data) {
    const s = data.stats;
    document.querySelector(".hero h1").textContent = data.name || "Learning";
    if (!s.started) {
      $("guitar-sub").textContent = "Not started yet.";
      $("panel").replaceChildren(el("section", { class: "glass money-section" }, el("p", {}, data.next)));
      return;
    }
    $("guitar-sub").textContent = "Learning path · Stage " + s.stage + (s.stages ? " of " + s.stages : "");
    const plan = (s.plan.minutes_a_day || 0) * (s.plan.days_a_week || 0);
    const best = Object.entries(s.bests || {})[0];
    const openById = Object.fromEntries(data.open.map((c) => [c.id, c]));
    const checks = (data.stage_checks && data.stage_checks.length) ? data.stage_checks
      : data.open.map((c) => Object.assign({ passed: false, state: "Open" }, c));
    const tuning = checks.find((c) => c.how === "heard_tuning" && !c.passed);
    $("panel").replaceChildren(
      el("section", { class: "gp-stage" },
        el("h2", {}, "Stage " + s.stage + ": " + s.stage_name),
        el("p", { class: "dim" }, "Understand · Plan · Practise · Verify · Next stage"),
        s.stages ? el("div", { class: "gp-rail", role: "img", "aria-label": "Stage " + s.stage + " of " + s.stages },
          Array.from({ length: s.stages }, (_, i) => el("span", { class: "gp-seg" + (i + 1 < s.stage ? " done" : i + 1 === s.stage ? " now" : "") }))) : null),
      el("section", { class: "glass prop-trio gp-week", "aria-label": "This week" },
        el("div", { class: "prop-trio-cell" }, el("span", { class: "prop-trio-t" }, "This Week"),
          el("strong", {}, s.week_minutes + (plan ? " / " + plan : "") + " min")),
        el("div", { class: "prop-trio-cell" }, el("span", { class: "prop-trio-t" }, "Streak"),
          el("strong", {}, s.streak + " day" + (s.streak === 1 ? "" : "s"))),
        el("div", { class: "prop-trio-cell" }, el("span", { class: "prop-trio-t" }, "Best"),
          el("strong", {}, best ? String(best[1]) : "—"))),
      el("section", { class: "glass surface-focus gp-next", "aria-label": "Work on next" },
        el("span", { class: "gp-label" }, "Work On Next"), el("p", { class: "gp-next-text" }, data.next),
        data.homework ? el("p", { class: "dim" }, "Homework: " + data.homework) : null),
      el("section", { class: "glass gp-checks", "aria-label": "Checks to pass" },
        el("h2", { class: "gp-label" }, "Checks To Pass · " + checks.filter((c) => c.passed).length + " of " + checks.length),
        ...checks.map((c) => checkRow(c, openById[c.id]))),
      el("div", { class: "gp-actions" },
        el("button", { type: "button", class: "btn btn-big btn-green",
          onclick: () => { location.href = "assistant.html?draft=" + encodeURIComponent("I practised " + (data.name || "") + " for  minutes."); } }, "Log Practice"),
        tuning ? el("button", { type: "button", class: "btn btn-big quiet",
          onclick: () => { const r = $("check-" + tuning.id); if (r) r.scrollIntoView({ behavior: "smooth", block: "center" }); } }, "Tune") : null));
  }

  async function load() { paint(await MIA.guitar(PATH)); }

  MIAShell.start(load);
})();
