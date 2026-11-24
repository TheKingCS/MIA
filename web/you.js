/*
 * you.js — The Picture of You (DEC-0290, claude, 2026-11-23).
 * Renders MIA.picture() (core/picture_of_you.py): what MIA remembers about you, grouped, each with how she knows it
 * and where it came from, with Fix and Forget (memory.fix, memory.forget: undoable); your skills by level; what
 * you're learning and the stage; how you like answers. Formatting only; every fact and every change is the engine's.
 */
(function () {
  "use strict";
  const { el } = MIAShell;
  const $ = (id) => document.getElementById(id);

  async function fix(item) {
    const text = window.prompt("What should I remember instead?", item.text);
    if (text && text.trim() && text.trim() !== item.text) {
      await MIAShell.act({ kind: "memory.fix", params: { memory_id: item.id, text: text.trim() } });
      draw();
    }
  }
  async function forget(item) {
    await MIAShell.act({ kind: "memory.forget", params: { memory_id: item.id } });
    draw();
  }

  function memories(groups) {
    if (!groups.length) {
      return el("section", { class: "glass money-section" }, el("h2", {}, "What I Remember"),
        el("p", { class: "dim" }, "Nothing yet. As we talk, what matters is kept here, and you can fix or forget any of it."));
    }
    return el("section", { class: "glass money-section" }, el("h2", {}, "What I Remember"),
      ...groups.map((g) => el("div", { class: "you-group" }, el("p", { class: "pw-label" }, g.category),
        el("div", { class: "rows" }, ...g.items.map((m) => el("div", { class: "row" },
          el("div", {}, el("div", { class: "row-title" }, m.text),
            el("div", { class: "row-sub" }, [m.how, "from " + m.source, m.confirmed ? "confirmed" : null, m.since].filter(Boolean).join(" · "))),
          el("div", { class: "row-buttons" },
            el("button", { type: "button", class: "btn btn-ghost btn-small", onclick: () => fix(m) }, "Fix"),
            el("button", { type: "button", class: "btn btn-ghost btn-small", onclick: () => forget(m) }, "Forget"))))))));
  }

  function list(title, rows, empty, line) {
    return el("section", { class: "glass money-section" }, el("h2", {}, title),
      rows.length ? el("div", { class: "rows" }, ...rows.map((r) => el("div", { class: "row" }, el("div", {}, ...line(r)))))
        : el("p", { class: "dim" }, empty));
  }

  async function draw() {
    const data = await MIA.picture();
    $("you-sub").textContent = data.count ? data.count + " things I remember, and how I know each." : "What I know about you, and where it came from.";
    $("panel").replaceChildren(
      memories(data.memories || []),
      list("Your Skills", data.skills || [], "No skill XP yet: it comes from what you log and finish.",
        (s) => [el("div", { class: "row-title" }, s.name), el("div", { class: "row-sub" }, "level " + s.level + " · " + s.xp + " XP")]),
      list("What You're Learning", data.learning || [], "Nothing started. Say \"I want to learn woodworking\" to begin a path.",
        (p) => [el("a", { class: "row-title", href: "skills.html#paths" }, p.name), el("div", { class: "row-sub" }, "stage " + p.stage + " of " + p.of)]),
      list("How You Like Answers", (data.answers || []).filter((a) => a.lean), "Not learned yet: pick between two ways when she offers them.",
        (a) => [el("div", { class: "row-title" }, a.name + ": " + a.lean), el("div", { class: "row-sub" }, a.word)]),
      el("p", { class: "dim" }, "Say \"what do you know about me?\" any time. Fixing or forgetting one can be undone."));
  }

  MIAShell.start(draw);
})();
