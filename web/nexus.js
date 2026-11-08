/*
 * nexus.js — the Nexus (DEC-0130, claude, 2026-11-08).
 * Draws MIA.nexus() (core/web_nexus.nexus): a portal per area on MIASpatial.ring, each in its hue and glowing amber
 * with a count when something inside needs you; the HUD (Today, Browser, Settings, Search, MIA; you, your level and
 * XP); the vapor in the areas' hues. Going through a portal opens that area's hub. By voice: "take me to the garage".
 */
(function () {
  "use strict";
  const { el } = MIAShell;
  const $ = (id) => document.getElementById(id);
  const icon = (name) => (window.MIAIcons && MIAIcons.svg(name)) || null;
  let ring = null;

  function hud(page) {
    const link = (href, label, ico) => el("a", { href, "aria-label": label }, icon(ico), el("span", { class: "nav-label" }, label));
    $("hud-nav").replaceChildren(
      link("index.html?today=1", "Today", "calendar"),
      link("browser.html", "Browser", "search"),
      link("settings.html", "Settings", "settings"),
      el("button", { type: "button", "aria-label": "Search", onclick: () => MIAShell.search() }, icon("search"), el("span", { class: "nav-label" }, "Search")),
      el("button", { type: "button", "aria-label": "Talk to MIA", onclick: () => MIAShell.talk(true) }, icon("mia"), el("span", { class: "nav-label" }, "MIA")));
    const h = page.hud;
    const pct = h.xp_for_level ? Math.round(100 * h.xp_into_level / h.xp_for_level) : 0;
    $("me").replaceChildren(
      el("span", { class: "me-face", "aria-hidden": "true" }, (h.name || "?").trim().charAt(0).toUpperCase()),
      el("span", { class: "me-line" }, "LV " + h.level + (h.missions ? " · " + h.missions + " mission" + (h.missions === 1 ? "" : "s") : "")),
      el("span", { class: "me-xp", role: "img", "aria-label": pct + "% of the way to level " + (h.level + 1) }, el("span", { style: "width:" + pct + "%" })));
  }

  function portal(p) {
    // The glass inside the frame holds the swirl: its own flat, clipped layer (3D space turns clipping off).
    const frame = el("span", { class: "portal-frame" }, el("span", { class: "portal-glass", "aria-hidden": "true" }),
      el("span", { class: "portal-ico", "aria-hidden": "true" }, icon(p.icon)));
    if (p.needs) frame.append(el("span", { class: "portal-needs" }, p.needs + " need" + (p.needs === 1 ? "s" : "") + " you"));
    const a = el("a", { class: "portal", href: p.page, role: "listitem", style: "--hue:" + p.hue,
      "aria-label": p.name + (p.needs ? ", " + p.needs + " need you" : "") + ". " + p.line }, frame, el("span", { class: "portal-name" }, p.name));
    return a;
  }

  MIAShell.start(async () => {
    const page = await MIA.nexus();
    hud(page);
    const items = page.portals.map(portal);
    $("ring").replaceChildren(...items);
    MIASpatial.vapor($("vapor"), page.portals.map((p) => p.hue));
    const remembered = (() => { try { return sessionStorage.getItem("mia.nexus.front"); } catch (e) { return null; } })();
    const start = Math.max(0, page.portals.findIndex((p) => p.id === remembered));
    ring = MIASpatial.ring($("ring"), items, {
      start,
      radius: () => (innerWidth < 640 ? 420 : 760),
      onTurn: (i) => {
        const p = page.portals[i];
        $("here-name").textContent = p.name;
        $("here-line").textContent = p.needs ? p.needs + " need" + (p.needs === 1 ? "s" : "") + " you · " + p.line : p.line;
        try { sessionStorage.setItem("mia.nexus.front", p.id); } catch (e) { /* fine */ }
      },
      onEnter: (node, i) => MIASpatial.enter(node, page.portals[i].page, page.portals[i].hue),
    });
    $("prev").onclick = () => ring.turn(-1);
    $("next").onclick = () => ring.turn(1);
    $("orb").onclick = () => MIAShell.talk(true);
  });
})();
