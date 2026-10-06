/*
 * dashboard.js — Home (claude, 2026-10-06, DEC-0017). Renders MIA.home();
 * every number and sentence is the engine's. Ticking a focus item runs its
 * action through MIAShell.act (propose → confirm → approve → undo).
 */
(function () {
  "use strict";
  const { el, act, talk } = MIAShell;
  const $ = (id) => document.getElementById(id);

  function focusRow(item) {
    const what = el("span", { class: "what" },
      item.page ? el("a", { href: item.page }, item.title) : item.title,
      item.detail || item.time ? el("small", {}, [item.time, item.detail].filter(Boolean).join(" · ")) : null);
    const tick = el("button", {
      type: "button", class: "tick", disabled: !item.action,
      "aria-label": item.action ? item.action.label + ": " + item.title : item.title,
      title: item.action ? item.action.label : "Open it to deal with this",
      onclick: () => act(item.action),
    });
    return el("li", { class: item.when }, tick, el("span", { "aria-hidden": "true" }, item.icon || "•"), what);
  }

  async function render() {
    const home = await MIA.home();
    $("greeting").textContent = home.greeting;
    $("subtitle").textContent = home.subtitle;
    $("date").textContent = home.date;
    $("saying").textContent = "“" + home.saying + "”";

    $("focus").replaceChildren(...home.focus.map(focusRow));
    $("focus-empty").hidden = home.focus.length > 0;
    $("focus-count").textContent = home.focus.length ? home.focus.length + " to do" : "";

    $("upcoming").replaceChildren(...home.upcoming.map(focusRow));
    $("upcoming-empty").hidden = home.upcoming.length > 0;

    $("wins").replaceChildren(...home.wins.map((w) => el("li", {}, w.summary)));
    $("wins-empty").hidden = home.wins.length > 0;

    $("quick").replaceChildren(...home.quick_actions.map((q) =>
      el("button", { type: "button", onclick: () => talk(true, q.talk) },
        el("span", { "aria-hidden": "true" }, q.icon), q.label)));

    $("glance").replaceChildren(...home.glance.map((c) => {
      const card = el("section", { class: "glass" + (c.tone === "attention" ? " attention" : "") },
        el("h3", {}, el("span", { "aria-hidden": "true" }, c.icon), c.title), el("p", {}, c.line));
      return c.page ? el("a", { href: c.page }, card) : card;
    }));
  }

  MIAShell.start(render);
})();
