/*
 * people.js — People & Pets (claude, 2026-10-17). Renders MIA.people()
 * (core/web_more.py) in tabs: Birthdays (the next 60 days, with gift
 * ideas), People (who they are, favorites, gift ideas, when you last
 * caught up) and Pets. Changes are actions: person.*, pet.*,
 * person.caught_up ("Caught Up Today"). Formatting only.
 */
(function () {
  "use strict";
  const { el, act, form } = MIAShell;
  const $ = (id) => document.getElementById(id);
  const TABS = [["people", "People"], ["birthdays", "Birthdays"], ["pets", "Pets"]];
  let page = null;
  let tab = TABS.some(([t]) => t === location.hash.slice(1)) ? location.hash.slice(1) : "people";

  const btn = (label, cls, onclick) => el("button", { type: "button", class: "btn " + cls, onclick }, label);
  const buttons = (...list) => el("div", { class: "row-buttons" }, list.filter(Boolean));
  const section = (title, actions, ...body) =>
    el("section", { class: "glass money-section" }, el("div", { class: "sect" }, el("h2", {}, title), actions), ...body);
  const day = (iso) => iso ? new Date(iso + "T00:00:00").toLocaleDateString(undefined, { month: "short", day: "numeric" }) : "";
  const when = (n) => n === 0 ? "Today!" : n === 1 ? "Tomorrow" : "In " + n + " days";
  const ago = (n) => n === 0 ? "today" : n === 1 ? "yesterday" : n < 14 ? n + " days ago" : n < 60 ? Math.round(n / 7) + " weeks ago" : Math.round(n / 30) + " months ago";

  async function add(kind) {
    const v = await form(kind === "pet" ? "Add A Pet" : "Add A Person", page.forms[kind].fields, {});
    if (v) act({ kind: kind + ".add", params: v });
  }
  async function edit(kind, x) {
    const v = await form("Edit " + x.name, page.forms[kind].fields, x.values);
    if (v) act({ kind: kind + ".edit", params: Object.assign({ [kind + "_id"]: x.id }, v) });
  }
  const del = (kind, x) => act({ kind: kind + ".delete", params: { [kind + "_id"]: x.id } });
  const field = (label, text) => text ? el("div", { class: "pp-field" }, el("span", { class: "pp-label" }, label), el("span", {}, text)) : null;

  function personCard(p) {
    return el("article", { class: "glass pp-card" },
      el("div", { class: "pp-head" },
        el("span", { class: "pp-avatar", "aria-hidden": "true" }, (p.name || "?").trim().charAt(0).toUpperCase()),
        el("div", { class: "pp-title" }, el("h3", {}, p.name), p.relationship ? el("p", { class: "dim" }, p.relationship) : null),
        p.birthday_in != null && p.birthday_in <= 30 ? el("span", { class: "chip chip-soon" }, "🎂 " + when(p.birthday_in)) : null),
      field("Birthday", p.birthday ? day(p.birthday) + (p.turning ? " · turning " + p.turning : "") : ""),
      field("Favorites", p.favorites), field("Gift ideas", p.gifts), field("Notes", p.notes), field("Email", p.email),
      el("p", { class: "dim pp-contact" }, p.days_since != null ? "Last caught up " + ago(p.days_since) : "No catch-up noted yet"),
      buttons(btn("Caught Up Today", "btn-green btn-small", () => act({ kind: "person.caught_up", params: { person_id: p.id } })),
        btn("Edit", "btn-ghost btn-small", () => edit("person", p)), btn("Delete", "btn-ghost btn-small", () => del("person", p))));
  }

  function petCard(a) {
    return el("article", { class: "glass pp-card" },
      el("div", { class: "pp-head" },
        el("span", { class: "pp-avatar", "aria-hidden": "true" }, "🐾"),
        el("div", { class: "pp-title" }, el("h3", {}, a.name), a.species ? el("p", { class: "dim" }, a.species) : null),
        a.birthday_in != null && a.birthday_in <= 30 ? el("span", { class: "chip chip-soon" }, "🎂 " + when(a.birthday_in)) : null),
      field("Birthday", a.birthday ? day(a.birthday) + (a.turning ? " · turning " + a.turning : "") : ""),
      field("Vet & medical", a.medical), field("Notes", a.notes),
      buttons(btn("Edit", "btn-ghost btn-small", () => edit("pet", a)), btn("Delete", "btn-ghost btn-small", () => del("pet", a))));
  }

  const VIEWS = {
    people: () => section("People", btn("Add Person", "btn-amber", () => add("person")),
      page.people.length ? el("div", { class: "pp-grid" }, page.people.map(personCard))
        : el("p", { class: "empty" }, "Add the people who matter: family, friends, the ones you want to remember things about.")),
    birthdays: () => section("Coming Up", null, page.upcoming.length ? el("div", { class: "rows" }, page.upcoming.map((u) =>
      el("div", { class: "row money-row" },
        el("div", {}, el("div", { class: "row-title" }, (u.kind === "pet" ? "🐾 " : "🎂 ") + u.name + (u.turning ? " · turning " + u.turning : "")),
          el("div", { class: "row-sub" }, day(u.date) + (u.gifts ? " · gift ideas: " + u.gifts : ""))),
        el("span", { class: "chip " + (u.in <= 7 ? "chip-soon" : "") }, when(u.in)))))
      : el("p", { class: "empty" }, "No birthdays in the next 60 days. Add birthdays to people and pets and MIA will remember them.")),
    pets: () => section("Pets", btn("Add Pet", "btn-amber", () => add("pet")),
      page.pets.length ? el("div", { class: "pp-grid" }, page.pets.map(petCard)) : el("p", { class: "empty" }, "No pets yet.")),
  };

  function draw() {
    const c = page.counts;
    $("strip").replaceChildren(
      el("div", { class: "cell ok" }, el("span", { class: "n" }, c.people), el("span", { class: "t" }, "People")),
      el("div", { class: "cell soon" }, el("span", { class: "n" }, c.birthdays), el("span", { class: "t" }, "Birthdays Soon")),
      el("div", { class: "cell ok" }, el("span", { class: "n" }, c.pets), el("span", { class: "t" }, "Pets")));
    $("tabs").hidden = false;
    $("tabs").replaceChildren(...TABS.map(([id, l]) => el("button", { type: "button", role: "tab", "aria-selected": String(id === tab),
      onclick: () => { tab = id; history.replaceState(null, "", "#" + id); draw(); } }, l)));
    $("panel").replaceChildren(VIEWS[tab]());
  }

  MIAShell.start(async () => {
    page = await MIA.people();
    if (!page.available) {
      $("panel").replaceChildren(el("p", { class: "empty" }, "People & Pets isn't set up on this MIA."));
      return;
    }
    draw();
  });
})();
