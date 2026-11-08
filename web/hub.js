/*
 * hub.js — an area's hub (DEC-0129, claude, 2026-11-08).
 * Renders MIA.hub(area) (core/web_areas.hub): the area's apps and pages as tiles, each opening its own page, then the
 * other areas to jump to. Which apps are in which area is decided in core; this only lays them out. An area with its own
 * space (core/web_environments.py) draws that instead; the Garage's is a 3D room on the Nexus's engine where the
 * graphics card allows (garageRoom), its flat layout otherwise. Every other area is a room of its apps in the Spatial
 * look (areaRoom), its tiles otherwise.
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

  // ------------------------------------------------------------ an area's own space (DEC-0130 M3)
  // Garage (core/web_environments.garage): bays floating in a row (each vehicle or tool with its photo, what's overdue
  // and what's next), what needs you, the parts running low, and the bench's tools. Lit in the area's hue.
  function ico(name, fallback) { return (window.MIAIcons && (MIAIcons.svg(name) || MIAIcons.svg(fallback))) || null; }

  function bay(b) {
    const pic = b.photo ? el("img", { class: "bay-photo", alt: "", loading: "lazy" }) : el("span", { class: "bay-photo bay-blank", "aria-hidden": "true" }, ico("garage"));
    if (b.photo) MIA.image(b.photo).then((u) => { if (u) pic.src = u; });
    return el("a", { class: "bay" + (b.overdue ? " bay-due" : ""), href: b.page,
      "aria-label": b.name + (b.overdue ? ", " + b.overdue + " overdue" : "") + (b.next ? ", next: " + b.next.title + " " + b.next.text : "") },
      pic,
      el("span", { class: "bay-name" }, b.name),
      el("span", { class: "bay-sub" }, [b.category, b.make_model].filter(Boolean).join(" · ")),
      b.meter ? el("span", { class: "bay-meter" }, b.meter) : null,
      b.next ? el("span", { class: "bay-next" + (b.next.urgency === "overdue" ? " due" : "") }, b.next.title + " · " + b.next.text) : null,
      b.overdue ? el("span", { class: "bay-badge" }, b.overdue + " overdue") : null);
  }

  function garage(env) {
    if (!env.available) return [el("p", { class: "empty" }, "The Garage isn't set up on this MIA.")];
    return [
      env.needs.length ? el("section", { class: "holo env-needs", "aria-label": "Needs you" },
        el("h2", { class: "pw-label" }, "Needs You"),
        el("div", { class: "env-needs-row" }, env.needs.map((n) => el("a", { class: "env-need", href: n.page },
          el("strong", {}, n.title), el("span", {}, n.asset + " · " + n.text))))) : null,
      el("section", { class: "env-bays", "aria-label": "Bays" },
        el("div", { class: "env-head" }, el("h2", { class: "pw-label" }, "Bays · " + env.bays.length),
          el("a", { class: "btn btn-ghost btn-small", href: "garage.html" }, "Manage ›")),
        env.bays.length ? el("div", { class: "bay-row" }, env.bays.map(bay))
          : el("p", { class: "dim" }, "Add your vehicles, tools and equipment in the Garage and they'll park here.")),
      el("div", { class: "env-lower" },
        el("section", { class: "holo env-parts", "aria-label": "Parts running low" },
          el("h2", { class: "pw-label" }, "Parts Running Low"),
          env.parts.length ? el("div", { class: "rows" }, env.parts.map((p) => el("div", { class: "row money-row" },
            el("div", {}, el("div", { class: "row-title" }, p.name), el("div", { class: "row-sub" }, "For " + p.used_by.filter(Boolean).join(", "))),
            el("span", { class: "chip chip-soon" }, p.state === "out" ? "Out" : p.have + (p.unit ? " " + p.unit : "") + " left"))))
            : el("p", { class: "dim" }, "Nothing low. List what each vehicle uses on its Parts tab and MIA watches the shelf.")),
        el("section", { class: "holo env-bench", "aria-label": "The bench" },
          el("h2", { class: "pw-label" }, "The Bench"),
          el("div", { class: "bench-row" }, env.bench.map((t) => el("a", { class: "bench-tool", href: t.page },
            el("span", { class: "bench-ico", "aria-hidden": "true" }, ico(t.id, t.icon)), el("strong", {}, t.name), el("span", {}, t.line))))))];
  }

  const ENVIRONMENTS = { garage };

  // ------------------------------------------------------------ the Garage as a room (the Nexus's engine, web/nexus3d.js)
  // Its bays stand round MIA's orb as wide door frames, each with the vehicle's or tool's photo; a bay's floor glows
  // amber when something on it is overdue. Drag, swipe, the arrows or a click turn to a bay; its card (left) opens it.
  // What needs you, the parts running low and the bench are clean panels over the room. Coming from the Nexus, you
  // arrive out of the portal's light. Without WebGL 2 or with reduced motion, the flat Garage above shows instead.
  function bayCard(box, b) {
    box.replaceChildren(
      el("div", { class: "n3-card-head" }, el("span", { class: "n3-card-ico", "aria-hidden": "true" }, ico(b.category === "Vehicle" ? "garage" : "maintenance", "garage")),
        el("h2", {}, b.name)),
      el("p", { class: "n3-card-line" }, [b.category, b.make_model, b.meter].filter(Boolean).join(" · ") || "In the Garage"),
      b.next ? el("p", { class: "n3-card-needs" + (b.next.urgency === "overdue" ? " attn" : "") }, b.next.title + " · " + b.next.text)
        : el("p", { class: "n3-card-needs" }, "Nothing scheduled"),
      b.overdue > 1 ? el("p", { class: "n3-card-needs attn" }, b.overdue + " overdue") : null,
      el("a", { class: "btn n3-enter", href: b.page }, "Open ", el("span", { "aria-hidden": "true" }, "›")));
  }

  let room = null;   // the room now showing ({scene, nodes, ring}): a re-render (MIA's data changed) replaces it
  let keysOn = false;
  function garageRoom(h, env) {
    const front = room && room.ring ? room.ring.front : 0;
    if (room) { room.scene.stop(); room.nodes.forEach((x) => x.remove()); room = null; document.body.classList.remove("room-3d"); }
    if (!(window.MIARoom && MIARoom.supported()) || /[?&]flat\b/.test(location.search) || !env.available || !env.bays.length) return false;
    if (MIAShell.look && MIAShell.look() !== "spatial") return false;  // the cards look keeps the Garage's cards (DEC-0135)
    const links = env.bays.map((b) => el("a", { href: b.page, role: "listitem",
      "aria-label": b.name + (b.overdue ? ", " + b.overdue + " overdue" : "") + (b.next ? ", next: " + b.next.title + " " + b.next.text : "") }, b.name));
    const list = el("div", { class: "room-links", role: "list", "aria-label": "Bays, turn with the arrow keys" }, ...links);
    const canvas = el("canvas", { class: "n3-canvas", "aria-hidden": "true" });
    const labels = el("div", { class: "n3-labels", "aria-hidden": "true" });
    const card = el("aside", { class: "n3-card room-card", style: "--hue:" + h.hue });
    let arriveHue = null;
    try { arriveHue = sessionStorage.getItem("mia.arrive"); sessionStorage.removeItem("mia.arrive"); } catch (e) { /* fine */ }
    const items = env.bays.map((b) => ({ id: b.id, name: b.name, hue: h.hue, needs: b.overdue || 0,
      icon: b.category === "Vehicle" ? "garage" : "maintenance", photo: b.photo }));
    let ring = null;
    const scene = MIARoom.mount(canvas, items, {
      start: Math.min(front, items.length - 1), shape: "bay", theme: MIAShell.roomLight(), fire: 0.35, labels, needsGlow: true, arrive: !!arriveHue, arriveHue,
      art: (it) => (it.photo ? MIA.image(it.photo) : null),
      onPick: (i) => (ring && i === ring.front ? (location.href = env.bays[i].page) : ring && ring.go(i)),
      onOrb: () => MIAShell.talk(true),
      onDrop: (i) => ring && ring.go(i),
    });
    if (!scene) return false;
    document.body.classList.add("room-3d");
    const side = el("div", { class: "room-side" },
      env.needs.length ? el("section", { class: "holo env-needs", "aria-label": "Needs you" },
        el("h2", { class: "pw-label" }, "Needs You"),
        el("div", { class: "rows" }, env.needs.map((n) => el("a", { class: "env-need", href: n.page },
          el("strong", {}, n.title), el("span", {}, n.asset + " · " + n.text))))) : null,
      el("section", { class: "holo env-parts", "aria-label": "Parts running low" },
        el("h2", { class: "pw-label" }, "Parts Running Low"),
        env.parts.length ? el("div", { class: "rows" }, env.parts.map((p) => el("div", { class: "row money-row" },
          el("div", {}, el("div", { class: "row-title" }, p.name), el("div", { class: "row-sub" }, "For " + p.used_by.filter(Boolean).join(", "))),
          el("span", { class: "chip chip-soon" }, p.state === "out" ? "Out" : p.have + (p.unit ? " " + p.unit : "") + " left"))))
          : el("p", { class: "dim" }, "Nothing low.")));
    const bench = el("nav", { class: "room-bench", "aria-label": "The bench" }, env.bench.map((t) => el("a", { class: "bench-tool", href: t.page, title: t.line },
      el("span", { class: "bench-ico", "aria-hidden": "true" }, ico(t.id, t.icon)), el("strong", {}, t.name))));
    const head = el("header", { class: "room-head" },
      el("a", { class: "btn btn-ghost btn-small", href: "nexus.html" }, "‹ Nexus"),
      el("div", {}, el("h1", {}, h.name), el("p", { class: "tagline" }, env.bays.length + " bays · " + (env.needs.length ? env.needs.length + " need you" : "nothing needs you"))),
      el("a", { class: "btn btn-ghost btn-small", href: "garage.html" }, "Manage ›"));
    const ui = el("div", { class: "room-ui" }, head, el("div", { class: "room-spacer" }), card, side, bench, list);
    document.body.append(canvas, labels, ui);
    ring = MIASpatial.ring(list, links, {
      start: Math.min(front, links.length - 1),
      onTurn: (i) => { scene.focus(i); bayCard(card, env.bays[i]); },
      onEnter: (node, i) => { location.href = env.bays[i].page; },
    });
    room = { scene, ring, nodes: [canvas, labels, ui] };
    if (!keysOn) {  // the arrows turn the room from anywhere on the page (once, whatever re-renders)
      keysOn = true;
      document.addEventListener("keydown", (e) => {
        if (!room || e.defaultPrevented || e.target.closest && e.target.closest(".room-links, dialog, .talk, [role=dialog]")) return;
        if (/^(INPUT|TEXTAREA|SELECT)$/.test(e.target.tagName)) return;
        if (e.key === "ArrowRight") { e.preventDefault(); room.ring.turn(1); }
        if (e.key === "ArrowLeft") { e.preventDefault(); room.ring.turn(-1); }
      });
    }
    return true;
  }

  // ------------------------------------------------------------ any other area as a room (DEC-0130 M5, first pass)
  // Its apps and pages stand round MIA's orb as portals in the area's hue (core/web_environments.room), each glowing
  // amber when something in it needs you today; the chosen one's card opens it, and What Needs You is a panel. Only in
  // the Spatial look where the graphics card allows; otherwise (and with ?flat) the area's tiles show as before.
  function doorCard(box, d, hue) {
    box.replaceChildren(
      el("div", { class: "n3-card-head", style: "--hue:" + hue }, el("span", { class: "n3-card-ico", "aria-hidden": "true" }, ico(d.id, d.icon)),
        el("h2", {}, d.name)),
      el("p", { class: "n3-card-line" }, d.tagline || ""),
      el("p", { class: "n3-card-needs" + (d.needs ? " attn" : "") }, d.needs ? d.needs + (d.needs === 1 ? " needs you today" : " need you today") : "Nothing due today"),
      el("a", { class: "btn n3-enter", href: d.page }, "Open ", el("span", { "aria-hidden": "true" }, "›")));
  }

  function areaRoom(h, env) {
    const front = room && room.ring ? room.ring.front : 0;
    if (room) { room.scene.stop(); room.nodes.forEach((x) => x.remove()); room = null; document.body.classList.remove("room-3d"); }
    if (!(window.MIARoom && MIARoom.supported()) || /[?&]flat\b/.test(location.search) || !env.available || !env.doors.length) return false;
    if (!MIAShell.look || MIAShell.look() !== "spatial") return false;  // the cards look keeps the area's tiles (DEC-0135)
    const doors = env.doors;
    const links = doors.map((d) => el("a", { href: d.page, role: "listitem",
      "aria-label": d.name + (d.needs ? ", " + d.needs + " need you" : "") + ". " + (d.tagline || "") }, d.name));
    const list = el("div", { class: "room-links", role: "list", "aria-label": h.name + ", turn with the arrow keys" }, ...links);
    const canvas = el("canvas", { class: "n3-canvas", "aria-hidden": "true" });
    const labels = el("div", { class: "n3-labels", "aria-hidden": "true" });
    const card = el("aside", { class: "n3-card room-card", style: "--hue:" + h.hue });
    let arriveHue = null;
    try { arriveHue = sessionStorage.getItem("mia.arrive"); sessionStorage.removeItem("mia.arrive"); } catch (e) { /* fine */ }
    // the portal's icon by name (an app's own line icon, else the page's; an app's emoji isn't one)
    const iconName = (d) => (window.MIAIcons && MIAIcons.svg(d.id) ? d.id : window.MIAIcons && MIAIcons.svg(d.icon) ? d.icon : "mia");
    const items = doors.map((d) => ({ id: d.id, name: d.name, hue: h.hue, needs: d.needs || 0, icon: iconName(d) }));
    let ring = null;
    const scene = MIARoom.mount(canvas, items, {
      start: Math.min(front, items.length - 1), theme: MIAShell.roomLight(), fire: 0.55, labels, needsGlow: true, arrive: !!arriveHue, arriveHue,
      onPick: (i) => (ring && i === ring.front ? (location.href = doors[i].page) : ring && ring.go(i)),
      onOrb: () => MIAShell.talk(true),
      onDrop: (i) => ring && ring.go(i),
    });
    if (!scene) return false;
    document.body.classList.add("room-3d");
    const waiting = env.needs.length;
    const side = el("div", { class: "room-side" },
      el("section", { class: "holo env-needs", "aria-label": "Needs you" },
        el("h2", { class: "pw-label" }, waiting ? "Needs You" : "Nothing Needs You"),
        waiting ? el("div", { class: "rows" }, env.needs.map((n) => el("a", { class: "env-need", href: n.page || "#" },
          el("strong", {}, n.title), el("span", {}, n.text))))
          : el("p", { class: "dim" }, "Nothing here is due today.")));
    const head = el("header", { class: "room-head" },
      el("a", { class: "btn btn-ghost btn-small", href: "nexus.html" }, "‹ Nexus"),
      el("div", {}, el("h1", {}, h.name), el("p", { class: "tagline" }, doors.length + " apps · " + (waiting ? waiting + " need you" : "nothing needs you"))),
      el("a", { class: "btn btn-ghost btn-small", href: "hub.html?area=" + encodeURIComponent(h.id) + "&flat" }, "Tiles ›"));
    const ui = el("div", { class: "room-ui" }, head, el("div", { class: "room-spacer" }), card, side, list);
    document.body.append(canvas, labels, ui);
    ring = MIASpatial.ring(list, links, {
      start: Math.min(front, links.length - 1),
      onTurn: (i) => { scene.focus(i); doorCard(card, doors[i], h.hue); },
      onEnter: (node, i) => { location.href = doors[i].page; },
    });
    room = { scene, ring, nodes: [canvas, labels, ui] };
    if (!keysOn) {
      keysOn = true;
      document.addEventListener("keydown", (e) => {
        if (!room || e.defaultPrevented || e.target.closest && e.target.closest(".room-links, dialog, .talk, [role=dialog]")) return;
        if (/^(INPUT|TEXTAREA|SELECT)$/.test(e.target.tagName)) return;
        if (e.key === "ArrowRight") { e.preventDefault(); room.ring.turn(1); }
        if (e.key === "ArrowLeft") { e.preventDefault(); room.ring.turn(-1); }
      });
    }
    return true;
  }

  function paint(h) {
    document.title = h.name + " — MIA";
    $("hub-name").textContent = h.name;
    $("hub-sub").textContent = h.tagline;
    document.body.style.setProperty("--hue", h.hue || "");
    if (h.environment && h.environment.kind === "room") {  // every other area: a room of its apps, or its tiles
      if (areaRoom(h, h.environment)) return;
    }
    const env = h.environment && ENVIRONMENTS[h.environment.kind];
    if (env) {
      document.body.classList.add("env", "env-" + h.environment.kind);
      if (h.environment.kind === "garage" && garageRoom(h, h.environment)) return;
      const vapor = $("vapor");
      vapor.hidden = false;
      MIASpatial.vapor(vapor, [h.hue, h.hue, "#35d4ff"]);
      $("panel").replaceChildren(...env(h.environment).filter(Boolean),
        el("nav", { class: "hub-areas", "aria-label": "Other areas" },
          el("a", { class: "btn btn-ghost btn-small", href: "nexus.html" }, "‹ Nexus"),
          h.areas.filter((x) => x.id !== h.id).map((x) => el("a", { class: "btn btn-ghost btn-small", href: "hub.html?area=" + x.id }, x.name))));
      return;
    }
    $("panel").replaceChildren(
      h.apps.length ? el("div", { class: "hub-grid" }, h.apps.map(tile)) : el("p", { class: "empty" }, "Nothing here yet."),
      el("nav", { class: "hub-areas", "aria-label": "Other areas" },
        h.areas.filter((x) => x.id !== h.id).map((x) => el("a", { class: "btn btn-ghost btn-small", href: "hub.html?area=" + x.id }, x.name))));
  }

  MIAShell.start(async () => { paint(await MIA.hub(area)); });
})();
