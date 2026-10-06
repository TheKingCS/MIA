/*
 * welcome.js — Home (DEC-0018, claude). Renders MIA.dashboard() and the
 * frame's shell data; ticking a focus item runs its action (confirm, undo).
 */
(function () {
  "use strict";
  const { el, act } = MIAShell;
  const $ = (id) => document.getElementById(id);
  const SHOWN = ["voice", "calendar", "journal", "assistant"];

  function focusRow(item) {
    return el("li", { class: item.when },
      el("button", { type: "button", class: "tick", disabled: !item.action,
        "aria-label": item.action ? item.action.label + ": " + item.title : item.title,
        title: item.action ? item.action.label : "Open it to deal with this", onclick: () => act(item.action) }),
      el("span", { class: "what" },
        item.page ? el("a", { href: item.page }, item.title) : item.title,
        item.detail ? el("small", {}, item.detail) : null));
  }

  async function render() {
    const [home, shell] = await Promise.all([MIA.dashboard(), MIA.shell()]);
    $("greeting").textContent = home.greeting;
    $("subtitle").textContent = home.subtitle;
    $("date-chip").textContent = home.date;
    $("saying").textContent = home.saying;
    $("focus").replaceChildren(...home.focus.slice(0, 6).map(focusRow));
    $("focus-empty").hidden = home.focus.length > 0;
    $("quick").replaceChildren(...home.quick_actions.filter((q) => SHOWN.includes(q.id)).map((q) =>
      el("a", { class: "glass quick-tile", href: q.href }, el("span", { class: "ico", "aria-hidden": "true" }, q.icon), q.label)));
    const p = shell.person;
    const pct = p.xp_for_level ? Math.round((100 * p.xp_into_level) / p.xp_for_level) : 0;
    $("level").replaceChildren(
      el("span", { class: "home-avatar", "aria-hidden": "true" }, "🧙"),
      el("span", { class: "home-level-text" }, el("strong", {}, "lvl " + p.level), el("small", {}, p.total_xp + " XP")),
      el("span", { class: "xpbar" }, el("span", { class: "xpbar-track" }, el("span", { class: "xpbar-fill", style: "width:" + pct + "%" }))));
  }

  MIAShell.start(render);
})();
