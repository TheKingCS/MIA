/*
 * diagnostics.js — the PC's check-ups (claude, 2026-11-06, T-0040).
 * Renders MIA.diagnostics() (core/diagnostics.py): each built-in check-up over
 * one passive inspection (nothing is probed or changed), what passed, what to
 * look at, and what couldn't be read (never counted as a pass). The PC's
 * owner's page. Formatting only; the look is muse's. What she can do (WP-08): each capability's state from its
 * evidence (core/capability_registry.py).
 * Her care of herself (DEC-0222, DEC-0225): the changes she made to herself,
 * each with Undo (the action lab.revert, approved on its card), what she put
 * right, and what she can never change. All decided in core (self_view).
 */
(function () {
  "use strict";
  const { el } = MIAShell;
  const $ = (id) => document.getElementById(id);

  // The design canvas (DEC-0113): Passed / Look At / Unread as tiles, then one row per check-up with its dot (green
  // all passed, amber something to look at, grey something it couldn't read) and the line that matters, then Run Again.
  function row(c) {
    const state = c.failed.length ? "look" : c.unknown.length ? "unread" : "ok";
    const note = c.failed.length ? c.failed.join(" ") : c.unknown.length ? "Couldn't read: " + c.unknown.join(", ")
      : c.passed + (c.passed === 1 ? " check passed" : " checks passed");
    return el("div", { class: "dx-row" }, el("span", { class: "dx-dot " + state, "aria-hidden": "true" }),
      el("div", { class: "dx-text" }, el("span", {}, c.title), el("span", { class: "dx-note" }, note),
        c.failed.length && c.unknown.length ? el("span", { class: "dx-note" }, "Couldn't read: " + c.unknown.join(", ")) : null),
      el("span", { class: "sr-only" }, state === "ok" ? "passed" : state === "look" ? "to look at" : "couldn't read all of it"));
  }
  // Her own repository (T-0020): where her docs disagree with it, grouped; read only, like the rest of the page.
  function repoPanel(r) {
    if (!r || !r.available) return null;
    return el("details", { class: "glass dx-list dx-repo", open: r.findings ? "" : null },
      el("summary", { class: "dx-label" }, "Her Own Repository · " + (r.findings ? r.findings + " to look at" : "matches her docs")),
      ...(r.groups.length ? r.groups.map((g) => el("div", { class: "dx-repo-group" },
        el("p", { class: "dx-repo-title" }, g.title + " · " + g.items.length),
        el("ul", { class: "dx-repo-items" }, ...g.items.slice(0, 12).map((x) => el("li", {}, x))),
        g.items.length > 12 ? el("p", { class: "dim" }, (g.items.length - 12) + " more") : null))
        : [el("p", { class: "dim" }, "Every file her docs name is there, and every requirement is installed.")]));
  }

  // Her care of herself (core/diagnostics.self_view): what she changed in herself, what she put right, and what she
  // can never change. Undo is the action lab.revert, through the approval card like any change.
  function selfPanels(s) {
    if (!s) return [];
    const changes = el("details", { class: "glass dx-list dx-repo", open: s.changes.length ? "" : null },
      el("summary", { class: "dx-label" }, "Changes I Made To Myself · " + s.changes.length),
      ...(s.changes.length ? s.changes.map((c) => el("div", { class: "dx-hw-row" },
        el("span", { class: "dx-hw-name" }, c.why || c.title),
        el("span", { class: "dim" }, when(c.at) + " · " + c.proposal + (c.status === "undone" ? " · undone" : "")),
        c.status === "merged" ? el("button", { type: "button", class: "btn btn-quiet btn-small",
          onclick: async () => { await MIAShell.act({ kind: "lab.revert", params: { proposal_id: c.proposal } });
            paint(await MIA.diagnostics()); } }, "Undo") : null))
        : [el("p", { class: "dim" }, "Nothing lately. What Night School keeps goes in only on Claude's pass, and you get a summary.")]));
    const repairs = el("details", { class: "glass dx-list dx-repo" },
      el("summary", { class: "dx-label" }, "What I Put Right · " + s.repairs.length),
      ...(s.repairs.length ? s.repairs.map((r) => el("div", { class: "dx-log-row" },
        el("span", { class: "dx-dot " + (r.ok ? "ok" : "look"), "aria-hidden": "true" }),
        el("div", {}, el("div", { class: "dx-log-text" }, r.said), el("div", { class: "dim" }, when(r.at)))))
        : [el("p", { class: "dim" }, "Nothing needed restarting lately.")]));
    const kept = el("details", { class: "glass dx-list dx-repo" },
      el("summary", { class: "dx-label" }, "What I Can Never Change"),
      el("p", { class: "dim" }, "A change that touches any of these is refused before it's tested, whoever wrote it."),
      ...s.protected.filter((g) => g.count).map((g) => el("div", { class: "dx-repo-group" },
        el("p", { class: "dx-repo-title" }, g.name), el("p", { class: "dim" }, g.why))));
    return [changes, repairs, kept];
  }
  const when = (iso) => !iso ? "" : new Date(iso).toLocaleString(undefined, { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" });

  // What she can do (WP-08, core/capability_registry.py): each capability's state from its evidence, counted; the ones
  // not fully working with why; and the latest changes of state, each with what caused it. Read only, rebuilt each look.
  const STATE_WORDS = { working: "Working", partial: "Partly", degraded: "Degraded now", "unavailable here": "Not on this device",
    malfunctioning: "Unwell", unverified: "Unverified", planned: "Planned", retired: "Retired" };
  function capabilitiesPanel(c) {
    if (!c) return null;
    const n = c.counts || {};
    const line = Object.keys(STATE_WORDS).filter((s) => n[s]).map((s) => STATE_WORDS[s] + " " + n[s]).join(" · ");
    return el("details", { class: "glass dx-list dx-repo" },
      el("summary", { class: "dx-label" }, "What I Can Do · " + line),
      el("p", { class: "dim" }, "Each one's state is worked out from evidence: its tests, when it was last used and last failed, "
        + "the devices it's on and what it needs. Nothing here can be set by hand, or by me."),
      ...(c.notable || []).map((r) => el("div", { class: "dx-hw-row" },
        el("span", { class: "dx-hw-name" }, r.name), el("span", { class: "dx-hw-value" }, STATE_WORDS[r.state] || r.state),
        el("span", { class: "dim" }, r.evidence.slice(1).join("; ") || r.evidence[0]))),
      ...((c.changes || []).length ? [el("p", { class: "dx-repo-title" }, "Lately")].concat(c.changes.map((x) =>
        el("div", { class: "dx-hw-row" }, el("span", { class: "dx-hw-name" }, x.id),
          el("span", { class: "dx-hw-value" }, (STATE_WORDS[x.from] || x.from) + " \u2192 " + (STATE_WORDS[x.to] || x.to)),
          el("span", { class: "dim" }, when(x.at) + " · " + (x.because || []).slice(1).join("; "))))) : []));
  }

  function paint(data) {
    const sum = (f) => data.checks.reduce((n, c) => n + f(c), 0);
    const passed = sum((c) => c.passed), look = sum((c) => c.failed.length), unread = sum((c) => c.unknown.length);
    $("diag-sub").textContent = data.error ? "Couldn't look." : look ? look + " to look at." : "All good.";
    const tile = (cls, label, n) => el("div", { class: "glass dx-tile " + cls }, el("span", { class: "dx-dot " + cls, "aria-hidden": "true" }),
      el("div", {}, el("div", { class: "dx-label" }, label), el("div", { class: "dx-n" }, String(n))));
    $("panel").replaceChildren(...[
      data.error ? el("p", { class: "empty" }, data.error) : null,
      el("div", { class: "dx-tiles" }, tile("ok", "Passed", passed), tile("look", "Look At", look), tile("unread", "Unread", unread)),
      el("section", { class: "glass dx-list", "aria-labelledby": "dx-checks" }, el("h2", { id: "dx-checks", class: "dx-label" }, "Check-Ups"),
        ...data.checks.map(row)),
      (data.hardware || []).length ? el("section", { class: "glass dx-list dx-hw", "aria-labelledby": "dx-hw" },
        el("h2", { id: "dx-hw", class: "dx-label" }, "This PC"),
        ...data.hardware.map((h) => el("div", { class: "dx-hw-row" }, el("span", { class: "dx-hw-name" }, h.name),
          el("span", { class: "dx-hw-value" }, h.value), el("span", { class: "dim" }, h.note)))) : null,
      el("details", { class: "glass dx-list dx-log" }, el("summary", { class: "dx-label" }, "Recent Problems In MIA's Log · " + (data.problems || []).length),
        ...((data.problems || []).length ? data.problems.map((p) => el("div", { class: "dx-log-row " + p.level },
          el("span", { class: "dx-dot " + (p.level === "error" ? "bad" : "look"), "aria-hidden": "true" }),
          el("div", {}, el("div", { class: "dx-log-text" }, p.text), el("div", { class: "dim" }, p.when + " · " + p.where))))
          : [el("p", { class: "dim" }, "No warnings or errors lately.")])),
      repoPanel(data.repository),
      ...selfPanels(data.self),
      capabilitiesPanel(data.capabilities),
      el("p", { class: "dim dx-foot" }, "Looks only. Nothing is probed or changed. Anything it couldn't read is never counted as a pass. "
        + "You can also ask her: \"check my PC\", \"check the network\"."),
      el("button", { type: "button", class: "btn btn-ghost", onclick: async () => paint(await MIA.diagnostics()) }, "Run Again"),
    ].filter(Boolean));
  }

  MIAShell.start(async () => { paint(await MIA.diagnostics()); });
})();
