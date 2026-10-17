/*
 * party.js — Party and guild (claude, 2026-10-17, DEC-0028). Renders
 * MIA.party() (core/party.py): raids going (everyone's jobs, who has
 * what, +1 on your own), raids to start with who's in, your own raid, and
 * the household leaderboard (opt-in: only people who joined it, wins this
 * week, never money). Every button proposes an action from
 * core/game_actions.py or core/mission_actions.py. Formatting only.
 */
(function () {
  "use strict";
  const { el, act, form } = MIAShell;
  const $ = (id) => document.getElementById(id);
  let page = null;

  const btn = (label, cls, onclick) => el("button", { type: "button", class: "btn " + cls, onclick }, label);
  const section = (title, actions, ...body) =>
    el("section", { class: "glass money-section" }, el("div", { class: "sect" }, el("h2", {}, title), actions), ...body);

  // Who's in: everyone in the household, ticked to start with.
  function pickCrew(title) {
    return new Promise((resolve) => {
      const dialog = el("dialog", { class: "confirm form-dialog", "aria-label": title });
      const boxes = page.household.map((p) => el("label", { class: "setup-chip" },
        el("input", { type: "checkbox", value: p.id, checked: true }), el("span", {}, p.me ? p.name + " (you)" : p.name)));
      const close = (v) => { dialog.close(); dialog.remove(); resolve(v); };
      dialog.append(el("h3", {}, title), el("p", { class: "dim" }, "Who's in? MIA shares the jobs out round the table."),
        el("div", { class: "party-crew" }, boxes),
        el("div", { class: "confirm-actions" },
          btn("Next", "btn-amber", () => close(boxes.map((b) => b.querySelector("input")).filter((i) => i.checked).map((i) => i.value).join(","))),
          btn("Cancel", "btn-ghost", () => close(null))));
      dialog.oncancel = (e) => { e.preventDefault(); close(null); };
      document.body.append(dialog);
      dialog.showModal();
    });
  }
  async function startRaid(r) {
    const people = await pickCrew(r.icon + " " + r.name);
    if (people !== null) act({ kind: "raid.start", params: { raid_id: r.id, people } });
  }
  async function ownRaid() {
    const v = await form("Make A Raid", [
      { name: "name", label: "Raid", type: "text", required: true, options: [], default: null },
      { name: "icon", label: "Icon (an emoji)", type: "text", required: false, options: [], default: "⚔️" },
      { name: "objectives", label: "The jobs, one per line", type: "textarea", required: true, options: [], default: null }], {});
    if (!v) return;
    const people = await pickCrew(v.name || "Your Raid");
    if (people !== null) act({ kind: "raid.add", params: Object.assign({ people }, v) });
  }

  function raidCard(r) {
    const active = r.status === "active";
    return el("article", { class: "glass quest-card raid-card" + (active ? "" : " finished") },
      el("div", { class: "quest-head" },
        el("span", { class: "quest-icon", "aria-hidden": "true" }, active ? r.icon : "🏆"),
        el("div", { class: "quest-title" }, el("h3", {}, r.name),
          el("p", { class: "quest-kind" }, "Household Raid · " + r.done + "/" + r.total + " jobs")),
        el("span", { class: "chip " + (active ? "chip-soon" : "chip-ok") }, active ? r.percent + "%" : "Won")),
      el("div", { class: "bar", role: "progressbar", "aria-valuenow": String(r.percent), "aria-valuemin": "0", "aria-valuemax": "100" },
        el("div", { class: "bar-fill", style: "width:" + r.percent + "%" })),
      el("div", { class: "chip-row" }, r.crew.map((c) => el("span", { class: "chip" + (c.me ? " chip-ok" : "") }, c.name + " " + c.done + "/" + c.total))),
      el("ul", { class: "objective-list" }, r.objectives.map((o) => el("li", { class: o.done ? "done" : "" },
        el("span", { class: "objective-check", "aria-hidden": "true" }, o.done ? "✓" : ""),
        el("span", { class: "objective-text" }, o.description, el("small", {}, " (" + o.for + ")")),
        active && !o.done && o.mine ? btn("Done", "btn-green btn-small", () => act({ kind: "objective.tick", params: { mission_id: r.id, index: o.index } })) : null))),
      el("p", { class: "dim boss-lines" }, r.reward),
      r.ready ? el("div", { class: "row-buttons" }, btn("Claim The Win", "btn-green", () => act({ kind: "mission.complete", params: { mission_id: r.id } }))) : null);
  }

  function board() {
    const lb = page.leaderboard;
    const toggle = btn(lb.on ? "Leave" : "Join", lb.on ? "btn-ghost btn-small" : "btn-amber btn-small",
      () => act({ kind: "party.leaderboard", params: { on: !lb.on } }));
    return section("This Week's Leaderboard", toggle,
      el("p", { class: "dim" }, "Only people who joined are on it. It counts wins (things done), never money, never what wasn't done."),
      lb.rows.length ? el("div", { class: "rows" }, lb.rows.map((r) => el("div", { class: "row money-row" + (r.me ? " me" : "") },
        el("div", {}, el("div", { class: "row-title" }, (r.medal ? r.medal + " " : "") + r.name + (r.me ? " (you)" : "")),
          el("div", { class: "row-sub" }, "Level " + r.level)),
        el("span", { class: "chip chip-ok" }, r.wins + (r.wins === 1 ? " win" : " wins")))))
        : el("p", { class: "empty" }, "Nobody's on it yet. Join, and anyone else in your household can too."));
  }

  function draw() {
    const active = page.raids.filter((r) => r.status === "active");
    $("strip").replaceChildren(
      el("div", { class: "cell ok" }, el("span", { class: "n" }, page.household.length), el("span", { class: "t" }, "In Your Household")),
      el("div", { class: "cell soon" }, el("span", { class: "n" }, active.length), el("span", { class: "t" }, "Raids On")),
      el("div", { class: "cell ok" }, el("span", { class: "n" }, page.leaderboard.rows.length), el("span", { class: "t" }, "On The Board")));
    $("panel").replaceChildren(...[
      section("Raids", null, page.raids.length ? el("div", { class: "mission-grid" }, page.raids.map(raidCard))
        : el("p", { class: "empty" }, "No raid going. Start one below: everyone gets their jobs, and everyone shares the reward.")),
      section("Start A Raid", btn("Make Your Own", "btn-ghost", ownRaid),
        el("div", { class: "mission-grid" }, page.starters.map((r) => el("article", { class: "glass quest-card offer" },
          el("div", { class: "quest-head" }, el("span", { class: "quest-icon", "aria-hidden": "true" }, r.icon),
            el("div", { class: "quest-title" }, el("h3", {}, r.name), el("p", { class: "quest-kind" }, r.objectives.length + " jobs"))),
          el("p", { class: "dim quest-summary" }, r.summary),
          el("p", { class: "quest-chapters" }, r.objectives.join(" · ")),
          el("div", { class: "row-buttons" }, btn("Start Raid", "btn-amber btn-small", () => startRaid(r))))))),
      board(),
    ]);
  }

  MIAShell.start(async () => {
    page = await MIA.party();
    if (!page.available) { $("panel").replaceChildren(el("p", { class: "empty" }, "Missions aren't set up on this MIA.")); return; }
    draw();
  });
})();
