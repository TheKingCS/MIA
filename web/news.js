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

  // The design canvas (DEC-0113): a card per story: how it's known as a tag (green confirmed, plain from the source,
  // amber one outlet: core/good_news.KNOWN_TAGS), the story, its caveats, and its sources.
  function story(s) {
    return el("article", { class: "glass nw-story" },
      el("span", { class: "kind " + (s.tone || "") }, s.tag || s.known),
      el("p", { class: "nw-title" }, s.title),
      el("p", { class: "nw-caveat" }, [s.outlets.join(", "), ...s.caveats].filter(Boolean).join(" · ")),
      el("details", { class: "nw-sources" }, el("summary", {}, "Sources (" + s.links.length + ")"),
        el("ul", {}, s.links.map((href, i) => el("li", {}, el("a", { href, target: "_blank", rel: "noopener noreferrer" }, s.outlets[i] || href))))));
  }
  const WORDS = ["No", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten"];

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
    const n = data.stories.length;
    $("panel").replaceChildren(
      el("section", { class: "nw-head" }, el("span", { class: "nw-label" }, new Date(data.day + "T00:00:00")
        .toLocaleDateString(undefined, { weekday: "short", day: "2-digit", month: "short" })),
        el("h2", {}, (WORDS[n] || String(n)) + (n === 1 ? " story today" : " stories today"))),
      el("div", { class: "nw-stories" }, data.stories.map(story)),
      el("section", { class: "glass money-section" }, el("h2", {}, "On the air"), tabs,
        track ? el("p", { class: "dim" }, "In your music: \"" + track + "\".") : null,
        el("p", { class: "council-text" }, (data.scripts || {})[showing] || "")));
  }

  MIAShell.start(async () => { paint(await MIA.news()); });
})();
