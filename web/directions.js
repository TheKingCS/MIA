/*
 * directions.js — My Directions (claude, 2026-11-08, DEC-0141/0143).
 * Renders MIA.directions() (core/web_directions.py): today's seed and one thing
 * within reach (both from real state, never invented), then each standing
 * direction in the person's own words, with how MIA encourages it and the little
 * nudges she may raise. Set, change, pause, resume and let go are direction.*
 * actions, so each is approved and undoable. No logic here: the engine decides.
 */
(function () {
  "use strict";
  const { el, form } = MIAShell;
  const $ = (id) => document.getElementById(id);
  const button = (label, onclick, cls) => el("button", { type: "button", class: "btn " + (cls || "btn-ghost") + " btn-small", onclick }, label);
  const day = (iso) => iso ? new Date(iso + "T00:00:00").toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" }) : "";

  async function add(fields) {
    const v = await form("Set a Direction", fields, {});
    if (v) MIAShell.act({ kind: "direction.add", params: v });
  }

  async function change(d, fields) {
    const v = await form("Change " + d.title, fields, d.values);
    if (v) MIAShell.act({ kind: "direction.edit", params: { direction_id: d.id, ...v } });
  }

  // The two cards at the top: a little thing toward them today, and something already in reach.
  function inspiration(data) {
    const cards = [];
    if (data.seed) cards.push(el("div", { class: "glass dir-card dir-seed" },
      el("p", { class: "pw-label" }, "Today's Seed"),
      el("p", { class: "dir-card-line" }, data.seed),
      el("p", { class: "dim dir-card-foot" }, "From your directions, the season and what's on your shelf. A new one tomorrow.")));
    if (data.right_now) cards.push(el("div", { class: "glass dir-card dir-now" },
      el("p", { class: "pw-label" }, "Within Reach"),
      el("p", { class: "dir-card-line" }, data.right_now)));
    return cards.length ? el("section", { class: "dir-cards" }, ...cards) : null;
  }

  function direction(d, fields) {
    return el("article", { class: "glass dir-item" + (d.active ? "" : " paused") },
      el("div", { class: "dir-head" },
        el("h3", { class: "dir-title" }, d.title),
        el("span", { class: "dir-state" + (d.active ? " on" : "") }, d.active ? "In force" : "Paused")),
      el("p", { class: "dir-words" }, d.statement),
      d.encourage ? el("p", { class: "dir-how" }, el("span", { class: "dim" }, "How MIA encourages it: "), d.encourage) : null,
      d.nudges.length ? el("div", { class: "dir-nudges" }, ...d.nudges.map((n) => el("span", { class: "dir-nudge" }, n))) : null,
      el("div", { class: "dir-foot" },
        el("span", { class: "dim" }, d.since ? "Since " + day(d.since) : ""),
        el("div", { class: "row-buttons" },
          button("Change", () => change(d, fields)),
          d.active
            ? button("Pause", () => MIAShell.act({ kind: "direction.pause", params: { direction_id: d.id } }, { quick: true }))
            : button("Resume", () => MIAShell.act({ kind: "direction.resume", params: { direction_id: d.id } }, { quick: true })),
          button("Let Go", () => MIAShell.act({ kind: "direction.remove", params: { direction_id: d.id } }), "btn-quiet"))));
  }

  function paint(data) {
    if (!data.available) {
      $("dir-sub").textContent = "Directions aren't set up on this MIA yet.";
      $("panel").replaceChildren();
      return;
    }
    const fields = data.forms.direction.fields;
    const count = data.directions.length;
    $("dir-sub").textContent = count
      ? "What you're steering by. MIA keeps it in mind and leans that way when it fits, never preachy."
      : "Nothing set yet. A direction is a value you're steering your life by, in your own words.";
    const full = count >= data.max;
    $("panel").replaceChildren(...[
      inspiration(data),
      el("div", { class: "dir-actions" },
        el("button", { type: "button", class: "btn btn-green btn-big", disabled: full || null, onclick: () => add(fields) },
          "Set a Direction"),
        full ? el("span", { class: "dim" }, "You have " + data.max + ". Let one go to set another.") : null),
      count ? el("section", { class: "dir-list" },
        el("p", { class: "pw-label" }, data.in_force + " in force" + (count > data.in_force ? " · " + (count - data.in_force) + " paused" : "")),
        ...data.directions.map((d) => direction(d, fields))) : null,
      el("p", { class: "dim dir-say" }, "Say \"what are my directions?\", \"add a direction: grow and cook my own food\", " +
        "\"pause the whimsy one\" or \"inspire me\" any time."),
    ].filter(Boolean));
  }

  MIAShell.start(async () => { paint(await MIA.directions()); }, { refreshOnChange: true });
})();
