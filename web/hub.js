/*
 * hub.js — an area's hub (DEC-0129, claude, 2026-11-08).
 * Renders MIA.hub(area) (core/web_areas.hub): the area's apps and pages as tiles, each opening its own page, then the
 * other areas to jump to. Which apps are in which area is decided in core; this only lays them out.
 */
(function () {
  "use strict";
  const { el } = MIAShell;
  const $ = (id) => document.getElementById(id);
  const area = new URLSearchParams(location.search).get("area") || "home";

  function tile(a) {
    const ico = el("span", { class: "hub-ico", "aria-hidden": "true" });
    const pic = window.MIAIcons && (MIAIcons.svg(a.id) || MIAIcons.svg(a.icon));  // the app's own icon, else the page's
    if (pic) ico.append(pic); else ico.textContent = "•";
    return el("a", { class: "glass hub-tile", href: a.page }, ico,
      el("span", { class: "hub-name" }, a.name), el("span", { class: "hub-line" }, a.tagline || ""));
  }

  function paint(h) {
    document.title = h.name + " — MIA";
    $("hub-name").textContent = h.name;
    $("hub-sub").textContent = h.tagline;
    $("panel").replaceChildren(
      h.apps.length ? el("div", { class: "hub-grid" }, h.apps.map(tile)) : el("p", { class: "empty" }, "Nothing here yet."),
      el("nav", { class: "hub-areas", "aria-label": "Other areas" },
        h.areas.filter((x) => x.id !== h.id).map((x) => el("a", { class: "btn btn-ghost btn-small", href: "hub.html?area=" + x.id }, x.name))));
  }

  MIAShell.start(async () => { paint(await MIA.hub(area)); });
})();
