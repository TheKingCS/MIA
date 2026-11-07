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
    $("hero-name").textContent = "Character";  // the name is on the portrait card below (the canvas)
    $("hero-tagline").textContent = "Level " + me.level + (me.prestige_tier ? " · Prestige " + me.prestige_tier : "") +
      (page.member_since ? " · since " + day(page.member_since) : "");
    $("strip").replaceChildren(
      el("div", { class: "cell ok" }, el("span", { class: "n" }, me.total_xp.toLocaleString()), el("span", { class: "t" }, "Lifetime XP")),
      el("a", { class: "cell soon", href: "shop.html", title: "Spend them in the Reward Shop" }, el("span", { class: "n" }, me.credits.toLocaleString()), el("span", { class: "t" }, "Credits · Shop ›")),
      el("div", { class: "cell ok" }, el("span", { class: "n" }, page.missions_completed || 0), el("span", { class: "t" }, "Missions done")));
    const stats = page.stats.length ? el("div", { class: "stat-grid" }, page.stats.map((s) => el("div", { class: "glass stat-tile" },
      el("span", { class: "ico", "aria-hidden": "true" }, s.icon),
      el("strong", {}, s.value.toLocaleString() + (s.unit ? " " + s.unit : "")), el("small", {}, s.name)))) : el("p", { class: "dim" }, "No stats yet.");
    // Real character stats (DEC-0028): six attributes, 1 to 20, from what you've really done.
    const attrs = (page.attributes || []).length ? el("div", { class: "attr-grid" }, page.attributes.map((a) =>
      el("div", { class: "glass attr", title: a.about },
        el("div", { class: "attr-head" }, el("span", { class: "attr-ico", "aria-hidden": "true" }, a.icon),
          el("span", { class: "attr-name" }, a.name), el("strong", { class: "attr-value" }, String(a.value))),
        el("div", { class: "attr-bar", role: "meter", "aria-valuenow": String(a.value), "aria-valuemin": "1", "aria-valuemax": String(a.max),
          "aria-label": a.name + " " + a.value + " of " + a.max },
          el("span", { class: "attr-train", style: "width:" + (100 * (1 + a.training) / a.max) + "%" }),
          el("span", { class: "attr-recent", style: "width:" + (100 * a.recent / a.max) + "%" }),
          (a.buffs || []).length ? el("span", { class: "attr-buff", style: "width:" + (100 * a.buffs.length / a.max) + "%" }) : null),
        el("p", { class: "attr-from" }, a.from.length ? a.from.join(" · ") : a.about),
        (a.buffs || []).length ? el("p", { class: "attr-buffs" }, a.buffs.join(" · ")) : null,
        a.watch.length ? el("p", { class: "attr-watch" }, "⌚ A watch adds: " + a.watch.join(", ")) : null))) : null;
    const collection = page.collection.length
      ? el("div", { class: "rows" }, page.collection.map((c) => el("div", { class: "row rarity " + RARITY[c.rarity] },
        el("div", {}, el("div", { class: "row-title" }, c.icon + " " + c.name),
          el("div", { class: "row-sub" }, el("span", { class: "rarity-tag" }, c.rarity_name), " " + c.description)))))
      : el("p", { class: "empty" }, el("strong", {}, "Nothing unlocked yet."), "Go do something real: log workouts, finish missions, cook.");
    const tally = page.rarity.length ? el("div", { class: "chip-row" }, page.rarity.map((r) =>
      el("span", { class: "chip rarity " + RARITY[r.rarity] }, el("span", { class: "rarity-tag" }, r.rarity_name), " ×" + r.count))) : null;
    // The design canvas (DEC-0113): the portrait, level, prestige and the XP meter first; then Stats (the six
    // attributes, each with its meter), the collection by rarity, top skills; the rest below.
    const ROMAN = ["", "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X"];
    const pct = me.xp_for_level ? Math.round(100 * me.xp_into_level / me.xp_for_level) : 0;
    const unlocked = page.rarity.reduce((t, r) => t + r.count, 0);
    $("strip").hidden = true;
    $("panel").replaceChildren(...[
      el("section", { class: "glass ch-hero" + (me.prestige_color ? " prestige-" + me.prestige_color : "") },
        el("div", { class: "ch-portrait", role: "img", "aria-label": "Character art placeholder" }),
        el("h2", {}, me.name || "You"),
        el("div", { class: "ch-level" }, el("span", { class: "pw-label" }, "Level"), el("strong", {}, String(me.level)),
          me.prestige_tier ? el("span", { class: "pw-label" }, "Prestige") : null, me.prestige_tier ? el("span", { class: "ch-prestige" }, ROMAN[me.prestige_tier] || String(me.prestige_tier)) : null),
        el("div", { class: "ch-xp" }, el("div", { class: "meter", role: "meter", "aria-valuenow": String(pct), "aria-valuemin": "0", "aria-valuemax": "100",
          "aria-label": me.xp_into_level + " of " + me.xp_for_level + " XP to level " + (me.level + 1) }, el("div", { class: "meter-fill", style: "width:" + pct + "%" })),
          el("span", {}, me.total_xp.toLocaleString() + " lifetime XP")),
        el("a", { class: "ch-credits", href: "shop.html" }, me.credits.toLocaleString() + " credits · Reward Shop ›")),
      (page.attributes || []).length ? el("section", { class: "glass ch-panel", "aria-label": "Stats" }, el("p", { class: "pw-label" }, "Stats"),
        el("div", { class: "ch-stats" }, ...page.attributes.map((a) => el("div", { class: "ch-stat", title: a.from.length ? a.from.join(" · ") : a.about },
          el("span", { class: "dim" }, a.name), el("strong", {}, String(a.value)),
          el("div", { class: "meter" }, el("div", { class: "meter-fill", style: "width:" + Math.round(100 * a.value / a.max) + "%" })))))) : null,
      el("section", { class: "glass ch-panel", "aria-label": "Collection" }, el("p", { class: "pw-label" }, "Collection · " + unlocked + " Unlocked"),
        el("div", { class: "ch-rarity" }, ...page.rarity.map((r) => el("div", { class: "ch-r " + RARITY[r.rarity] },
          el("strong", {}, String(r.count)), el("span", {}, r.rarity_name))))),
      el("section", { class: "glass ch-panel", "aria-label": "Top skills" }, el("div", { class: "ch-head" }, el("p", { class: "pw-label" }, "Top Skills"),
        el("a", { href: "skills.html" }, "All skills ›")),
        ...(page.top_skills && page.top_skills.length ? page.top_skills.map((s) => el("div", { class: "ch-row" }, el("span", {}, s.name), el("span", { class: "ch-lv" }, "Lv " + s.level)))
          : [el("p", { class: "dim" }, "No skill XP yet.")])),
      section("Buffs", (page.buffs || []).length ? MIAShell.buffChips(page.buffs)
        : el("p", { class: "dim" }, "No buffs right now. Work out, cook, write, catch up with someone: good days earn them.")),
      page.chronicle ? sectionWith("The Chronicle", el("a", { class: "btn btn-ghost", href: "chronicle.html" }, "Read It"),
        el("div", { class: "chron-teaser" }, el("span", { class: "chron-title" }, page.chronicle.title + " · " + page.chronicle.dates +
          (page.chronicle.so_far ? " · so far" : "")), el("h3", {}, page.chronicle.name),
          ...page.chronicle.story.map((line) => el("p", { class: "dim" }, line)))) : null,
      attrs ? el("details", { class: "glass money-section ch-more" }, el("summary", {}, el("h2", {}, "How your stats are made")),
        el("p", { class: "dim" }, "Blue is training (your skills), which never goes down. Green is what you've done in the last 30 days. Gold is a buff."), attrs) : null,
      section("Lifetime stats", stats),
      sectionWith("Latest missions", el("a", { class: "btn btn-ghost", href: "missions.html" }, "Missions"), page.latest_missions && page.latest_missions.length
        ? el("div", { class: "rows" }, page.latest_missions.map((m) => el("div", { class: "row" }, el("div", { class: "row-title" }, m.icon + " " + m.name), el("span", { class: "dim" }, day(m.when)))))
        : el("p", { class: "dim" }, "No missions completed yet.")),
      section("Everything unlocked", tally, collection),
      page.emblems.length ? section("Prestige emblems", el("div", { class: "chip-row" }, page.emblems.map((e) =>
        el("span", { class: "chip prestige-" + e.color }, "🏆 " + e.name)))) : null,
    ].filter(Boolean));
    const portrait = document.querySelector(".ch-portrait");
    if (portrait && window.MIAIcons) MIAIcons.badge(portrait, "character");
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
