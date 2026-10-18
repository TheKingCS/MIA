/*
 * sound.js — MIA's sounds (claude, 2026-10-17, DEC-0028 #11). Short tones
 * made in the browser (Web Audio: no sound files to download, works
 * offline): a chime for an objective, a quest-complete arpeggio for a
 * mission, a fanfare for a level. MIA's voice line (from the engine's
 * reward.say, core/actions.voice_line) is spoken by this device's voice
 * when the person turned voice lines on. Settings come from MIA.shell()
 * (`sound`: on, voice; Settings → Sound). Only ever for a win.
 */
(function () {
  "use strict";
  let settings = { on: true, voice: false };
  let ctx = null;

  function audio() {
    if (!ctx) {
      const AC = window.AudioContext || window.webkitAudioContext;
      if (!AC) return null;
      ctx = new AC();
    }
    if (ctx.state === "suspended") ctx.resume().catch(() => {});
    return ctx;
  }

  // One soft note: a sine with a short attack and a gentle fade.
  function note(freq, at, length, volume, type) {
    const a = audio();
    if (!a) return;
    const start = a.currentTime + at;
    const osc = a.createOscillator(), gain = a.createGain();
    osc.type = type || "sine";
    osc.frequency.setValueAtTime(freq, start);
    gain.gain.setValueAtTime(0.0001, start);
    gain.gain.exponentialRampToValueAtTime(volume || 0.18, start + 0.02);
    gain.gain.exponentialRampToValueAtTime(0.0001, start + length);
    osc.connect(gain).connect(a.destination);
    osc.start(start);
    osc.stop(start + length + 0.05);
  }

  const TUNES = {
    // A bright two-note chime (an objective done).
    chime: () => { note(880, 0, 0.35); note(1318.5, 0.09, 0.5); },
    // Quest complete: a rising arpeggio that lands on a held note.
    quest: () => { [523.25, 659.25, 783.99].forEach((f, i) => note(f, i * 0.1, 0.3)); note(1046.5, 0.32, 0.9, 0.2); },
    // Level up: a little fanfare, with a triangle voice for brass.
    fanfare: () => {
      [[523.25, 0], [523.25, 0.12], [523.25, 0.24], [659.25, 0.36], [783.99, 0.62], [659.25, 0.8], [1046.5, 0.95]]
        .forEach(([f, t], i) => note(f, t, i === 6 ? 1.1 : 0.22, 0.16, "triangle"));
      note(1568, 0.95, 1.0, 0.06);
    },
    // A quiet tick (credits, XP without a finish).
    tick: () => note(1200, 0, 0.12, 0.08),
  };

  function play(name) {
    if (!settings.on || !TUNES[name]) return;
    try { TUNES[name](); } catch (e) { /* no sound is fine */ }
  }

  function speak(text) {
    if (!settings.voice || !text || !window.speechSynthesis) return;
    try {
      speechSynthesis.cancel();
      const u = new SpeechSynthesisUtterance(text);
      u.rate = 1.02;
      setTimeout(() => speechSynthesis.speak(u), 650);  // after the tune starts
    } catch (e) { /* no voice is fine */ }
  }

  /** The engine's proposal.reward (core/actions.reward_for) → the right tune and line. */
  function celebrate(reward) {
    if (!reward) return;
    play(reward.level_up ? "fanfare" : reward.headline === "Mission Complete" ? "quest"
      : reward.headline === "Objective Complete" ? "chime" : "tick");
    speak(reward.say);
  }

  // A sound check (Settings → Sound): plays even while sounds are off.
  function preview(name) { try { if (TUNES[name]) TUNES[name](); } catch (e) { /* fine */ } }

  window.MIASound = {
    configure: (s) => { if (s) settings = { on: s.on !== false, voice: !!s.voice }; },
    play, speak, celebrate, preview,
    get settings() { return Object.assign({}, settings); },
  };
})();
