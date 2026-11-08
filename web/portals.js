/*
 * portals.js — Portal Pictures (claude, 2026-11-08, DEC-0140 / DEC-0130).
 * Renders MIA.portals() (core/portal_pictures.py): each area's portal in the Nexus with the picture it shows (your
 * painting, the original, or none yet), and three ways to change it: Paint One (MIA paints it on the PC's graphics
 * card and it goes in that portal when it's done), Choose (one of your paintings) and Original. Choosing is the
 * portal.picture action, undoable; painting is MIA.paint(..., "portal", true, area).
 */
(function () {
  "use strict";
  const { el } = MIAShell;
  const $ = (id) => document.getElementById(id);
  const button = (label, onclick, cls) => el("button", { type: "button", class: "btn " + (cls || "btn-ghost") + " btn-small", onclick }, label);
  const SOURCE = { yours: "Your painting", original: "The original", none: "No picture yet" };
  let data = null, open = "", mode = "", timer = 0, note = "";

  // A picture into an element's background: a page path at once, one of yours through your sign-in (MIA.image).
  function show(node, path) {
    if (!path) return node;
    if (path.startsWith("/api/")) {
      Promise.resolve(MIA.image(path)).then((url) => { if (url) node.style.backgroundImage = "url(\"" + url + "\")"; });
    } else node.style.backgroundImage = "url(\"" + path + "\")";
    return node;
  }

  const choose = (area, art) => MIAShell.act({ kind: "portal.picture", params: { area: area.id, art } }, { quick: true });

  async function paintFor(area) {
    const box = $("pp-words");
    const words = box ? box.value.trim() : "";
    if (!words) return;
    note = "";
    try { await MIA.paint(words, "portal", true, area.id); mode = ""; }
    catch (e) { note = (e && e.message) || "She couldn't start that painting."; }
    refresh();
  }

  function tools(area) {
    if (open !== area.id) return null;
    if (mode === "paint") {
      const engine = data.engine || {};
      return el("div", { class: "pp-tools" },
        engine.available ? null : el("p", { class: "dim" }, engine.line || "The image engine isn't running on the PC."),
        el("input", { id: "pp-words", type: "text", maxlength: "400", placeholder: "A misty glasshouse at dawn",
          "aria-label": "What should MIA paint for the " + area.name + " portal?", disabled: engine.available ? null : "",
          onkeydown: (e) => { if (e.key === "Enter") paintFor(area); } }),
        el("div", { class: "pp-row" }, button("Paint It", () => paintFor(area), "btn-primary"), button("Cancel", () => { mode = ""; paint(); })),
        note ? el("p", { class: "pp-note", role: "status" }, note) : null);
    }
    if (mode === "choose") {
      const mine = data.paintings;
      return el("div", { class: "pp-tools" },
        mine.length ? el("div", { class: "pp-strip", role: "list", "aria-label": "Your paintings" }, ...mine.map((p) =>
          el("button", { type: "button", role: "listitem", class: "pp-thumb" + (p.id === area.art_id ? " on" : ""),
            "aria-label": p.description + (p.id === area.art_id ? " (in this portal now)" : ""),
            onclick: () => { mode = ""; open = ""; choose(area, p.id); } }, show(el("span", { class: "pp-thumb-img", "aria-hidden": "true" }), p.image))))
          : el("p", { class: "dim" }, "You haven't any paintings yet. Paint One makes the first."),
        el("div", { class: "pp-row" }, button("Cancel", () => { mode = ""; paint(); })));
    }
    return null;
  }

  function card(area) {
    const going = data.jobs.find((j) => j.area === area.id && j.status === "painting");
    const failed = data.jobs.find((j) => j.area === area.id && j.status === "failed");
    const frame = el("span", { class: "pp-frame" + (area.picture ? " has-art" : ""), style: "--hue:" + area.hue, "aria-hidden": "true" },
      area.picture ? show(el("span", { class: "pp-art" }), area.picture)
        : el("span", { class: "pp-ico" }, window.MIAIcons ? MIAIcons.svg(area.icon) || MIAIcons.svg("mia") : null));
    const set = (m) => () => { open = area.id; mode = m; note = ""; paint(); if (m === "paint") setTimeout(() => $("pp-words") && $("pp-words").focus(), 0); };
    return el("article", { class: "glass pp-card" + (open === area.id ? " open" : ""), style: "--hue:" + area.hue },
      frame,
      el("div", { class: "pp-body" },
        el("h2", {}, area.name),
        el("p", { class: "pp-source " + area.source }, going ? "Painting… (" + going.seconds + " s)" : SOURCE[area.source]),
        failed ? el("p", { class: "pp-note" }, failed.error || "The last painting didn't finish.") : null,
        el("div", { class: "pp-row" },
          button("Paint One", set("paint")),
          button("Choose", set("choose")),
          area.source === "yours" ? button("Original", () => choose(area, ""), "btn-quiet") : null),
        tools(area)));
  }

  function paint() {
    if (!data) return;
    const yours = data.areas.filter((a) => a.source === "yours").length;
    $("pp-sub").textContent = "The picture inside each area's portal in the Nexus. " + (yours
      ? yours + " of " + data.areas.length + " show your own paintings."
      : "Put one of your paintings in any of them, or have MIA paint one for it.");
    $("panel").replaceChildren(
      el("section", { class: "pp-grid" }, ...data.areas.map(card)),
      el("div", { class: "pp-say" }, el("p", { class: "dim" }, "Or say \"paint me a misty forest for the Plants portal\"."),
        el("a", { class: "btn btn-ghost btn-small", href: "nexus.html" }, "‹ Nexus")));
    clearTimeout(timer);
    if (data.jobs.some((j) => j.status === "painting")) timer = setTimeout(refresh, 5000);  // a painting takes a minute or so
  }

  async function refresh() { data = await MIA.portals(); paint(); }

  MIAShell.start(refresh, { refreshOnChange: true });
})();
