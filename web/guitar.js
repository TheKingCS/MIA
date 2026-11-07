/*
 * guitar.js — a learning path (claude, 2026-11-07, DEC-0111, DEC-0112): guitar
 * by default, any path with ?path=<id>.
 * Renders MIA.guitar() (core/guitar.py): the stage, this week against the
 * plan, the streak, the bests, what to work on next, and each open check.
 * A check MIA hears gets a Record button: a few seconds from the microphone,
 * made into a 16-bit mono WAV here (the engine reads WAV), sent to
 * MIA.guitarListen(); what she heard is shown under it. Tuning goes one
 * string at a time. Nothing is kept but the result. Formatting only; the
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
        : "Tell MIA when you've done it.")));
  }

  function paint(data) {
    const s = data.stats;
    document.querySelector(".hero h1").textContent = data.name || "Learning";
    if (!s.started) {
      $("guitar-sub").textContent = "Not started yet.";
      $("panel").replaceChildren(el("section", { class: "glass money-section" }, el("p", {}, data.next)));
      return;
    }
    $("guitar-sub").textContent = "Stage " + s.stage + ": " + s.stage_name;
    const bests = Object.entries(s.bests || {}).map(([k, v]) => k.replace(/_/g, " ") + " " + v);
    $("panel").replaceChildren(
      el("section", { class: "glass money-section" }, el("h2", {}, "This week"),
        el("p", {}, s.week_days + " of " + s.plan.days_a_week + " days, " + s.week_minutes + " minutes · streak " +
          s.streak + " · " + s.hours + " hours in all · " + s.checks_passed + " of " + s.checks + " checks passed"),
        bests.length ? el("p", { class: "dim" }, "Bests: " + bests.join("; ")) : null,
        el("p", {}, data.next)),
      el("section", { class: "glass money-section" }, el("h2", {}, "Checks to pass"),
        el("div", { class: "sync-rows" }, data.open.map((c) => c.how.startsWith("heard") ? heardRow(c) : plainRow(c)))));
  }

  async function load() { paint(await MIA.guitar(PATH)); }

  MIAShell.start(load);
})();
