/*
 * checkin.js — the Sunday check-in (claude, 2026-10-27, DEC-0047 rule 5).
 * Renders MIA.checkin() (core/weekly_checkin.py): last week (the story, the
 * loop's honest score, loot, what MIA noticed, quests finished) and the
 * week ahead, day by day (runs with projected loot, rhythms, calendar
 * events), quests in progress and the next dungeon. "Debrief Done" is the
 * one action (loop.checkin_done). Formatting only.
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

  MIAShell.start(async () => {
    const c = await MIA.checkin();
    $("hero-name").textContent = c.title;
    const L = c.last;
    const runs = L.loop.find((r) => r.kind === "work");
    $("strip").replaceChildren(
      el("div", { class: "cell ok" }, el("span", { class: "n" }, runs ? runs.cleared + "/" + runs.scheduled : "—"), el("span", { class: "t" }, "Runs Cleared")),
      el("div", { class: "cell ok" }, el("span", { class: "n" }, (L.loot && L.loot.loot_text) || "—"), el("span", { class: "t" }, "Last Week's Loot")),
      el("div", { class: "cell ok" }, el("span", { class: "n" }, c.ahead.projected_text || "—"), el("span", { class: "t" }, "This Week")));
    $("panel").replaceChildren(last(c), ...ahead(c).filter(Boolean),
      el("div", { class: "row-buttons ci-done" }, c.done
        ? el("p", { class: "dim" }, "✓ Debrief done for this week.")
        : el("button", { type: "button", class: "btn btn-amber", onclick: () => act({ kind: "loop.checkin_done", params: {} }) },
          "Debrief Done · +" + c.xp + " XP")));
  });
})();
