/*
 * about.js — About MIA (claude, 2026-11-08, DEC-0142).
 * Renders MIA.about() (core/web_about.py): what she is, her real scale as tiles,
 * what she's working on, what she's trained for (each specialty read from the code
 * that makes it true), how her apps are doing on this device (DEC-0057: working, partly,
 * planned, not here, broke this week), and what she knows about you, linking to where it's kept.
 * Read only. Formatting only: every line comes from the engine.
 */
(function () {
  "use strict";
  const { el } = MIAShell;
  const $ = (id) => document.getElementById(id);
  const n = (v) => Number(v).toLocaleString();

  // How her apps are doing here: a count per status, then what isn't simply working (broke this week first; that's
  // inferred from what broke, and says so).
  function appsHealth(apps) {
    if (!apps || !apps.counts.length) return null;
    return el("section", { class: "glass ab-apps" },
      el("p", { class: "pw-label" }, "How Her Apps Are Doing Here"),
      el("div", { class: "ab-counts" }, ...apps.counts.map((c) => el("span", { class: "ab-count " + c.status.replace(" ", "-") },
        el("b", {}, n(c.n)), " " + c.word))),
      apps.notes.length ? el("ul", { class: "ab-app-notes" }, ...apps.notes.slice(0, 12).map((r) =>
        el("li", { class: "ab-app " + r.status.replace(" ", "-") },
          el("span", { class: "ab-app-word" }, r.word),
          el("span", {}, el("b", {}, r.name), " · " + r.why + (r.evidence === "inferred" ? " (from what broke)" : ""))))) : null,
      apps.notes.length > 12 ? el("p", { class: "dim" }, (apps.notes.length - 12) + " more. Ask her \"what isn't working?\"") : null);
  }

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
      appsHealth(data.apps),
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

  // This device, as her app list counts it: a touch screen without a fine pointer is the phone.
  const here = window.matchMedia && matchMedia("(pointer: coarse)").matches && !matchMedia("(pointer: fine)").matches ? "phone" : "pc";
  MIAShell.start(async () => { paint(await MIA.about(here)); }, { refreshOnChange: true });
})();
