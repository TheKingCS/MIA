/*
 * checkin.js — the Sunday check-in (claude, 2026-10-27, DEC-0047 rule 5).
 * Renders MIA.checkin() (core/weekly_checkin.py): last week (the story, the
 * loop's honest score, loot, what MIA noticed, quests finished) and the
 * week ahead, day by day (runs with projected loot, rhythms, calendar
 * events), quests in progress and the next dungeon. "Debrief Done" is the
 * one action (loop.checkin_done). Laid out as the design canvas's Check-in
 * (DEC-0113): the summary first, the full week folded below. Formatting only.
 */
(function () {
  "use strict";
  const { el, act } = MIAShell;
  const $ = (id) => document.getElementById(id);

  const section = (title, aside, ...body) =>
    el("section", { class: "glass money-section" }, el("div", { class: "sect" }, el("h2", {}, title), aside), ...body);
  const tiles = (...list) => el("div", { class: "craft-tiles" }, list.filter(Boolean).map(([label, value, cls]) =>
    el("div", { class: "craft-tile " + (cls || "") }, el("span", { class: "dim" }, label), el("strong", {}, value))));
  const bar = (pct) => el("div", { class: "bar", role: "progressbar", "aria-valuenow": String(pct), "aria-valuemin": "0", "aria-valuemax": "100" },
    el("div", { class: "bar-fill", style: "width:" + Math.max(0, Math.min(100, pct || 0)) + "%" }));

  function last(c) {
    const L = c.last;
    const loop = L.loop.filter((r) => r.scheduled);
    return section("Last Week", el("span", { class: "dim" }, L.span),
      el("p", { class: "progress-sentence" }, L.chapter),
      ...L.story.map((line) => el("p", {}, line)),
      loop.length ? el("div", { class: "ci-scores" }, loop.map((r) => el("div", { class: "ci-score" },
        el("div", { class: "row-title" }, r.icon + " " + r.name + ": " + r.cleared + " of " + r.scheduled + " cleared"),
        bar(r.pct), r.missed && r.kind === "work" ? el("p", { class: "dim" }, r.missed + " missed: nothing earned " + (r.missed === 1 ? "that day." : "those days.")) : null))) : null,
      L.loot ? tiles(L.loot.loot_text ? ["Loot", L.loot.loot_text, "ok"] : null, ["Runs", String(L.loot.runs)],
        ["Hours", L.loot.hours + " h"], L.loot.bosses ? ["Bosses", String(L.loot.bosses), "soon"] : null,
        L.loot.banked_text ? ["Banked", L.loot.banked_text] : null) : null,
      L.noticed.length ? el("div", { class: "ci-noticed" }, el("h3", {}, "MIA Noticed"),
        el("ul", {}, L.noticed.map((n) => el("li", {}, n)))) : null,
      L.quests.length ? el("div", { class: "ci-noticed" }, el("h3", {}, "Quests Finished"),
        el("ul", {}, L.quests.map((q) => el("li", {}, "✓ " + q)))) : null,
      L.highlights.length ? el("details", { class: "ins-list" }, el("summary", {}, "Highlights"),
        el("ul", {}, L.highlights.map((h) => el("li", {}, h)))) : null);
  }

  function ahead(c) {
    const A = c.ahead;
    return [section("This Week", el("span", { class: "dim" }, A.span),
      tiles(["Runs Planned", String(A.runs)], A.projected_text ? ["Projected Loot", A.projected_text, "ok"] : null),
      el("ol", { class: "ci-days" }, A.days.map((d) => el("li", { class: "ci-day" + (d.today ? " today" : "") },
        el("div", { class: "ci-day-name" }, d.today ? "Today" : d.label),
        d.items.length ? el("ul", {}, d.items.map((x) => el("li", { class: "ci-item " + x.kind + (x.boss ? " boss" : "") },
          el("span", { class: "ci-time" }, x.time || ""), el("span", {}, x.icon + " " + x.text),
          x.loot_text ? el("span", { class: "dim" }, x.loot_text) : null)))
          : el("p", { class: "dim" }, "Nothing in the loop: a free day."))))),
    A.quests.length ? section("Quests In Progress", el("a", { class: "btn btn-ghost btn-small", href: "missions.html" }, "Missions"),
      ...A.quests.map((q) => el("div", { class: "ci-score" }, el("div", { class: "row-title" }, q.icon + " " + q.name + " · " + q.pct + "%"), bar(q.pct)))) : null,
    A.next_dungeon && A.next_dungeon.ready ? section("The Next Dungeon", el("a", { class: "btn btn-ghost btn-small", href: "freedom.html" }, "Freedom"),
      el("p", {}, A.next_dungeon.progress_pct + "% unlocked · " + A.next_dungeon.left_text + " to go"), bar(A.next_dungeon.progress_pct)) : null];
  }

  // The design canvas (DEC-0113): the week in a sentence first, three figures, what MIA noticed, the week ahead one
  // line a day, and Debrief Done; the full week's detail folds below.
  function summary(c) {
    const L = c.last;
    const runs = L.loop.find((r) => r.kind === "work");
    return [
      el("header", { class: "ci-top" }, el("span", { class: "pw-label" }, c.title + " · " + L.span),
        el("h2", {}, L.chapter), L.story.length ? el("p", {}, L.story.slice(0, 2).join(" ")) : null),
      el("div", { class: "sh-tiles" },
        el("div", { class: "glass sh-tile" }, el("span", { class: "pw-label" }, "Runs"), el("strong", {}, runs ? runs.cleared + " / " + runs.scheduled : "—")),
        el("div", { class: "glass sh-tile" }, el("span", { class: "pw-label" }, "Loot"), el("strong", { class: "money" }, (L.loot && L.loot.loot_text) || "—")),
        el("div", { class: "glass sh-tile" }, el("span", { class: "pw-label" }, "Quests"), el("strong", {}, String(L.quests.length)))),
      L.noticed.length ? el("section", { class: "glass ci-noticed-card", "aria-label": "What MIA noticed" }, el("span", { class: "pw-label" }, "MIA Noticed"),
        ...L.noticed.slice(0, 3).map((n) => el("p", {}, n))) : null,
      el("section", { class: "glass ci-ahead", "aria-label": "The week ahead" }, el("p", { class: "pw-label" }, "The Week Ahead" + (c.ahead.projected_text ? " · " + c.ahead.projected_text + " projected" : "")),
        ...c.ahead.days.map((d) => el("div", { class: "ci-ahead-row" + (d.today ? " today" : "") },
          el("span", { class: "ci-ahead-day" }, d.today ? "Today" : d.label.split(",")[0]),
          el("span", { class: "ci-ahead-what" }, d.items.length ? d.items.map((x) => x.text).join(", ") : "A free day"),
          el("span", { class: "ci-ahead-extra" }, d.items.map((x) => x.loot_text || "").filter(Boolean).join(" ") || (d.items[0] && d.items[0].time) || "")))),
      c.done ? el("p", { class: "dim ci-done-note" }, "✓ Debrief done for this week.")
        : el("button", { type: "button", class: "btn btn-green ci-debrief", onclick: () => act({ kind: "loop.checkin_done", params: {} }) },
          "Debrief Done · +" + c.xp + " XP"),
    ].filter(Boolean);
  }

  MIAShell.start(async () => {
    const c = await MIA.checkin();
    $("strip").hidden = true;
    $("panel").replaceChildren(...summary(c),
      el("details", { class: "ci-more" }, el("summary", {}, "The whole week"), last(c), ...ahead(c).filter(Boolean)));
  });
})();
