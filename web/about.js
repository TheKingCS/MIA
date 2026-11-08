/*
 * about.js — About MIA (claude, 2026-11-08, DEC-0142).
 * Renders MIA.about() (core/web_about.py): what she is, her real scale as tiles,
 * what she's working on, what she's trained for (each specialty read from the code
 * that makes it true), and what she knows about you, linking to where it's kept.
 * Read only. Formatting only: every line comes from the engine.
 */
(function () {
  "use strict";
  const { el } = MIAShell;
  const $ = (id) => document.getElementById(id);
  const n = (v) => Number(v).toLocaleString();

  function paint(data) {
    $("ab-sub").textContent = "What she can honestly say about herself, read from her own code and what you've told her.";
    const you = data.you || {};
    $("panel").replaceChildren(...[
      el("section", { class: "glass ab-intro" },
        el("div", { class: "ab-orb", "aria-hidden": "true" }),
        el("p", { class: "ab-line" }, data.about || "")),
      data.numbers.length ? el("section", { class: "ab-tiles" }, ...data.numbers.map((t) => el("div", { class: "glass ab-tile" },
        el("span", { class: "ab-n" }, n(t.value)),
        el("span", { class: "ab-label" }, t.label),
        el("span", { class: "dim ab-note" }, t.note)))) : null,
      data.focus ? el("section", { class: "glass ab-focus" },
        el("p", { class: "pw-label" }, "Working On"),
        el("p", { class: "ab-focus-line" }, data.focus)) : null,
      data.specialties.length ? el("section", { class: "ab-specs" },
        el("p", { class: "pw-label" }, "Trained For"),
        el("div", { class: "ab-spec-grid" }, ...data.specialties.map((s) => el("article", { class: "glass ab-spec" },
          el("h3", { class: "ab-spec-title" }, s.title),
          el("p", { class: "ab-spec-line" }, s.line))))) : null,
      el("section", { class: "glass ab-you" },
        el("p", { class: "pw-label" }, "What She Knows About You"),
        el("p", { class: "ab-you-line" }, you.line || ""),
        el("div", { class: "row-buttons" },
          el("a", { class: "btn btn-ghost btn-small", href: "directions.html" }, you.directions && you.directions.length ? "Your Directions (" + you.directions.length + ")" : "Set a Direction"),
          el("a", { class: "btn btn-ghost btn-small", href: "answers.html" }, "How She Answers" + (you.style_picks ? " (" + you.style_picks + " picks)" : "")),
          el("a", { class: "btn btn-ghost btn-small", href: "yourdata.html" }, "Everything She Keeps"))),
      el("p", { class: "dim ab-say" }, "Say \"what are you?\", \"what are you trained for?\" or \"what do you know about me?\" any time."),
    ].filter(Boolean));
  }

  MIAShell.start(async () => { paint(await MIA.about()); }, { refreshOnChange: true });
})();
