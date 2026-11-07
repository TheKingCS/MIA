/*
 * cook.js — cook mode (claude, 2026-11-07, DEC-0113: the design canvas's
 * Kitchen · Cook Mode). The recipe being cooked takes the whole screen, on
 * the Kitchen page and on a recipe's page alike: one step in large type,
 * what this step uses, the step's own timer to start, every timer running
 * (they keep going across steps), MIA listening, and Back / Next Step as big
 * targets. "I made this" on the last step logs the meal (cooking.made, which
 * is meal.cook). Tuck it away and a bar brings it back.
 *
 * The session comes from the engine (core/cooking_session.py, on the page's
 * own read as `cooking`); every button is an action (core/cooking_actions.py)
 * through MIAShell.act, so it's confirmed and undoable. Formatting only.
 *
 *   MIACook.render(cooking)  -> mounts, redraws or removes the cook mode layer
 *   MIACook.start(recipeId)  -> proposes cooking.start
 *   MIACook.bar()            -> the "still cooking" bar, or null
 */
(function () {
  "use strict";
  const { el, act } = MIAShell;
  const state = { cooking: null, hidden: false, tick: null, rendered: 0 };
  const mmss = (n) => Math.floor(n / 60) + ":" + String(n % 60).padStart(2, "0");

  function speak(text) {
    try { if (window.MIAPhoneVoice && MIAPhoneVoice.say) { MIAPhoneVoice.say(String(text)); return; } } catch (e) { /* next */ }
    try { if (window.speechSynthesis) speechSynthesis.speak(new SpeechSynthesisUtterance(String(text))); } catch (e) { /* silent */ }
  }

  // The timers count down here between reads; the engine's numbers win on the next one.
  function ticker() {
    if (state.tick) clearInterval(state.tick);
    state.tick = null;
    const c = state.cooking;
    if (!c || !c.timers.some((t) => !t.done)) return;
    const base = Date.now();
    state.tick = setInterval(() => {
      const gone = Math.floor((Date.now() - base) / 1000);
      c.timers.forEach((t, i) => {
        const left = Math.max(0, t.left - gone), node = document.getElementById("cook-timer-" + i);
        if (node) node.textContent = mmss(left);
        if (left === 0 && !t.announced && !t.done) { t.announced = true; speak(t.name + " timer's done."); }
      });
    }, 1000);
  }

  function timerRow(t, i) {
    return el("div", { class: "cook-timer" + (t.done ? " done" : "") },
      el("div", { class: "cook-timer-head" }, el("span", {}, t.name),
        el("span", { class: "kind " + (t.done ? "attention" : "accent") }, t.done ? "Done" : "Running")),
      el("span", { class: "cook-timer-n", id: "cook-timer-" + i, role: "timer" }, mmss(t.left)),
      el("div", { class: "meter" }, el("div", { class: "meter-fill", style: "width:" + (t.seconds ? Math.round(100 * (1 - t.left / t.seconds)) : 100) + "%" })),
      el("button", { type: "button", class: "btn btn-ghost", onclick: () => act({ kind: "cooking.timer_cancel", params: { name: t.name } }) },
        t.done ? "Clear" : "Stop"));
  }

  function layer(c) {
    const offer = c.offer_timer && !c.timers.some((t) => t.name.toLowerCase() === c.offer_timer.name.toLowerCase())
      ? c.offer_timer : null;
    return el("div", { class: "cook-mode", role: "dialog", "aria-label": "Cooking " + c.title },
      el("header", { class: "cook-top" },
        el("button", { type: "button", class: "btn btn-ghost cook-exit", onclick: () => { state.hidden = true; render(c); } }, "✕ Hide"),
        el("div", { class: "cook-title" }, el("span", { class: "wk-label atmo" }, "Cooking"), el("strong", {}, c.title)),
        el("div", { class: "cook-steps", "aria-label": "Step " + c.number + " of " + c.steps_total },
          ...Array.from({ length: c.steps_total }, (_, i) =>
            el("span", { class: i < c.number - 1 ? "done" : i === c.number - 1 ? "now" : "" })))),
      el("div", { class: "cook-body" },
        el("section", { class: "surface-focus cook-step" },
          el("span", { class: "wk-label" }, "Step " + c.number + " of " + c.steps_total),
          el("h1", {}, c.step),
          c.uses.length ? el("div", { class: "cook-uses" }, el("span", { class: "wk-label" }, "This Step Uses"),
            el("div", { class: "cook-chips" }, ...c.uses.map((u) => el("span", { class: "cook-chip" },
              u.amount ? el("span", { class: "atmo wk-mono" }, u.amount + " ") : null, u.name)))) : null,
          offer ? el("button", { type: "button", class: "btn btn-amber cook-offer", onclick: () =>
            act({ kind: "cooking.timer", params: { name: offer.name, minutes: String(Math.round(offer.seconds / 6) / 10) } }) },
            "Start " + offer.name + " Timer · " + mmss(offer.seconds)) : null),
        el("aside", { class: "cook-side" },
          el("section", { class: "glass cook-timers" }, el("span", { class: "wk-label" }, "Timers"),
            ...(c.timers.length ? c.timers.map(timerRow) : [el("p", { class: "dim" }, "None running. A step that says how long offers its timer.")]),
            el("button", { type: "button", class: "btn btn-ghost", onclick: addTimer }, "Add Timer")),
          el("section", { class: "glass cook-mia" },
            el("span", { class: "mia-orb", "data-state": "listening", role: "img", "aria-label": "MIA is listening" }),
            el("div", {}, el("span", { class: "mia-orb-label" }, "Listening"),
              el("p", { class: "dim" }, "“Next step” · “Go back” · “Set a timer for 18 minutes”"))))),
      el("footer", { class: "cook-foot" },
        el("button", { type: "button", class: "btn-big quiet cook-back", disabled: c.number <= 1 ? true : null,
          onclick: () => act({ kind: "cooking.back", params: {} }) }, "‹ Back"),
        c.last
          ? el("button", { type: "button", class: "btn-big", onclick: () => act({ kind: "cooking.made", params: {} }) }, "I Made This")
          : el("button", { type: "button", class: "btn-big", onclick: () => act({ kind: "cooking.next", params: {} }) }, "Next Step ›")),
      el("button", { type: "button", class: "btn btn-ghost cook-stop", onclick: () => act({ kind: "cooking.stop", params: {} }) },
        "Stop Without Logging"));
  }

  async function addTimer() {
    const v = await MIAShell.form("Start a timer", [
      { name: "name", label: "What it's for", type: "text", required: true, default: "Timer" },
      { name: "minutes", label: "Minutes", type: "number", required: true }], {});
    if (v) act({ kind: "cooking.timer", params: v });
  }

  function render(cooking) {
    state.cooking = cooking || null;
    let host = document.getElementById("cook-host");
    if (!cooking || state.hidden) {
      if (host) host.remove();
      document.body.classList.remove("cook-live");
      ticker();
      return;
    }
    if (!host) { host = el("div", { id: "cook-host" }); document.body.append(host); }
    host.replaceChildren(layer(cooking));
    document.body.classList.add("cook-live");
    ticker();
  }

  function bar() {
    const c = state.cooking;
    if (!c || !state.hidden) return null;
    return el("button", { type: "button", class: "glass wk-bar", onclick: () => { state.hidden = false; render(c); } },
      el("span", { class: "kind accent" }, "Cooking"), el("span", {}, c.title + " · step " + c.number + " of " + c.steps_total),
      el("span", { class: "dim" }, "Open"));
  }

  window.MIACook = {
    render,
    bar,
    start: (recipeId) => act({ kind: "cooking.start", params: { recipe_id: recipeId } }),
  };
})();
