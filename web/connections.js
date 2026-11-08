/*
 * connections.js — Connections (claude, 2026-11-08, DEC-0146).
 * Renders MIA.connections() (core/web_connections.py): the ties MIA is holding
 * (what you said, when, the project, goal or idea from weeks ago it ties into, and
 * how, and what she found about it first in her own offline sources, each with where it
 * came from), what became of the recent ones, and the things she's been asked never to
 * tie into. Don't Bring It Up and Allow Again are connection.* actions, undoable.
 */
(function () {
  "use strict";
  const { el } = MIAShell;
  const $ = (id) => document.getElementById(id);
  const button = (label, onclick, cls) => el("button", { type: "button", class: "btn " + (cls || "btn-ghost") + " btn-small", onclick }, label);
  const day = (iso) => iso ? new Date(iso + "T00:00:00").toLocaleDateString(undefined, { month: "short", day: "numeric" }) : "";

  function tie(c, live) {
    return el("article", { class: "glass cn-tie" + (live ? "" : " settled") },
      el("p", { class: "cn-said" }, "“" + c.said + "”", el("span", { class: "dim" }, "  · " + day(c.noticed))),
      el("div", { class: "cn-link", "aria-hidden": "true" }, el("span", { class: "cn-line" }), el("span", { class: "cn-node" })),
      el("p", { class: "cn-target" }, el("span", { class: "dim" }, "ties into your " + c.kind + " "), el("b", {}, c.name),
        c.since ? el("span", { class: "dim" }, ", started " + day(c.since) + (c.status ? ", still " + c.status : "")) : null),
      c.how ? el("p", { class: "dim cn-how" }, c.how) : null,
      (c.found || []).length ? el("div", { class: "cn-found" },
        el("p", { class: "pw-label" }, "What She Found First"),
        ...c.found.map((f) => el("p", { class: "cn-found-line" }, f.line[0].toUpperCase() + f.line.slice(1) + ".",
          el("span", { class: "dim" }, "  · " + f.source)))) : null,
      el("div", { class: "cn-foot" },
        el("span", { class: "cn-state " + c.state }, c.state_word),
        c.state !== "declined" ? button("Don't Bring It Up", () => MIAShell.act({ kind: "connection.decline", params: { connection_id: c.id } }), "btn-quiet") : null));
  }

  function paint(data) {
    if (!data.available) { $("cn-sub").textContent = "Connections aren't kept on this MIA."; $("panel").replaceChildren(); return; }
    $("cn-sub").textContent = "Something you said in passing can matter to a thing you started weeks ago. She brings it up once, if it fits, then lets it go.";
    $("panel").replaceChildren(...[
      el("p", { class: "pw-label" }, data.waiting.length ? "Waiting to Come Up · " + data.waiting.length : "Nothing Waiting"),
      data.waiting.length ? el("section", { class: "cn-list" }, ...data.waiting.map((c) => tie(c, true)))
        : el("p", { class: "dim" }, "When something you say ties into an older project, goal or idea, it shows here first."),
      data.recent.length ? el("p", { class: "pw-label cn-gap" }, "Lately") : null,
      data.recent.length ? el("section", { class: "cn-list" }, ...data.recent.map((c) => tie(c, false))) : null,
      data.quiet.length ? el("p", { class: "pw-label cn-gap" }, "Not to Be Raised") : null,
      data.quiet.length ? el("section", { class: "glass cn-quiet" }, ...data.quiet.map((q) => el("div", { class: "cn-quiet-row" },
        el("span", {}, q.name), button("Allow Again", () => MIAShell.act({ kind: "connection.allow", params: { ref: q.ref } }, { quick: true }))))) : null,
      el("p", { class: "dim cn-say" }, "Say \"don't bring that up\" right after she raises one, or \"what connections have you noticed?\" any time."),
    ].filter(Boolean));
  }

  MIAShell.start(async () => { paint(await MIA.connections()); }, { refreshOnChange: true });
})();
