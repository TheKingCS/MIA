/*
 * closet.js — Smart Closet (claude, 2026-11-15, DEC-0162).
 *
 * Renders MIA.closet() (core/web_closet.py) in four tabs:
 * - Today: the day (weather, plans, occasion) and up to three picks, each
 *   shown as its pieces side by side, so you see them together, with why.
 * - Closet: the pieces by kind. Tap pieces to choose them, then save them
 *   as an outfit or mark them worn. Each piece has edit, photo, wash and
 *   remove.
 * - Outfits: the saved outfits with their stars, to wear or rate.
 * - Insights: what's gone unworn (let it go?), the most worn, the best
 *   rated, what's in the wash, and what's missing.
 *
 * Every change is an action (core/closet_actions.py). This file only
 * formats.
 */
(function () {
  "use strict";
  const { el, act, form, say } = MIAShell;
  const $ = (id) => document.getElementById(id);
  const TABS = [["today", "Today"], ["closet", "Closet"], ["outfits", "Outfits"], ["insights", "Insights"]];
  let page = null;
  let tab = TABS.some(([t]) => t === location.hash.slice(1)) ? location.hash.slice(1) : "today";
  const chosen = new Set();  // pieces tapped in the Closet tab, for an outfit or "wore these"

  const btn = (label, cls, onclick) => el("button", { type: "button", class: "btn " + cls, onclick }, label);
  const buttons = (...list) => el("div", { class: "row-buttons" }, list.filter(Boolean));
  const section = (title, actions, ...body) =>
    el("section", { class: "glass money-section" }, el("div", { class: "sect" }, el("h2", {}, title), actions), ...body);
  const chip = (text, cls) => el("span", { class: "chip " + (cls || "") }, text);
  const stars = (n) => n == null ? "not rated" : "★".repeat(Math.round(n)) + "☆".repeat(5 - Math.round(n)) + " " + n;
  const go = (id) => { tab = id; history.replaceState(null, "", "#" + id); draw(); };
  const field = (name, label, type, def, required, options) => ({ name, label, type, required: !!required, options: options || [], default: def ?? null });

  // A piece's picture (or its colour swatch and name when it has none), so an outfit can be seen together.
  function thumb(p) {
    const box = el("figure", { class: "closet-thumb", title: p.name },
      el("div", { class: "closet-swatch", "aria-hidden": "true" }, p.color ? p.color.slice(0, 1).toUpperCase() : "·"),
      el("figcaption", {}, p.name));
    if (p.photo_url) MIA.image(p.photo_url).then((src) => {
      if (src) box.replaceChild(el("img", { src, alt: p.name, loading: "lazy" }), box.firstChild);
    });
    return box;
  }
  const together = (pieces) => el("div", { class: "closet-together" }, pieces.map(thumb));

  // ------------------------------------------------------------ changes
  async function editPiece(p) {
    const values = p ? Object.assign({}, p, { occasions: (p.occasions || []).join(", "), waterproof: p.waterproof ? "yes" : "no" }) : {};
    const v = await form(p ? "Change " + p.name : "Add A Piece", page.form.fields, values);
    if (v) act({ kind: p ? "closet_piece.edit" : "closet_piece.add", params: p ? Object.assign({ piece_id: p.piece_id }, v) : v });
  }
  function photo(p) {
    const input = el("input", { type: "file", accept: "image/*", capture: "environment", hidden: true });
    input.addEventListener("change", async () => {
      const file = input.files && input.files[0];
      if (!file) return;
      try { say("Saving the photo…"); say((await MIA.upload("/api/closet/piece/" + encodeURIComponent(p.piece_id) + "/photo", file)).message); MIAShell.refresh(); }
      catch (e) { say(e.message); }
    });
    document.body.appendChild(input);
    input.click();
  }
  async function saveOutfit(ids) {
    const v = await form("Save As An Outfit", [field("name", "A name (optional)", "text")], {});
    if (v) { await act({ kind: "closet.outfit", params: { piece_ids: ids.join(","), name: v.name || "" } }); chosen.clear(); }
  }
  async function rate(o) {
    const v = await form("Rate " + o.name, [field("stars", "Stars", "choice", "4", true, ["5", "4", "3", "2", "1"]),
      field("note", "What worked, or didn't (optional)", "text")], {});
    if (v) act({ kind: "closet.rate", params: { outfit_id: o.outfit_id, stars: v.stars, note: v.note || "" } });
  }
  const wore = (params) => act({ kind: "closet.wore", params });

  // ------------------------------------------------------------ tabs
  function today() {
    const d = page.day, plan = page.suggestion;
    const lead = el("p", { class: "progress-sentence" },
      (d.weather_text ? d.weather_text + (d.place ? " in " + d.place : "") : "No weather yet (name your town on the Dashboard)") +
      " · " + plan.occasion + (d.events.length ? " · " + d.events.join(", ") : ""));
    if (!page.count) return section("Today", null, lead, el("p", { class: "empty" }, "Your closet is empty: add a few pieces and MIA will start picking."),
      buttons(btn("Add A Piece", "btn-green", () => editPiece(null))));
    const picks = plan.picks.map((pk, i) => el("article", { class: "glass closet-pick" + (i === 0 ? " best" : "") },
      el("div", { class: "row-title" }, (i === 0 ? "Best pick: " : "Or: ") + pk.name, pk.saved ? chip("saved", "ok") : chip("new combo")),
      together(pk.pieces),
      pk.why.length ? el("p", { class: "dim" }, pk.why.join(" · ")) : null,
      buttons(btn("Wearing This", "btn-green", () => wore(pk.outfit_id ? { outfit_id: pk.outfit_id } : { piece_ids: pk.piece_ids.join(",") })),
        pk.saved ? null : btn("Save As Outfit", "btn-ghost", () => saveOutfit(pk.piece_ids)))));
    return [section("Today", null, lead,
      plan.outerwear ? el("p", {}, plan.wet ? "Rain on the way: a waterproof layer." : "Cool today: bring a jacket.") : null,
      plan.missing.length ? el("p", { class: "dim" }, "The closet needs " + plan.missing.join(", ") + " to dress today fully.") : null),
      ...picks];
  }

  function closet() {
    const pick = (p) => { chosen.has(p.piece_id) ? chosen.delete(p.piece_id) : chosen.add(p.piece_id); draw(); };
    const ids = [...chosen];
    const bar = ids.length ? el("div", { class: "glass closet-chosen" }, el("span", {}, ids.length + " chosen"),
      buttons(ids.length > 1 ? btn("Save As Outfit", "btn-green", () => saveOutfit(ids)) : null,
        btn("Wore These", "btn-ghost", async () => { await wore({ piece_ids: ids.join(",") }); chosen.clear(); }),
        btn("Into The Wash", "btn-ghost", async () => { await act({ kind: "closet.laundry", params: { piece_ids: ids.join(","), into_wash: "yes" } }); chosen.clear(); }),
        btn("Clear", "btn-ghost", () => { chosen.clear(); draw(); }))) : null;
    return [section("Your Closet", buttons(btn("Add A Piece", "btn-green", () => editPiece(null)),
      btn("Laundry's Done", "btn-ghost", () => act({ kind: "closet.laundry", params: {} }))),
      el("p", { class: "dim" }, page.count + " pieces. Tap pieces to choose them for an outfit.")), bar,
      ...page.groups.map((g) => section(g.label, null, el("div", { class: "closet-grid" }, g.pieces.map((p) =>
        el("div", { class: "closet-piece" + (chosen.has(p.piece_id) ? " chosen" : "") + (p.in_wash ? " washing" : "") },
          el("button", { type: "button", class: "closet-pick-btn", "aria-pressed": String(chosen.has(p.piece_id)), onclick: () => pick(p) }, thumb(p)),
          el("div", { class: "dim" }, [p.color, p.warmth, (p.occasions || []).join("/"), p.in_wash ? "in the wash" : "",
            p.condition !== "good" ? p.condition : "", p.last_worn ? "worn " + p.last_worn : "not worn yet"].filter(Boolean).join(" · ")),
          buttons(btn("Edit", "btn-ghost btn-small", () => editPiece(p)), btn("Photo", "btn-ghost btn-small", () => photo(p)),
            btn("Remove", "btn-ghost btn-small", () => act({ kind: "closet_piece.delete", params: { piece_id: p.piece_id } }))))))))];
  }

  function outfits() {
    if (!page.outfits.length) return section("Outfits", null, el("p", { class: "empty" }, "No saved outfits yet: choose pieces in the Closet tab and save them."));
    return page.outfits.map((o) => el("article", { class: "glass closet-pick" },
      el("div", { class: "row-title" }, o.name, chip(stars(o.stars), o.stars >= 4 ? "ok" : "")),
      together(o.pieces),
      el("p", { class: "dim" }, (o.times_worn ? "Worn " + o.times_worn + "×, last " + o.last_worn : "Not worn yet") + (o.ratings ? " · " + o.ratings + " ratings" : "")),
      buttons(btn("Wearing This", "btn-green", () => wore({ outfit_id: o.outfit_id })), btn("Rate", "btn-ghost", () => rate(o)),
        btn("Forget", "btn-ghost", () => act({ kind: "closet.outfit_delete", params: { outfit_id: o.outfit_id } })))));
  }

  function insights() {
    const i = page.insights;
    const list = (items) => el("ul", {}, items.map((x) => el("li", {}, x)));
    return [
      i.unworn.length ? section("Let It Go?", null, el("p", { class: "dim" }, "Not worn in six months or more."),
        list(i.unworn.map((x) => x.name + (x.never ? " (never worn)" : " · " + x.days + " days")))) : null,
      i.most_worn.length ? section("Most Worn", null, list(i.most_worn.map((x) => x.name + " · " + x.times + "×"))) : null,
      i.top_rated.length ? section("Best Rated", null, list(i.top_rated.map((x) => x.name + " · " + x.stars + "★"))) : null,
      i.in_wash.length || i.needs_repair.length ? section("Not Ready", null, list([...i.in_wash.map((n) => n + ": in the wash"), ...i.needs_repair.map((n) => n + ": needs a repair")])) : null,
      i.gaps.length ? section("Missing", null, el("p", {}, "No " + i.gaps.join(", ") + " yet.")) : null,
    ].filter(Boolean).concat(page.count ? [] : [section("Insights", null, el("p", { class: "empty" }, "Add pieces and wear them; this fills in."))]);
  }

  const VIEWS = { today, closet, outfits, insights };

  function draw() {
    const plan = page.suggestion;
    $("strip").replaceChildren(
      el("div", { class: "cell ok" }, el("span", { class: "n" }, String(page.count)), el("span", { class: "t" }, "Pieces")),
      el("div", { class: "cell ok" }, el("span", { class: "n" }, String(page.outfits.length)), el("span", { class: "t" }, "Outfits")),
      el("div", { class: "cell ok" }, el("span", { class: "n" }, plan.occasion), el("span", { class: "t" }, "Today")),
      el("div", { class: "cell " + (page.insights.in_wash.length ? "soon" : "ok") }, el("span", { class: "n" }, String(page.insights.in_wash.length)), el("span", { class: "t" }, "In The Wash")));
    $("tabs").hidden = false;
    $("tabs").replaceChildren(...TABS.map(([id, l]) => el("button", { type: "button", role: "tab", "aria-selected": String(id === tab),
      onclick: () => go(id) }, l)));
    $("panel").replaceChildren(...[].concat(VIEWS[tab]()).filter(Boolean));
  }

  MIAShell.start(async () => {
    page = await MIA.closet();
    if (!page.available) { $("panel").replaceChildren(el("p", { class: "empty" }, "There's no closet on this MIA.")); return; }
    draw();
  });
})();
