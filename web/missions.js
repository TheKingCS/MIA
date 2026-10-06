/*
 * missions.js — the Missions screen (claude, 2026-10-06, DEC-0017/0018, H-0013).
 * Renders MIA.missions() (core/web_progress.py): active missions (ready to
 * complete first), daily missions with streaks, completed and set-aside ones;
 * each opens to its objectives (+1, add, remove), rewards and the skills it
 * teaches, with Complete, Give up for now, Pick back up, Edit and Delete.
 * Every change is a mission action (core/mission_actions.py). Formatting only.
 */
(function () {
  "use strict";
  const { el, act, form } = MIAShell;
  const $ = (id) => document.getElementById(id);
  const TABS = [["active", "Active"], ["daily", "Daily"], ["completed", "Completed"], ["set_aside", "Set aside"]];
  let page = null;
  let tab = TABS.some(([t]) => t === location.hash.slice(1)) ? location.hash.slice(1) : "active";

  const btn = (label, cls, onclick) => el("button", { type: "button", class: "btn " + cls, onclick }, label);
  const buttons = (...list) => el("div", { class: "row-buttons" }, list.filter(Boolean));
  const day = (iso) => iso ? new Date(iso + "T00:00:00").toLocaleDateString(undefined, { month: "short", day: "numeric" }) : "";
  const DIFF = { EASY: "chip-ok", NORMAL: "", HARD: "chip-bad" };
  const section = (title, actions, ...body) =>
    el("section", { class: "glass money-section" }, el("div", { class: "sect" }, el("h2", {}, title), actions), ...body);

  function rewards(m) {
    const bits = [m.reward_xp ? "+" + m.reward_xp + " XP" : null, m.reward_credits ? "+" + m.reward_credits + " credits" : null,
      ...m.skill_rewards.map((s) => "+" + s.xp + " " + s.name)].filter(Boolean);
    return bits.length ? bits.join(" · ") : null;
  }
  const bar = (pct) => el("div", { class: "bar", role: "progressbar", "aria-valuenow": String(pct), "aria-valuemin": "0", "aria-valuemax": "100" },
    el("div", { class: "bar-fill", style: "width:" + pct + "%" }));

  // ------------------------------------------------------------ changes
  async function add() {
    const v = await form("A new mission", page.forms.mission.fields, {});
    if (v) act({ kind: "mission.add", params: v });
  }
  async function edit(m) {
    const v = await form("Edit " + m.name, page.forms.mission.fields, m.values);
    if (v) act({ kind: "mission.edit", params: Object.assign({ mission_id: m.id }, v) });
  }
  async function addObjective(m) {
    const v = await form("Add an objective to " + m.name, page.forms.objective.fields, {});
    if (v) act({ kind: "objective.add", params: Object.assign({ mission_id: m.id }, v) });
  }
  async function abandon(m) {
    const v = await form("Give up on " + m.name + " for now?", page.forms.abandon.fields, {});
    if (v) act({ kind: "mission.abandon", params: Object.assign({ mission_id: m.id }, v) });
  }
  async function teaches(m) {
    const v = await form(m.name + " also teaches…", page.forms.skill_reward.fields, {}, { skills: page.skills });
    if (v) act({ kind: "mission.skill_reward", params: Object.assign({ mission_id: m.id }, v) });
  }
  const tick = (m, o) => act({ kind: "objective.tick", params: { mission_id: m.id, index: o.index } });

  // ------------------------------------------------------------ a mission, opened
  function sheet(m) {
    const dialog = el("dialog", { class: "confirm form-dialog mission-sheet", "aria-label": m.name });
    const close = () => { dialog.close(); dialog.remove(); };
    const then = (fn) => () => { close(); fn(m); };
    const active = m.status === "active";
    dialog.append(...[
      el("div", { class: "mission-sheet-head" }, el("span", { class: "mission-icon", "aria-hidden": "true" }, m.icon),
        el("div", {}, el("h3", {}, m.name), el("p", { class: "dim" }, [m.area, m.pathway, m.from_mia ? "From MIA" : null].filter(Boolean).join(" · ")))),
      m.summary ? el("p", { class: "mission-summary" }, m.summary) : null,
      el("div", { class: "chip-row" }, el("span", { class: "chip " + (DIFF[m.difficulty] || "") }, m.difficulty.toLowerCase()),
        m.streak ? el("span", { class: "chip chip-soon" }, "🔥 " + m.streak + "-day streak") : null,
        m.party.length ? el("span", { class: "chip" }, "👥 " + m.party.join(", ")) : null,
        m.status !== "active" ? el("span", { class: "chip" }, m.status === "abandoned" ? "set aside" + (m.abandon_reason ? ": " + m.abandon_reason.toLowerCase() : "") : m.status) : null),
      el("h4", {}, "Objectives " + (m.total ? m.done + "/" + m.total : "")),
      m.objectives.length ? el("ul", { class: "objective-list" }, m.objectives.map((o) => el("li", { class: o.done ? "done" : "" },
        el("span", { class: "objective-check", "aria-hidden": "true" }, o.done ? "✓" : ""),
        el("span", { class: "objective-text" }, o.description + (o.for ? " (" + o.for + ")" : ""),
          o.target > 1 ? el("small", {}, " " + o.progress + "/" + o.target) : null),
        active && !o.done && !o.counts_itself ? btn("+1", "btn-green btn-small", () => { close(); tick(m, o); }) : null,
        active ? btn("✕", "btn-ghost btn-small", () => { close(); act({ kind: "objective.delete", params: { mission_id: m.id, index: o.index } }); }) : null)))
        : el("p", { class: "dim" }, "No objectives yet. Add one, like “Clean the gutters”."),
      m.my_part ? el("p", { class: "dim" }, "Your part: " + m.my_part.done + "/" + m.my_part.total) : null,
      rewards(m) ? el("p", { class: "mission-rewards" }, "Rewards: " + rewards(m) + (m.rewards_given ? " (earned)" : "")) : null,
      m.unlocks_recipes.length ? el("p", { class: "dim" }, "Unlocks the recipe" + (m.unlocks_recipes.length > 1 ? "s " : " ") + m.unlocks_recipes.join(", ")) : null,
      m.asset ? el("p", { class: "dim" }, "For ", el("a", { href: "asset.html?id=" + encodeURIComponent(m.asset.id) }, m.asset.name)) : null,
      el("div", { class: "confirm-actions mission-actions" },
        active ? btn("Complete", "btn-green", then((x) => act({ kind: "mission.complete", params: { mission_id: x.id } }))) : null,
        active ? btn("Add objective", "btn-ghost", then(addObjective)) : null,
        btn("Teaches a skill", "btn-ghost", then(teaches)),
        active ? btn("Give up for now", "btn-ghost", then(abandon)) : btn("Pick back up", "btn-amber", then((x) => act({ kind: "mission.reopen", params: { mission_id: x.id } }))),
        btn("Edit", "btn-ghost", then(edit)),
        btn("Delete", "btn-ghost", then((x) => act({ kind: "mission.delete", params: { mission_id: x.id } }))),
        btn("Close", "btn-ghost", close)),
    ].filter(Boolean));
    dialog.oncancel = (e) => { e.preventDefault(); close(); };
    document.body.append(dialog);
    dialog.showModal();
  }

  // ------------------------------------------------------------ cards
  function card(m) {
    const meta = [m.area, m.total ? m.done + "/" + m.total + " objectives" : "no objectives yet", m.streak ? "🔥 " + m.streak : null]
      .filter(Boolean).join(" · ");
    return el("article", { class: "glass mission-card" + (m.ready ? " ready" : "") + (m.status !== "active" ? " finished" : ""),
      tabindex: "0", role: "button", "aria-label": "Open " + m.name,
      onclick: () => sheet(m), onkeydown: (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); sheet(m); } } },
    el("div", { class: "mission-top" },
      el("span", { class: "mission-icon", "aria-hidden": "true" }, m.icon),
      el("div", { class: "mission-title" }, el("h3", {}, m.name), el("p", { class: "dim" }, meta)),
      el("div", { class: "mission-chips" },
        m.from_mia ? el("span", { class: "chip chip-soon" }, "✦ MIA") : null,
        el("span", { class: "chip " + (DIFF[m.difficulty] || "") }, m.difficulty.toLowerCase()))),
    m.status === "active" ? bar(m.percent) : null,
    el("div", { class: "mission-foot" },
      el("span", { class: "mission-rewards" }, rewards(m) || ""),
      m.ready ? btn("Complete", "btn-green btn-small", (e) => { e.stopPropagation(); act({ kind: "mission.complete", params: { mission_id: m.id } }); })
        : m.status === "active" ? (() => { const next = m.objectives.find((o) => !o.done && !o.counts_itself);
          return next ? btn("+1 " + next.description, "btn-ghost btn-small", (e) => { e.stopPropagation(); tick(m, next); }) : null; })()
          : el("span", { class: "dim" }, m.status === "completed" ? "Done " + day(m.updated) : "Set aside " + day(m.updated))));
  }

  const EMPTY = {
    active: "No active missions. Add one, or ask MIA for one.",
    daily: "No daily missions. Ask MIA: “give me a daily push-up mission”.",
    completed: "Nothing completed in the last two months yet.",
    set_aside: "Nothing set aside.",
  };

  function draw() {
    const c = page.counts;
    $("strip").replaceChildren(
      el("div", { class: "cell ok" }, el("span", { class: "n" }, c.active), el("span", { class: "t" }, "Active")),
      el("div", { class: "cell soon" }, el("span", { class: "n" }, c.ready), el("span", { class: "t" }, "Ready to complete")),
      el("div", { class: "cell ok" }, el("span", { class: "n" }, c.completed), el("span", { class: "t" }, "Completed")));
    $("tabs").hidden = false;
    $("tabs").replaceChildren(...TABS.map(([id, l]) =>
      el("button", { type: "button", role: "tab", "aria-selected": String(id === tab), onclick: () => { tab = id; history.replaceState(null, "", "#" + id); draw(); } },
        l + (page[id].length ? " " + page[id].length : ""))));
    const list = page[tab];
    $("panel").replaceChildren(section(TABS.find(([t]) => t === tab)[1] + " missions",
      buttons(btn("Ask MIA for one", "btn-ghost", () => MIAShell.talk(true, "Give me a new mission based on what's going on in my life.")),
        btn("Add mission", "btn-amber", add)),
      list.length ? el("div", { class: "mission-grid" }, list.map(card)) : el("p", { class: "empty" }, EMPTY[tab])));
    MIAShell.levelCard($("level"), page.me);
  }

  MIAShell.start(async () => {
    page = await MIA.missions();
    if (!page.available) {
      $("panel").replaceChildren(el("p", { class: "empty" }, el("strong", {}, "Missions aren't set up on this MIA."), ""));
      return;
    }
    draw();
  });
})();
