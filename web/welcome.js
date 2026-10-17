/*
 * welcome.js — Home (DEC-0018, claude). Renders MIA.dashboard() and the
 * frame's shell data; ticking a focus item runs its action (confirm, undo).
 */
(function () {
  "use strict";
  const { el, act } = MIAShell;
  const $ = (id) => document.getElementById(id);
  if (window.MIAIcons) MIAIcons.badge($("gear"), "settings");  // the line icon (DEC-0023)

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
    $("focus").replaceChildren(...home.focus.slice(0, 6).map(focusRow));
    $("focus-empty").hidden = home.focus.length > 0;
    const buffs = MIAShell.buffChips(home.buffs, true);
    $("buffs").replaceChildren(...(buffs ? [buffs] : []));
    $("buffs").hidden = !buffs;
    $("upcoming").replaceChildren(...home.upcoming.map(focusRow));
    $("upcoming-empty").hidden = home.upcoming.length > 0;
    const p = shell.person;
    const pct = p.xp_for_level ? Math.round((100 * p.xp_into_level) / p.xp_for_level) : 0;
    $("level").replaceChildren(
      el("span", { class: "home-avatar", "aria-hidden": "true" }, "🧙"),
      el("span", { class: "home-level-text" }, el("strong", {}, "lvl " + p.level), el("small", {}, p.total_xp + " XP")),
      el("span", { class: "xpbar" }, el("span", { class: "xpbar-track" }, el("span", { class: "xpbar-fill", style: "width:" + pct + "%" }))));
  }

  // The gear: Profile, Settings, Log out (Zac, 2026-10-07).
  const gear = $("gear"), menu = $("account-dropdown");
  const openMenu = (open) => { menu.hidden = !open; gear.setAttribute("aria-expanded", String(open)); };
  gear.addEventListener("click", (e) => { e.stopPropagation(); openMenu(menu.hidden); });
  document.addEventListener("click", (e) => { if (!menu.hidden && !menu.contains(e.target)) openMenu(false); });
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") openMenu(false); });
  $("logout").addEventListener("click", async () => {
    await MIA.signOut();
    location.replace("index.html");  // no #token: back to sign-in
  });

  MIAShell.start(render);
})();
