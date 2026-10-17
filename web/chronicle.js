/*
 * chronicle.js — The Chronicle (claude, 2026-10-17, DEC-0028). Renders
 * MIA.chronicle() (core/chronicle.py): this week's chapter, the weeks
 * before it, and the yearly editions. Read only; formatting only.
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
        el("ul", {}, c.highlights.map((h) => el("li", {}, h)))) : null);
  }

  function draw() {
    $("tabs").hidden = false;
    $("tabs").replaceChildren(...TABS.map(([id, l]) => el("button", { type: "button", role: "tab", "aria-selected": String(id === tab),
      onclick: () => { tab = id; history.replaceState(null, "", "#" + id); draw(); } }, l)));
    const list = tab === "years" ? page.years : [page.this_week, ...page.weeks];
    $("panel").replaceChildren(...list.map((c, i) => chapter(c, i === 0)),
      el("p", { class: "dim" }, tab === "years" ? "The yearly edition grows all year and is finished on Dec 31."
        : "A new chapter is ready every Sunday. A quiet week is a quiet week, never a failure."));
  }

  MIAShell.start(async () => {
    page = await MIA.chronicle();
    draw();
  });
})();
