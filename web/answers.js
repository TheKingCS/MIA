/*
 * answers.js — How MIA Answers (claude, 2026-11-08, DEC-0138).
 * Renders MIA.answers() (core/answer_compare.py): for each part of how she answers
 * (how long, how it's laid out, the tone, what comes first) the way she leans, how
 * settled that is, and every option to choose outright (style.set); whether she
 * offers an answer two ways now and then (style.compare); and Forget (style.reset).
 * All actions, so each is undoable. Formatting only: the engine decides.
 */
(function () {
  "use strict";
  const { el } = MIAShell;
  const $ = (id) => document.getElementById(id);

  function dimension(d) {
    const most = Math.max(1, ...d.options.map((o) => o.count));
    return el("section", { class: "glass ans-dim" },
      el("div", { class: "ans-head" },
        el("h3", { class: "ans-name" }, d.name),
        el("span", { class: "ans-word" + (d.word === "Settled" ? " on" : "") }, d.word + (d.picks ? " · " + d.picks + (d.picks === 1 ? " pick" : " picks") : ""))),
      el("div", { class: "ptabs ans-options", role: "radiogroup", "aria-label": d.name },
        ...d.options.map((o) => el("button", { type: "button", role: "radio", "aria-checked": String(o.value === d.preferred),
          "aria-selected": String(o.value === d.preferred),
          onclick: o.value === d.preferred ? null : () => MIAShell.act({ kind: "style.set", params: { dimension: d.id, value: o.value } }, { quick: true }) },
          o.label))),
      d.picks ? el("div", { class: "ans-bars" }, ...d.options.map((o) => el("div", { class: "ans-bar" },
        el("span", { class: "dim" }, o.label),
        el("span", { class: "ans-track" }, el("span", { class: "ans-fill", style: "width:" + Math.round(100 * o.count / most) + "%" })),
        el("span", { class: "dim ans-n" }, String(o.count))))) : null);
  }

  function paint(data) {
    if (!data.available) {
      $("ans-sub").textContent = "Answer styles aren't set up on this MIA yet.";
      $("panel").replaceChildren();
      return;
    }
    $("ans-sub").textContent = data.picks
      ? "What she's learned from your picks. Tap any way to choose it outright."
      : "Nothing learned yet. Pick a way below, or choose between two when she offers.";
    const toggle = el("input", { id: "ans-compare", type: "checkbox", role: "switch", checked: data.compare ? true : null,
      "aria-label": "Offer an answer two ways now and then",
      onchange: (e) => MIAShell.act({ kind: "style.compare", params: { on: e.target.checked } }, { quick: true }) });
    $("panel").replaceChildren(...[
      data.instruction ? el("div", { class: "glass ans-now" },
        el("p", { class: "pw-label" }, "What She Follows Now"),
        el("p", { class: "ans-now-line" }, data.instruction)) : null,
      el("div", { class: "ans-grid" }, ...data.dimensions.map(dimension)),
      el("div", { class: "glass ans-row" },
        el("div", {},
          el("p", { class: "ans-row-title" }, "Two ways now and then"),
          el("p", { class: "dim ans-row-note" }, "At most once a day, after a longer answer, she shows it a second way and asks which you prefer. " +
            "Next she'd try " + data.next.dimension.replace("_", " ") + ". Never in a private conversation.")),
        el("span", { class: "switch" }, toggle, el("span", { "aria-hidden": "true" }))),
      data.picks ? el("div", { class: "row-buttons ans-forget" },
        el("button", { type: "button", class: "btn btn-quiet btn-small", onclick: () => MIAShell.act({ kind: "style.reset", params: {} }) },
          "Forget What She Learned")) : null,
      el("p", { class: "dim ans-say" }, "Say \"keep your answers short\", \"use bullet points\", \"be more direct\", " +
        "\"how do I like answers?\" or \"stop asking which I prefer\" any time."),
    ].filter(Boolean));
  }

  MIAShell.start(async () => { paint(await MIA.answers()); }, { refreshOnChange: true });
})();
