/*
 * news.js — Good News Radio (claude, 2026-11-07, DEC-0096).
 * Renders MIA.news() (core/good_news.py): today's stories, how each is known
 * (confirmed by two outlets, from the source itself, or one outlet), its
 * caveats and its links, and each personality's script. Formatting only;
 * the look is muse's.
 */
(function () {
  "use strict";
  const { el } = MIAShell;
  const $ = (id) => document.getElementById(id);
  let showing = null;

  function story(s) {
    return el("div", { class: "sync-row council-msg" }, el("div", {},
      el("p", { class: "council-text" }, s.title),
      el("p", { class: "dim" }, s.topic + " · " + s.known + " · " + s.outlets.join(", ") + (s.caveats.length ? " · " + s.caveats.join("; ") : "")),
      el("p", {}, ...s.links.map((href, i) => el("a", { href, target: "_blank", rel: "noopener noreferrer" }, i ? " · source " + (i + 1) : "Read it")))));
  }

  function paint(data) {
    if (!data.on) {
      $("news-sub").textContent = "It's off.";
      $("panel").replaceChildren(el("section", { class: "glass money-section" },
        el("p", {}, "Say \"turn on good news radio\" to MIA and she'll read credible outlets for you once a day.")));
      return;
    }
    if (!data.day) {
      $("news-sub").textContent = "Today's episode isn't ready yet.";
      $("panel").replaceChildren();
      return;
    }
    showing = showing || data.now;
    $("news-sub").textContent = "From " + data.day + ": " + data.stories.length + " stories.";
    const tabs = el("div", { class: "row-buttons" }, data.personalities.map((p) => el("button", {
      type: "button", class: "btn btn-small " + (p.key === showing ? "btn-amber" : "btn-ghost"),
      onclick: () => { showing = p.key; paint(data); } }, p.name)));
    const track = data.tracks && data.tracks[showing];
    $("panel").replaceChildren(
      el("section", { class: "glass money-section" }, el("h2", {}, "The stories"), el("div", { class: "sync-rows" }, data.stories.map(story))),
      el("section", { class: "glass money-section" }, el("h2", {}, "On the air"), tabs,
        track ? el("p", { class: "dim" }, "In your music: \"" + track + "\".") : null,
        el("p", { class: "council-text" }, (data.scripts || {})[showing] || "")));
  }

  MIAShell.start(async () => { paint(await MIA.news()); });
})();
