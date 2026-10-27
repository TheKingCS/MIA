/*
 * issues.js — the Fix-It Log (claude, 2026-10-27, DEC-0049). Renders
 * MIA.failures() (core/failure_actions.py): open issues first, worst first,
 * each with what happened (the latest examples) and Mark Fixed / Ignore;
 * what MIA learned you mean, with Forget; Report A Problem; and the fix
 * report, ready for Claude to turn into tests. Formatting only.
 */
(function () {
  "use strict";
  const { el, act, form, say } = MIAShell;
  const $ = (id) => document.getElementById(id);
  const btn = (label, cls, onclick) => el("button", { type: "button", class: "btn " + cls, onclick }, label);
  const section = (title, aside, ...body) =>
    el("section", { class: "glass money-section" }, el("div", { class: "sect" }, el("h2", {}, title), aside), ...body);
  const when = (iso) => iso ? new Date(iso).toLocaleString(undefined, { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" }) : "";
  const LABEL = { before: "First asked", prompt: "Asked", reply: "MIA said", note: "Note", error: "Error", tools: "Tools", seconds: "Seconds" };

  async function report() {
    const v = await form("Report A Problem", [{ name: "note", label: "What went wrong?", type: "textarea", required: true }], {});
    if (v) act({ kind: "failures.report", params: { note: v.note, page: "issues.html" } });
  }

  function example(e) {
    return el("div", { class: "fx-example" }, el("div", { class: "dim" }, when(e.at)),
      ...["before", "prompt", "reply", "note", "error", "tools", "seconds"].filter((k) => e[k] != null && e[k] !== "")
        .map((k) => el("div", {}, el("b", {}, LABEL[k] + ": "), Array.isArray(e[k]) ? e[k].join(", ") : String(e[k]))));
  }

  function issue(i) {
    const set = (status) => act({ kind: "failures.status", params: { key: i.key, status } });
    return el("article", { class: "glass money-section fx-issue " + i.status },
      el("div", { class: "row-title" }, i.title + " · " + i.count + "×" + (i.reopened ? " · came back" : "")),
      el("div", { class: "row-sub dim" }, i.said.join(" · ") + " · last " + when(i.last)),
      el("details", {}, el("summary", {}, "What happened"), ...i.examples.map(example)),
      el("div", { class: "row-buttons" }, i.status === "open"
        ? [btn("Mark Fixed", "btn-ghost btn-small", () => set("fixed")), btn("Ignore", "btn-ghost btn-small", () => set("ignored"))]
        : btn("Open Again", "btn-ghost btn-small", () => set("open"))));
  }

  MIAShell.start(async () => {
    const p = await MIA.failures();
    if (!p.available) { $("panel").replaceChildren(el("p", { class: "empty" }, "The Fix-It Log isn't set up on this MIA.")); return; }
    const s = p.summary;
    $("strip").replaceChildren(
      el("div", { class: "cell " + (s.open ? "soon" : "ok") }, el("span", { class: "n" }, s.open), el("span", { class: "t" }, "Open")),
      el("div", { class: "cell ok" }, el("span", { class: "n" }, s.this_week), el("span", { class: "t" }, "This Week")),
      el("div", { class: "cell ok" }, el("span", { class: "n" }, s.fixed), el("span", { class: "t" }, "Fixed")),
      el("div", { class: "cell ok" }, el("span", { class: "n" }, s.learned), el("span", { class: "t" }, "Learned")));
    const open = p.issues.filter((i) => i.status === "open");
    const done = p.issues.filter((i) => i.status !== "open");
    $("panel").replaceChildren(
      section("Open Issues", btn("Report A Problem", "btn-amber btn-small", report),
        open.length ? el("div", { class: "fx-list" }, open.map(issue))
          : el("p", { class: "empty" }, "Nothing's gone wrong lately that MIA knows of. Tap 👎 under an answer, or say “report a problem”, when something does."),
        el("p", { class: "dim" }, "MIA notices on her own too: errors, a request she couldn't match, asking again in other words, an undo right after she acted, slow answers, a page that broke.")),
      p.phrases.length ? section("What MIA Learned You Mean", null,
        el("p", { class: "dim" }, "Only what you confirmed. Teach her more: “when I say got off work, I mean log my shift”."),
        el("ul", { class: "dg-runs" }, p.phrases.map((ph) => el("li", { class: "dg-run" },
          el("div", {}, el("div", { class: "row-title" }, "“" + ph.said + "”"), el("div", { class: "row-sub dim" }, ph.meaning || ph.does)),
          el("div", { class: "row-buttons" }, btn("Forget", "btn-ghost btn-small", () => act({ kind: "failures.forget", params: { phrase_id: ph.phrase_id } }))))))) : null,
      p.report ? section("Fix Report For Claude", btn("Copy", "btn-ghost btn-small", () => {
          (navigator.clipboard ? navigator.clipboard.writeText(p.report) : Promise.reject()).then(() => say("Copied."), () => say("Select the text to copy it."));
        }),
        el("p", { class: "dim" }, "Claude reads this on your PC and turns each issue into a test before fixing it. It stays on your devices."),
        el("pre", { class: "fx-report" }, p.report)) : null,
      done.length ? section("Fixed And Ignored", null, el("div", { class: "fx-list" }, done.map(issue))) : null);
  });
})();
