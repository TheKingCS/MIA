/*
 * expeditions.js — the Expeditions screen (claude, 2026-10-16; Zac: the app
 * only opened a chat). Renders MIA.expeditions() (core/web_more.py):
 * expeditions happening now, coming up and past; one opens to its trips,
 * each with Start / Finish, its packing list (tap to pack) and its notes.
 * Every change is an action (expedition.*, trip.*, gear.*). Formatting only.
 */
(function () {
  "use strict";
  const { el, act, form } = MIAShell;
  const $ = (id) => document.getElementById(id);
  let page = null;
  let open = decodeURIComponent(location.hash.slice(1)) || null;

  const btn = (label, cls, onclick) => el("button", { type: "button", class: "btn " + cls, onclick }, label);
  const buttons = (...list) => el("div", { class: "row-buttons" }, list.filter(Boolean));
  const section = (title, actions, ...body) =>
    el("section", { class: "glass money-section" }, el("div", { class: "sect" }, el("h2", {}, title), actions), ...body);
  const day = (iso) => iso ? new Date(iso + "T00:00:00").toLocaleDateString(undefined, { month: "short", day: "numeric" }) : "";
  const span = (a, b) => a ? day(a) + (b && b !== a ? " – " + day(b) : "") : "No date yet";
  const STATUS = { planned: ["Planned", ""], active: ["Underway", "chip-soon"], completed: ["Done", "chip-ok"] };

  async function addExpedition() {
    const v = await form("Plan An Expedition", page.forms.expedition.fields, {});
    if (v) act({ kind: "expedition.add", params: v });
  }
  async function editExpedition(x) {
    const v = await form("Edit " + x.name, page.forms.expedition.fields, x.values);
    if (v) act({ kind: "expedition.edit", params: Object.assign({ expedition_id: x.id }, v) });
  }
  async function addTrip(x) {
    const v = await form("Add A Trip To " + x.name, page.forms.trip.fields, { start_date: x.start || "" });
    if (v) act({ kind: "trip.add", params: Object.assign({ expedition_id: x.id }, v) });
  }
  async function editTrip(t) {
    const v = await form("Edit " + t.name, page.forms.trip.fields, t.values);
    if (v) act({ kind: "trip.edit", params: Object.assign({ trip_id: t.id }, v) });
  }

  function trip(t) {
    const [label, cls] = STATUS[t.status] || [t.status, ""];
    const input = el("input", { type: "text", placeholder: "Add to the packing list…", "aria-label": "Add to the packing list for " + t.name });
    const addGear = (ev) => {
      ev.preventDefault();
      const label = input.value.trim();
      if (label) act({ kind: "gear.add", params: { trip_id: t.id, label } });
    };
    return el("article", { class: "glass trip-card" },
      el("div", { class: "trip-head" },
        el("div", {}, el("h3", {}, t.name),
          el("p", { class: "dim" }, [t.activity, span(t.start, t.end), t.distance_km ? t.distance_km + " km" : null].filter(Boolean).join(" · "))),
        el("span", { class: "chip " + cls }, label)),
      t.notes ? el("p", { class: "trip-notes" }, t.notes) : null,
      el("h4", {}, "Packing List" + (t.gear.length ? " " + t.packed + "/" + t.gear.length : "")),
      t.gear.length ? el("ul", { class: "gear-list" }, t.gear.map((g) => el("li", { class: g.packed ? "done" : "" },
        el("button", { type: "button", class: "tick" + (g.packed ? " on" : ""), "aria-pressed": String(g.packed),
          "aria-label": (g.packed ? "Unpack " : "Pack ") + g.label, onclick: () => act({ kind: "gear.toggle", params: { trip_id: t.id, index: g.index } }) },
          g.packed ? "✓" : ""),
        el("span", {}, g.label),
        el("button", { type: "button", class: "btn btn-ghost btn-small", "aria-label": "Remove " + g.label,
          onclick: () => act({ kind: "gear.remove", params: { trip_id: t.id, index: g.index } }) }, "✕"))))
        : el("p", { class: "dim" }, "Nothing on the list yet."),
      el("form", { class: "gear-add", onsubmit: addGear }, input, el("button", { type: "submit", class: "btn btn-ghost btn-small" }, "Add")),
      t.journal.length ? el("p", { class: "dim" }, "Journal: ", ...t.journal.map((j, i) => [i ? ", " : "", el("a", { href: "journal.html" }, j.title)]).flat()) : null,
      buttons(
        t.status === "planned" ? btn("Start Trip", "btn-green", () => act({ kind: "trip.status", params: { trip_id: t.id, status: "active" } })) : null,
        t.status === "active" ? btn("Finish Trip", "btn-green", () => act({ kind: "trip.status", params: { trip_id: t.id, status: "completed" } })) : null,
        btn("Edit", "btn-ghost", () => editTrip(t)),
        btn("Delete", "btn-ghost", () => act({ kind: "trip.delete", params: { trip_id: t.id } }))));
  }

  function card(x) {
    const go = () => { open = x.id; history.replaceState(null, "", "#" + encodeURIComponent(x.id)); draw(); window.scrollTo(0, 0); };
    const when = x.when === "now" ? "Happening Now" : x.days_away != null ? (x.days_away === 0 ? "Today" : x.days_away === 1 ? "Tomorrow" : "In " + x.days_away + " days") : x.when === "past" ? "Done" : "";
    return el("article", { class: "glass mission-card" + (x.when === "now" ? " ready" : "") + (x.when === "past" ? " finished" : ""),
      tabindex: "0", role: "button", "aria-label": "Open " + x.name, onclick: go,
      onkeydown: (ev) => { if (ev.key === "Enter" || ev.key === " ") { ev.preventDefault(); go(); } } },
    el("div", { class: "mission-top" },
      el("span", { class: "mission-icon", "aria-hidden": "true" }, "🏕"),
      el("div", { class: "mission-title" }, el("h3", {}, x.name),
        el("p", { class: "dim" }, [x.location, span(x.start, x.end), x.trips.length + (x.trips.length === 1 ? " trip" : " trips")].filter(Boolean).join(" · "))),
      when ? el("div", { class: "mission-chips" }, el("span", { class: "chip " + (x.when === "now" ? "chip-soon" : "") }, when)) : null));
  }

  function detail(x) {
    return [
      el("p", {}, el("a", { href: "#", onclick: (ev) => { ev.preventDefault(); open = null; history.replaceState(null, "", location.pathname); draw(); } }, "‹ All Expeditions")),
      section(x.name, buttons(btn("Add Trip", "btn-amber", () => addTrip(x)), btn("Edit", "btn-ghost", () => editExpedition(x)),
          btn("Delete", "btn-ghost", () => act({ kind: "expedition.delete", params: { expedition_id: x.id } }))),
        el("p", { class: "dim" }, [x.location, span(x.start, x.end)].filter(Boolean).join(" · ")),
        x.notes ? el("p", {}, x.notes) : null),
      x.trips.length ? el("div", { class: "trip-grid" }, x.trips.map(trip))
        : el("p", { class: "empty" }, "No trips yet. Add one: a hike, a paddle, a night of camping."),
    ];
  }

  function draw() {
    const c = page.counts;
    $("strip").replaceChildren(
      el("div", { class: "cell soon" }, el("span", { class: "n" }, c.now), el("span", { class: "t" }, "Happening Now")),
      el("div", { class: "cell ok" }, el("span", { class: "n" }, c.upcoming), el("span", { class: "t" }, "Coming Up")),
      el("div", { class: "cell ok" }, el("span", { class: "n" }, c.trips), el("span", { class: "t" }, "Trips")));
    const x = open && page.expeditions.find((e) => e.id === open);
    if (x) { $("panel").replaceChildren(...detail(x)); return; }
    const group = (title, list) => list.length ? section(title, null, el("div", { class: "mission-grid" }, list.map(card))) : null;
    const by = (w) => page.expeditions.filter((e) => e.when === w);
    $("panel").replaceChildren(...[
      el("div", { class: "journal-actions" }, btn("Plan An Expedition", "btn-amber", addExpedition)),
      group("Happening Now", by("now")), group("Coming Up", by("upcoming")), group("Past", by("past")),
      page.expeditions.length ? null : el("p", { class: "empty" }, "No expeditions yet. Plan one: a weekend at the lake, a long hike."),
    ].filter(Boolean));
  }

  MIAShell.start(async () => {
    page = await MIA.expeditions();
    if (!page.available) {
      $("panel").replaceChildren(el("p", { class: "empty" }, "Expeditions aren't set up on this MIA."));
      return;
    }
    draw();
  });
})();
