/*
 * skills.js — the Skills screen (claude, 2026-10-06, DEC-0017/0018, H-0013).
 * Renders MIA.skills() (core/web_progress.py): the skill tree by category
 * (your interests first), each skill's level, XP and capability, what a
 * locked one needs, the next honest step, each skill's pathways (Start),
 * challenge chains with their rarity, hidden achievements found, recent
 * achievements and prestige. Changes: pathway.start, character.prestige.
 */
(function () {
  "use strict";
  const { el, act } = MIAShell;
  const $ = (id) => document.getElementById(id);
  const RARITY = ["r-common", "r-uncommon", "r-rare", "r-epic", "r-legendary"];
  const STATUS = { locked: "🔒 Locked", learning: "Learning", practiced: "Practiced", demonstrated: "★ Demonstrated" };
  let page = null;
  let category = decodeURIComponent(location.hash.slice(1)) || null;

  const btn = (label, cls, onclick) => el("button", { type: "button", class: "btn " + cls, onclick }, label);
  const section = (title, actions, ...body) =>
    el("section", { class: "glass money-section" }, el("div", { class: "sect" }, el("h2", {}, title), actions), ...body);
  const bar = (pct) => el("div", { class: "bar" }, el("div", { class: "bar-fill", style: "width:" + Math.min(100, pct) + "%" }));

  function openSkill(s) {
    const dialog = el("dialog", { class: "confirm form-dialog mission-sheet", "aria-label": s.name });
    const close = () => { dialog.close(); dialog.remove(); };
    dialog.append(...[
      el("div", { class: "mission-sheet-head" }, el("span", { class: "mission-icon", "aria-hidden": "true" }, s.icon),
        el("div", {}, el("h3", {}, s.name), el("p", { class: "dim" }, s.category + " · tier " + s.tier))),
      el("p", {}, "Level " + s.level + " · " + s.xp_into_level + "/" + s.xp_for_level + " XP · " + STATUS[s.status]),
      bar(100 * s.xp_into_level / s.xp_for_level),
      s.needs.length && !s.unlocked ? el("p", { class: "locked-note" }, "Unlocks after some XP in: " + s.needs.join(", ")) : null,
      s.this_week ? el("p", { class: "dim" }, "+" + s.this_week + " XP this week") : null,
      el("h4", {}, "Pathways"),
      s.pathways.length ? el("div", { class: "rows" }, s.pathways.map((p) => el("div", { class: "row money-row" },
        el("div", {}, el("div", { class: "row-title" }, p.name),
          el("div", { class: "row-sub" }, p.status === "active" ? "Step " + p.step + " of " + p.steps + ": " + p.step_name
            : (p.status === "completed" ? "Completed · " : "") + p.steps + " steps" + (p.description ? " · " + p.description : ""))),
        p.status === "active" ? el("a", { class: "btn btn-ghost", href: "missions.html" }, "Missions")
          : btn(p.status === "completed" ? "Again" : "Start", "btn-green", () => { close(); act({ kind: "pathway.start", params: { pathway_id: p.id } }); }))))
        : el("p", { class: "dim" }, "No pathway for this skill yet. Ask MIA for a mission that grows it."),
      el("div", { class: "confirm-actions" },
        btn("Ask MIA for a mission", "btn-ghost", () => { close(); MIAShell.talk(true, "Give me a mission that grows my " + s.name + " skill."); }),
        btn("Close", "btn-ghost", close)),
    ].filter(Boolean));
    dialog.oncancel = (e) => { e.preventDefault(); close(); };
    document.body.append(dialog);
    dialog.showModal();
  }

  function skillCard(s) {
    return el("article", { class: "glass skill-card" + (s.unlocked ? "" : " locked") + (s.focus ? " focus" : ""), tabindex: "0", role: "button",
      "aria-label": s.name + ", level " + s.level, onclick: () => openSkill(s),
      onkeydown: (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); openSkill(s); } } },
    el("div", { class: "skill-head" }, el("span", { class: "skill-icon", "aria-hidden": "true" }, s.icon),
      el("div", {}, el("h3", {}, s.name), el("p", { class: "dim" }, s.unlocked ? "Lv " + s.level + " · " + STATUS[s.status] : STATUS.locked))),
    s.unlocked ? bar(100 * s.xp_into_level / s.xp_for_level) : el("p", { class: "locked-note" }, "Needs " + s.needs.join(", ")),
    s.unlocked ? el("p", { class: "dim skill-xp" }, s.xp_into_level + "/" + s.xp_for_level + " XP" + (s.this_week ? " · +" + s.this_week + " this week" : "")) : null,
    s.pathways.some((p) => p.status === "active") ? el("span", { class: "chip chip-soon" }, "On a pathway") : null);
  }

  function rewardsCard() {
    const r = page.rewards;
    if (!r.available) return null;
    return section("Rewards", null,
      el("div", { class: "rows" }, r.chains.map((c) => el("div", { class: "row chain-row rarity " + RARITY[(c.earned || c.next || {}).rarity || 0] },
        el("div", {},
          el("div", { class: "row-title" }, c.icon + " " + c.stat),
          c.earned ? el("div", { class: "row-sub" }, el("span", { class: "rarity-tag" }, c.earned.rarity_name), " " + c.earned.icon + " " + c.earned.name) : null,
          c.next ? el("div", { class: "row-sub" }, "Next: " + c.next.icon + " " + c.next.name + " (" + c.next.rarity_name + ") · " +
            c.value.toLocaleString() + " / " + c.next.threshold.toLocaleString() + (c.unit ? " " + c.unit : "")) : el("div", { class: "row-sub" }, "Maxed out"),
          c.next ? bar(c.next.percent) : null)))),
      r.hidden.length ? el("h4", {}, "Hidden achievements") : null,
      r.hidden.length ? el("div", { class: "rows" }, r.hidden.map((h) => el("div", { class: "row rarity " + RARITY[h.rarity] },
        el("div", {}, el("div", { class: "row-title" }, h.icon + " " + h.name), el("div", { class: "row-sub" }, el("span", { class: "rarity-tag" }, h.rarity_name), " " + h.description))))) : null);
  }

  function sideColumn() {
    const me = page.me;
    return el("div", { class: "stack" },
      section("Next honest step", null, page.focus
        ? el("p", {}, page.focus.icon + " Put some real time toward ", el("strong", {}, page.focus.name), " next: " + page.focus.to_next + " XP to its next level.")
        : el("p", { class: "dim" }, "Nothing to suggest right now.")),
      section("Prestige", null,
        el("p", {}, me.can_prestige ? "Level 100 maxed out! Prestige now for a " + me.next_prestige_color + " badge."
          : "Level " + me.level + "/100. Prestige opens once you max out level 100." + (me.prestige_tier ? " You're prestige " + me.prestige_tier + "." : "")),
        me.can_prestige ? btn("Prestige now", "btn-amber", () => act({ kind: "character.prestige", params: {} })) : null),
      section("Achievements", null, page.achievements.length
        ? el("div", { class: "rows" }, page.achievements.map((a) => el("div", { class: "row" },
          el("div", {}, el("div", { class: "row-title" }, a.title), el("div", { class: "row-sub" }, a.message + " · " + a.when)))))
        : el("p", { class: "dim" }, "No achievements yet. They show up as you level skills.")));
  }

  function trendNote() {
    const t = (page.categories.find((x) => x.name === category) || {}).trend;
    const said = { growing: "↑ Growing: real momentum lately", declining: "↓ Quieter than it was", "not started": "One of your interests, not started yet" };
    return t ? el("span", { class: "chip " + (t === "growing" ? "chip-ok" : "chip-soon") }, said[t]) : null;
  }

  function draw() {
    const c = page.counts;
    $("strip").replaceChildren(
      el("div", { class: "cell ok" }, el("span", { class: "n" }, c.touched + "/" + c.skills), el("span", { class: "t" }, "Skills touched")),
      el("div", { class: "cell soon" }, el("span", { class: "n" }, c.demonstrated), el("span", { class: "t" }, "Demonstrated")),
      el("div", { class: "cell ok" }, el("span", { class: "n" }, "lvl " + page.me.level), el("span", { class: "t" }, "Your level")));
    if (!category || !page.categories.some((x) => x.name === category)) category = page.categories.length ? page.categories[0].name : null;
    $("tabs").hidden = false;
    $("tabs").replaceChildren(...page.categories.map((x) =>
      el("button", { type: "button", role: "tab", "aria-selected": String(x.name === category),
        onclick: () => { category = x.name; history.replaceState(null, "", "#" + encodeURIComponent(x.name)); draw(); } },
      (x.interest ? "★ " : "") + x.name + (x.trend === "growing" ? " ↑" : x.trend === "declining" ? " ↓" : ""))));
    const skills = page.skills.filter((s) => s.category === category);
    $("panel").replaceChildren(
      el("div", { class: "skills-layout" },
        section(category || "Skills", trendNote(), el("div", { class: "skill-grid" }, skills.map(skillCard))),
        sideColumn()),
      rewardsCard() || "");
    MIAShell.levelCard($("level"), page.me);
  }

  MIAShell.start(async () => {
    page = await MIA.skills();
    if (!page.available) {
      $("panel").replaceChildren(el("p", { class: "empty" }, el("strong", {}, "Skills aren't set up on this MIA."), ""));
      return;
    }
    draw();
  });
})();
