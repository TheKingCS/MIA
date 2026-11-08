/*
 * chronicle.js — The Chronicle (claude, 2026-10-17, DEC-0028). Renders
 * MIA.chronicle() (core/chronicle.py): this week's chapter, the weeks
 * before it, and the yearly editions. Laid out as the design canvas's
 * Chronicle (DEC-0113): the newest chapter as prose, earlier ones to open.
 * Read only; formatting only.
 */
(function () {
  "use strict";
  const { el } = MIAShell;
  const $ = (id) => document.getElementById(id);
  const TABS = [["weeks", "Weekly"], ["years", "Yearly"]];
  let page = null;
  let tab = TABS.some(([t]) => t === location.hash.slice(1)) ? location.hash.slice(1) : "weeks";

  function chapter(c, open) {
    return el("article", { class: "glass chron" + (open ? " open" : "") },
      el("header", { class: "chron-head" },
        el("span", { class: "chron-title" }, c.title + " · " + c.dates + (c.so_far && c.kind === "week" ? " · so far" : "")),
        el("h2", {}, c.name)),
      el("div", { class: "chron-story" }, c.story.map((line) => el("p", {}, line))),
      c.highlights.length ? el("div", { class: "chron-high" }, el("span", { class: "chron-label" }, "Highlights"),
        el("ul", {}, c.highlights.map((h) => el("li", {}, h)))) : null,
      // The yearly edition, month by month (core/seasons.py keeps each month as it closes).
      c.months && c.months.length ? el("div", { class: "chron-high" }, el("span", { class: "chron-label" }, "Month by month"),
        ...c.months.map((m) => el("div", {}, el("h3", {}, m.month), el("ul", {}, m.lines.map((l) => el("li", {}, l)))))) : null,
      // The memory vault's photos from these days (core/memory_vault.photos_between).
      c.photos && c.photos.count ? el("a", { class: "chron-photos", href: "vault.html#photos" },
        (() => {
          const img = el("img", { alt: "", class: "vault-best" });
          if (c.photos.cover) MIA.image("/api/vault/photo/" + c.photos.cover).then((src) => { if (src) img.src = src; });
          return img;
        })(), "📷 " + c.photos.count + (c.photos.count === 1 ? " photo" : " photos")) : null);
  }

  // The design canvas (DEC-0113): the newest chapter told as prose (its label, its name, the story in two
  // paragraphs, its highlights as tags), then Earlier Chapters, each opening to its full story.
  function lead(c) {
    const half = Math.ceil(c.story.length / 2);
    return el("article", { class: "chron-lead" },
      el("span", { class: "pw-label" }, "The Chronicle · " + c.title + " · " + c.dates + (c.so_far && c.kind === "week" ? " · so far" : "")),
      el("h2", {}, c.name),
      el("p", {}, c.story.slice(0, half).join(" ")), c.story.length > 1 ? el("p", {}, c.story.slice(half).join(" ")) : null,
      c.highlights.length ? el("div", { class: "chron-tags" }, ...c.highlights.slice(0, 6).map((h) => el("span", { class: "chron-tag" }, h))) : null,
      c.months && c.months.length ? chapter(Object.assign({}, c, { story: [], highlights: [], photos: null, name: "Month by month" }), false) : null,
      c.photos && c.photos.count ? chapter(Object.assign({}, c, { story: [], highlights: [], months: [], name: "Photos" }), false) : null);
  }

  function draw() {
    $("tabs").hidden = false;
    $("tabs").replaceChildren(...TABS.map(([id, l]) => el("button", { type: "button", role: "tab", "aria-selected": String(id === tab),
      onclick: () => { tab = id; history.replaceState(null, "", "#" + id); draw(); } }, l)));
    const list = tab === "years" ? page.years : [page.this_week, ...page.weeks];
    const [first, ...rest] = list;
    $("panel").replaceChildren(...[first ? lead(first) : null,
      rest.length ? el("p", { class: "pw-label chron-earlier" }, "Earlier Chapters") : null,
      ...rest.map((c) => el("details", { class: "glass chron-row" },
        el("summary", {}, el("span", {}, c.name), el("span", { class: "dim" }, c.title)), chapter(c, false))),
      el("p", { class: "dim" }, tab === "years" ? "The yearly edition grows all year and is finished on Dec 31."
        : "A new chapter is ready every Sunday. A quiet week is a quiet week, never a failure.")].filter(Boolean));
  }

  MIAShell.start(async () => {
    page = await MIA.chronicle();
    draw();
  });
})();
