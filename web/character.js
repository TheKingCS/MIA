/*
 * character.js — the Character screen (claude, 2026-10-06, DEC-0017/0018,
 * H-0013). Renders MIA.character() (core/web_progress.py): the person's
 * level and prestige, lifetime stats, everything they've unlocked (highest
 * rarity first) and the tally by rarity, prestige emblems, top skills and
 * latest missions. Read only; character art comes later (Zac's call).
 */
(function () {
  "use strict";
  const { el } = MIAShell;
  const $ = (id) => document.getElementById(id);
  const RARITY = ["r-common", "r-uncommon", "r-rare", "r-epic", "r-legendary"];
  let page = null;

  const section = (title, ...body) => el("section", { class: "glass money-section" }, el("div", { class: "sect" }, el("h2", {}, title)), ...body);
  const sectionWith = (title, link, ...body) => el("section", { class: "glass money-section" }, el("div", { class: "sect" }, el("h2", {}, title), link), ...body);
  const day = (iso) => iso ? new Date(iso + "T00:00:00").toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" }) : "";

  function draw() {
    const me = page.me;
    $("hero-name").textContent = me.name || "Character";
    $("hero-tagline").textContent = "Level " + me.level + (me.prestige_tier ? " · Prestige " + me.prestige_tier : "") +
      (page.member_since ? " · since " + day(page.member_since) : "");
    $("strip").replaceChildren(
      el("div", { class: "cell ok" }, el("span", { class: "n" }, me.total_xp.toLocaleString()), el("span", { class: "t" }, "Lifetime XP")),
      el("div", { class: "cell soon" }, el("span", { class: "n" }, me.credits.toLocaleString()), el("span", { class: "t" }, "Credits")),
      el("div", { class: "cell ok" }, el("span", { class: "n" }, page.missions_completed || 0), el("span", { class: "t" }, "Missions done")));
    const stats = page.stats.length ? el("div", { class: "stat-grid" }, page.stats.map((s) => el("div", { class: "glass stat-tile" },
      el("span", { class: "ico", "aria-hidden": "true" }, s.icon),
      el("strong", {}, s.value.toLocaleString() + (s.unit ? " " + s.unit : "")), el("small", {}, s.name)))) : el("p", { class: "dim" }, "No stats yet.");
    const collection = page.collection.length
      ? el("div", { class: "rows" }, page.collection.map((c) => el("div", { class: "row rarity " + RARITY[c.rarity] },
        el("div", {}, el("div", { class: "row-title" }, c.icon + " " + c.name),
          el("div", { class: "row-sub" }, el("span", { class: "rarity-tag" }, c.rarity_name), " " + c.description)))))
      : el("p", { class: "empty" }, el("strong", {}, "Nothing unlocked yet."), "Go do something real: log workouts, finish missions, cook.");
    const tally = page.rarity.length ? el("div", { class: "chip-row" }, page.rarity.map((r) =>
      el("span", { class: "chip rarity " + RARITY[r.rarity] }, el("span", { class: "rarity-tag" }, r.rarity_name), " ×" + r.count))) : null;
    $("panel").replaceChildren(
      el("div", { class: "glass character-portrait" + (me.prestige_color ? " prestige-" + me.prestige_color : "") },
        el("span", { class: "character-avatar", "aria-hidden": "true" }, "🧙"),
        el("div", {}, el("strong", {}, "Level " + me.level), el("small", { class: "dim" }, "Character art is coming later."))),
      section("Lifetime stats", stats),
      el("div", { class: "two-up" },
        sectionWith("Top skills", el("a", { class: "btn btn-ghost", href: "skills.html" }, "All skills"), page.top_skills && page.top_skills.length
          ? el("div", { class: "rows" }, page.top_skills.map((s) => el("div", { class: "row" }, el("div", { class: "row-title" }, s.icon + " " + s.name), el("span", { class: "chip" }, "Lv " + s.level))))
          : el("p", { class: "dim" }, "No skill XP yet.")),
        sectionWith("Latest missions", el("a", { class: "btn btn-ghost", href: "missions.html" }, "Missions"), page.latest_missions && page.latest_missions.length
          ? el("div", { class: "rows" }, page.latest_missions.map((m) => el("div", { class: "row" }, el("div", { class: "row-title" }, m.icon + " " + m.name), el("span", { class: "dim" }, day(m.when)))))
          : el("p", { class: "dim" }, "No missions completed yet."))),
      section("Collection", tally, collection),
      page.emblems.length ? section("Prestige emblems", el("div", { class: "chip-row" }, page.emblems.map((e) =>
        el("span", { class: "chip prestige-" + e.color }, "🏆 " + e.name)))) : "");
  }

  MIAShell.start(async () => {
    page = await MIA.character();
    if (!page.available) {
      $("panel").replaceChildren(el("p", { class: "empty" }, el("strong", {}, "Sign in to see your character."), ""));
      return;
    }
    draw();
  });
})();
