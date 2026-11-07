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
    // The design canvas (DEC-0113): the title with how many times on the right, the latest thing said, what happened
    // folded under it, and Mark Fixed / Ignore.
    const latest = i.examples.length ? i.examples[i.examples.length - 1] : null;
    const said = latest && (latest.prompt || latest.before || latest.note);
    return el("article", { class: "glass fx-card " + i.status + (i.weight >= 3 && i.status === "open" ? " worst" : "") },
      el("div", { class: "fx-top" }, el("span", { class: "fx-title" }, i.title + (i.reopened ? " · came back" : "")),
        el("span", { class: "fx-n" }, "×" + i.count)),
      said ? el("p", { class: "fx-latest" }, "Latest: “" + said + "”") : null,
      el("p", { class: "fx-said" }, i.said.join(" · ") + " · last " + when(i.last)),
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
    $("panel").replaceChildren(...[
      el("button", { type: "button", class: "btn btn-big btn-green fx-report-btn", onclick: report }, "Report a Problem"),
      el("h2", { class: "fx-label" }, "Open · Worst First"),
      open.length ? el("div", { class: "fx-list" }, open.map(issue))
        : el("p", { class: "empty" }, "Nothing's gone wrong lately that MIA knows of. Tap 👎 under an answer, or say “report a problem”, when something does."),
      el("p", { class: "dim fx-note" }, "MIA notices on her own too: errors, a request she couldn't match, asking again in other words, an undo right after she acted, slow answers, a page that broke."),
      p.phrases.length ? el("section", { class: "glass fx-learned", "aria-label": "What MIA learned" },
        el("span", { class: "fx-label" }, "What MIA Learned You Mean"),
        ...p.phrases.map((ph) => el("div", { class: "fx-phrase" },
          el("span", {}, "“" + ph.said + "” → " + (ph.meaning || ph.does)),
          btn("Forget", "btn-ghost btn-small", () => act({ kind: "failures.forget", params: { phrase_id: ph.phrase_id } })))),
        el("p", { class: "dim fx-note" }, "Only what you confirmed. Teach her more: “when I say got off work, I mean log my shift”.")) : null,
      p.report ? section("Fix Report For Claude", btn("Copy", "btn-ghost btn-small", () => {
          (navigator.clipboard ? navigator.clipboard.writeText(p.report) : Promise.reject()).then(() => say("Copied."), () => say("Select the text to copy it."));
        }),
        el("p", { class: "dim" }, "Claude reads this on your PC and turns each issue into a test before fixing it. It stays on your devices."),
        el("pre", { class: "fx-report" }, p.report)) : null,
      done.length ? section("Fixed And Ignored", null, el("div", { class: "fx-list" }, done.map(issue))) : null].filter(Boolean));
  });
})();
