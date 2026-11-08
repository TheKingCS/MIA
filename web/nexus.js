/*
 * nexus.js — the Nexus (DEC-0130, claude, 2026-11-08).
 * Draws MIA.nexus() (core/web_nexus.nexus): a portal per area on MIASpatial.ring, each in its hue and glowing amber
 * with a count when something inside needs you; the HUD (Today, Browser, Settings, Search, MIA; you, your level and
 * XP); the vapor in the areas' hues. Going through a portal opens that area's hub. By voice: "take me to the garage".
 * Where the graphics card allows and motion is welcome, the room (web/nexus3d.js) draws the portals instead, with the
 * chosen one's card beside it; the links stay underneath for the keyboard and screen readers. ?flat keeps the flat one.
 */
(function () {
  "use strict";
  const { el } = MIAShell;
  const $ = (id) => document.getElementById(id);
  const icon = (name) => (window.MIAIcons && MIAIcons.svg(name)) || null;
  let ring = null;
  let room = null;   // the 3D room now showing ({scene, nodes}), so a re-render replaces it instead of stacking another
  let keysOn = false;

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
    // The flat Nexus (reduced motion, no WebGL 2) shows the area's picture too when Muse's is in (H-0096); else its icon.
    const frame = el("span", { class: "portal-frame" + (p.art ? " has-art" : "") },
      p.art ? el("span", { class: "portal-art", "aria-hidden": "true", style: "background-image:url('" + p.art + "')" }) : null,
      el("span", { class: "portal-glass", "aria-hidden": "true" }),
      p.art ? null : el("span", { class: "portal-ico", "aria-hidden": "true" }, icon(p.icon)));
    if (p.needs) frame.append(el("span", { class: "portal-needs" }, p.needs + " need" + (p.needs === 1 ? "s" : "") + " you"));
    const a = el("a", { class: "portal", href: p.page, role: "listitem", style: "--hue:" + p.hue,
      "aria-label": p.name + (p.needs ? ", " + p.needs + " need you" : "") + ". " + p.line }, frame, el("span", { class: "portal-name" }, p.name));
    return a;
  }

  const needsText = (p) => p.needs ? p.needs + (p.needs === 1 ? " needs you" : " need you") : "Nothing needs you here";

  // The chosen portal's card (the room only): its name, its line, what needs you, and Enter. Clean page text.
  function card(box, p, go) {
    const head = el("div", { class: "n3-card-head", style: "--hue:" + p.hue },
      el("span", { class: "n3-card-ico", "aria-hidden": "true" }, icon(p.icon)), el("h2", {}, p.name));
    box.style.setProperty("--hue", p.hue);
    box.replaceChildren(head, el("p", { class: "n3-card-line" }, p.line),
      el("p", { class: "n3-card-needs" + (p.needs ? " attn" : "") }, needsText(p)),
      el("button", { type: "button", class: "btn n3-enter", onclick: go }, "Enter ", el("span", { "aria-hidden": "true" }, "›")));
  }

  MIAShell.start(async () => {
    const page = await MIA.nexus();
    hud(page);
    const items = page.portals.map(portal);
    $("ring").replaceChildren(...items);
    const remembered = (() => { try { return sessionStorage.getItem("mia.nexus.front"); } catch (e) { return null; } })();
    const start = ring ? ring.front % page.portals.length : Math.max(0, page.portals.findIndex((p) => p.id === remembered));
    if (room) { room.scene.stop(); room.nodes.forEach((x) => x.remove()); room = null; }

    // The room (web/nexus3d.js) where the graphics card can draw it and motion is welcome; ?flat keeps the flat one.
    let scene = null;
    const box = el("aside", { class: "n3-card", "aria-hidden": "true" });
    const goIn = (i) => {
      const p = page.portals[i];
      try { sessionStorage.setItem("mia.arrive", p.hue); } catch (e) { /* fine: you just arrive without the light */ }
      if (scene) scene.enter(i, p.page); else MIASpatial.enter(items[i], p.page, p.hue);
    };
    if (window.MIANexus3D && MIANexus3D.supported() && !/[?&]flat\b/.test(location.search)) {
      const canvas = el("canvas", { class: "n3-canvas", "aria-hidden": "true" });
      const labels = el("div", { class: "n3-labels", "aria-hidden": "true" });
      $("app").prepend(canvas, labels);
      $("app").append(box);
      scene = MIANexus3D.mount(canvas, page.portals, {
        start, labels, theme: MIAShell.roomLight(),
        onPick: (i) => (ring && i === ring.front ? goIn(i) : ring && ring.go(i)),
        onOrb: () => MIAShell.talk(true),
        onDrop: (i) => ring && ring.go(i),
      });
      if (scene) { document.body.classList.add("nexus-3d"); room = { scene, nodes: [canvas, labels, box] }; }
      else { canvas.remove(); labels.remove(); box.remove(); }
    }
    if (!scene) MIASpatial.vapor($("vapor"), page.portals.map((p) => p.hue));

    ring = MIASpatial.ring($("ring"), items, {
      start,
      radius: () => (innerWidth < 640 ? 420 : 760),
      onTurn: (i) => {
        const p = page.portals[i];
        $("here-name").textContent = p.name;
        $("here-line").textContent = p.needs ? needsText(p) + " · " + p.line : p.line;
        if (scene) { scene.focus(i); card(box, p, () => goIn(i)); }
        try { sessionStorage.setItem("mia.nexus.front", p.id); } catch (e) { /* fine */ }
      },
      onEnter: (node, i) => goIn(i),
    });
    $("prev").onclick = () => ring.turn(-1);
    $("next").onclick = () => ring.turn(1);
    $("orb").onclick = () => MIAShell.talk(true);
    if (scene && !keysOn) {  // in the room, the arrows turn it from anywhere on the page (once, whatever re-renders)
      keysOn = true;
      document.addEventListener("keydown", (e) => {
        if (e.defaultPrevented || $("ring").contains(e.target) || /^(INPUT|TEXTAREA|SELECT)$/.test(e.target.tagName)) return;
        if (e.target.closest && e.target.closest("dialog, .talk, [role=dialog]")) return;
        if (e.key === "ArrowRight") { e.preventDefault(); ring.turn(1); }
        if (e.key === "ArrowLeft") { e.preventDefault(); ring.turn(-1); }
      });
    }
  });
})();
