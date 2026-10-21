/*
 * welcome.js — Home (DEC-0018, claude). Renders MIA.dashboard() and the
 * frame's shell data; ticking a focus item runs its action (confirm, undo).
 * DEC-0044: Home is Presence: what matters now across everything
 * (core/presence.py), ranked, each with why and what kind of thing it is
 * (a deadline, a fact, a suggestion), the next useful action marked; then
 * progress on your path.
 */
(function () {
  "use strict";
  const { el, act } = MIAShell;
  const $ = (id) => document.getElementById(id);
  if (window.MIAIcons) MIAIcons.badge($("gear"), "settings");  // the line icon (DEC-0023)

  const KIND = { deadline: "deadline", fact: "fact", suggestion: "suggestion", progress: "progress" };
  function presenceRow(item, next) {
    return el("li", { class: "pres-item " + item.kind + (item.urgency >= 85 ? " urgent" : "") + (next ? " pres-next" : "") },
      el("span", { class: "pres-kind" }, next ? "next" : KIND[item.kind] || item.kind),
      el("span", { class: "what" }, item.href ? el("a", { href: item.href }, item.title) : item.title,
        el("small", {}, [item.why, item.detail].filter(Boolean).join(" · "))),
      item.action ? el("button", { type: "button", class: "btn btn-green btn-small", onclick: () => act(item.action) }, item.action.label)
        : item.href ? el("a", { class: "btn btn-ghost btn-small", href: item.href }, "Open") : null);
  }

  async function render() {
    const [home, shell] = await Promise.all([MIA.dashboard(), MIA.shell()]);
    $("greeting").textContent = home.greeting;
    const pres = home.presence || { now: [], path: [] };
    $("subtitle").textContent = pres.line || home.subtitle;
    const nextKey = pres.next && pres.next.key;
    $("focus").replaceChildren(...pres.now.map((i) => presenceRow(i, i.key === nextKey)));
    $("focus-empty").hidden = pres.now.length > 0;
    $("focus-more").hidden = !pres.more;
    $("focus-more").textContent = pres.more ? pres.more + " more in World." : "";
    $("path").hidden = !pres.path.length;
    $("path-list").replaceChildren(...pres.path.map((i) => presenceRow(i, false)));
    // MIA Remembers (DEC-0029): what you told her, as it's about to matter.
    const remember = home.remember || [];
    $("remember").hidden = !remember.length;
    $("remember-list").replaceChildren(...remember.map((r) => el("li", {},
      el("a", { href: r.page }, el("span", { "aria-hidden": "true" }, r.icon + " "), r.title),
      ...r.lines.map((line) => el("small", {}, line)))));
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
