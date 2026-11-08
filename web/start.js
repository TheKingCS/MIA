/*
 * start.js — Start Here (claude, 2026-11-07). Renders MIA.guide() (core/web_guide.py): what she does, grouped by what
 * you want to get done; each with how it works, "Try saying" buttons that open Talk with the words typed in (press
 * Enter to send), and the page to open; the apps still empty, to fill in; then what's new. Formatting only; the look is muse's.
 */
(function () {
  "use strict";
  const { el } = MIAShell;
  const $ = (id) => document.getElementById(id);

  function topic(t) {
    return el("section", { class: "glass money-section guide-topic", id: "topic-" + t.id },
      el("h2", {}, t.title),
      el("p", {}, t.how),
      el("p", { class: "dim" }, "Try saying:"),
      el("div", { class: "row-buttons guide-say" }, t.say.map((s) =>
        el("button", { type: "button", class: "btn btn-ghost btn-small", title: "Opens Talk with this typed in",
          onclick: () => MIAShell.talk(true, s) }, "“" + s + "”"))),
      t.page && t.page !== "index.html"
        ? el("div", { class: "row-buttons" }, el("a", { class: "btn btn-green btn-small", href: t.page }, "Open"))
        : null);
  }

  // Still empty (2026-11-07): the apps with nothing in them yet, each with the first thing to say or its page. The
  // more of your life MIA holds, the more she can help.
  function fill(apps) {
    if (!apps.length) return null;
    return el("section", { class: "glass money-section guide-fill" },
      el("h2", {}, "Fill In Your Life"),
      el("p", { class: "dim" }, "These are still empty. Each one you fill makes MIA more useful: say the line, or open the page."),
      el("div", { class: "rows" }, apps.map((a) => el("div", { class: "row" },
        el("div", {}, el("div", { class: "row-title" }, a.title)),
        el("span", { class: "row-buttons" },
          ...a.say.map((s) => el("button", { type: "button", class: "btn btn-ghost btn-small", title: "Opens Talk with this typed in",
            onclick: () => MIAShell.talk(true, s) }, "“" + s + "”")),
          el("a", { class: "btn btn-ghost btn-small", href: a.page }, "Open"))))));
  }

  async function draw() {
    const data = await MIA.guide();
    $("panel").replaceChildren(
      el("section", { class: "glass money-section" },
        el("p", {}, "MIA works by talking: the glowing orb at the bottom right of every page opens Talk. "
          + "Every page in the sidebar is also a screen you can use directly. Below, by what you want to do: "
          + "tap a \"Try saying\" button to put the words in Talk, then press Enter."),
        el("div", { class: "row-buttons" }, data.topics.map((t) =>
          el("a", { class: "chip chip-button", href: "#topic-" + t.id }, t.title)))),
      fill(data.to_fill || []),
      el("section", { class: "glass money-section" }, el("h2", {}, "What's New"),
        el("ul", {}, data.new.map((n) => el("li", {},
          n.page && n.page !== "start.html" ? el("a", { href: n.page }, n.what) : n.what)))),
      ...data.topics.map(topic));
  }

  MIAShell.start(draw);
})();
