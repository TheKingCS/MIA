/*
 * worlds.js — Living Worlds (claude, 2026-11-08, DEC-0134 Phases 1 and 2).
 * Renders MIA.worlds(campaign) (core/web_worlds.py): your character and who they
 * are in each world; the worlds, each with its campaigns; one campaign opened with
 * the character's version in it (stats, skills, what they carry) and its quests.
 * Making a world, a campaign, your character, their version in a campaign, a quest,
 * finishing one, and pausing / resuming / ending a campaign are world.* actions,
 * so each is approved and undoable. Playing (Phase 2): in a campaign in play, say what
 * your character does and world.turn plays it with MIA as Dungeon Master (the model
 * proposes, the dice and code decide); the story so far is the campaign's own history
 * (core/web_worlds._story, from the book's turns). All fiction: no real XP. No logic here.
 */
(function () {
  "use strict";
  const { el, form } = MIAShell;
  const $ = (id) => document.getElementById(id);
  const button = (label, onclick, cls) => el("button", { type: "button", class: "btn " + (cls || "btn-ghost") + " btn-small", onclick }, label);
  const day = (iso) => iso ? new Date(iso + "T00:00:00").toLocaleDateString(undefined, { month: "short", day: "numeric" }) : "";
  let current = new URLSearchParams(location.search).get("campaign") || "";
  let forms = {};
  let playing = "";  // the campaign a turn is being played in right now

  async function play(c) {
    const box = $("lw-do");
    const said = box ? box.value.trim() : "";
    if (!said || playing) return;
    playing = c.id;
    paint(last);
    const done = await MIAShell.act({ kind: "world.turn", params: { campaign_id: c.id, action: said } }, { quick: true });
    playing = "";
    paint(await MIA.worlds(current));  // the story now holds this turn (the book keeps it)
    const again = $("lw-do");
    if (again) { if (!(done && done.status === "executed")) again.value = said; again.focus(); }
  }

  function storyPanel(data, c) {
    const told = c.story || [];
    const me = c.players[0];
    if (c.status !== "active" || !me) return null;
    const turns = told.slice(-12).map((t) => el("div", { class: "lw-turn" },
      el("p", { class: "lw-said" }, el("span", { class: "dim" }, me.name + " · "), t.said),
      t.lines[0] ? el("p", { class: "lw-told" }, t.lines[0]) : null,
      t.lines.length > 1 ? el("div", { class: "lw-chips lw-changed" }, ...t.lines.slice(1).map((line) =>
        el("span", { class: "lw-chip" + (/^Tried/.test(line) ? " missed" : "") }, line))) : null));
    const busy = playing === c.id;
    const log = turns.length ? el("div", { class: "lw-turns", role: "log", "aria-live": "polite" }, ...turns) : null;
    if (log) requestAnimationFrame(() => { log.scrollTop = log.scrollHeight; });  // the latest turn in view
    return el("div", { class: "lw-story" },
      el("p", { class: "pw-label" }, told.length ? "The Story So Far" : "Your First Turn"),
      log ? log
        : el("p", { class: "dim" }, "Say what " + me.name + " does, and MIA tells you what happens."),
      busy ? el("p", { class: "dim lw-thinking", role: "status" }, "MIA is telling what happens…") : null,
      el("div", { class: "lw-do-row" },
        el("input", { id: "lw-do", type: "text", maxlength: "500", placeholder: "I search the cartographer's desk",
          "aria-label": "What does " + me.name + " do?", disabled: busy ? "" : null,
          onkeydown: (e) => { if (e.key === "Enter") play(c); } }),
        el("button", { type: "button", class: "btn btn-primary", onclick: () => play(c), disabled: busy ? "" : null }, "Do It")));
  }

  async function make(kind, title, actionKind, extra) {
    const v = await form(title, forms[kind].fields, {});
    if (v) MIAShell.act({ kind: actionKind, params: { ...(extra || {}), ...v } });
  }

  async function open(id) {
    current = id;
    const url = new URL(location.href);
    url.searchParams.set("campaign", id);
    history.replaceState(null, "", url);
    paint(await MIA.worlds(current));
    const panel = $("lw-campaign");
    if (panel) panel.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function chips(items, cls) {
    return items.length ? el("div", { class: "lw-chips" }, ...items.map((t) => el("span", { class: "lw-chip " + (cls || "") }, t))) : null;
  }

  function characterCard(data) {
    const c = data.character;
    if (!c) return el("section", { class: "glass lw-hero-card lw-empty" },
      el("p", { class: "pw-label" }, "Your Character"),
      el("p", {}, "One self across every world: in each, a version of them with their own story."),
      el("button", { type: "button", class: "btn btn-green", onclick: () => make("character", "Make Your Character", "world.character_add") }, "Make Your Character"));
    return el("section", { class: "glass lw-hero-card" },
      el("div", { class: "lw-sigil", "aria-hidden": "true" }, (c.name || "?").slice(0, 1)),
      el("div", { class: "lw-hero-text" },
        el("p", { class: "pw-label" }, "Your Character"),
        el("h2", { class: "lw-name" }, c.name),
        c.note ? el("p", { class: "lw-note" }, c.note) : null,
        el("p", { class: "dim lw-versions" }, c.versions.length
          ? "In " + c.versions.length + (c.versions.length === 1 ? " world: " : " worlds: ") + c.versions.map((v) => v.name + " in " + v.world).join(" · ")
          : "Not in any world yet. Open a campaign and bring them in.")));
  }

  function worldCard(w) {
    return el("article", { class: "glass lw-world" },
      el("div", { class: "lw-world-head" },
        el("h3", { class: "lw-world-name" }, w.name),
        w.genre ? el("span", { class: "lw-chip" }, w.genre) : null),
      w.premise ? el("p", { class: "lw-premise" }, w.premise) : null,
      w.campaigns.length ? el("div", { class: "lw-runs" }, ...w.campaigns.map((c) => el("button", {
        type: "button", class: "lw-run" + (c.id === current ? " on" : "") + (c.status === "ended" ? " ended" : ""), onclick: () => open(c.id) },
        el("span", { class: "lw-run-name" }, c.name),
        el("span", { class: "dim lw-run-meta" }, c.status_word + (c.open ? " · " + c.open + " open" : "") + (c.last_played ? " · " + day(c.last_played) : ""))))) :
        el("p", { class: "dim" }, "No campaign yet."),
      el("div", { class: "row-buttons" },
        button("Begin a Campaign", () => make("campaign", "A Campaign in " + w.name, "world.campaign_add", { universe_id: w.id }))));
  }

  function player(v) {
    return el("div", { class: "lw-player" },
      el("div", { class: "lw-player-head" },
        el("h4", { class: "lw-player-name" }, v.name),
        v.origin ? el("span", { class: "dim" }, v.origin) : null),
      v.background ? el("p", { class: "lw-note" }, v.background) : null,
      v.attributes.length ? el("div", { class: "lw-stats" }, ...v.attributes.map((a) => el("div", { class: "lw-stat" },
        el("span", { class: "lw-stat-n" }, String(a.value)), el("span", { class: "dim" }, a.name)))) : null,
      v.skills.length ? el("p", { class: "pw-label lw-sub" }, "Skills") : null, chips(v.skills),
      v.inventory.length ? el("p", { class: "pw-label lw-sub" }, "Carrying") : null, chips(v.inventory, "item"));
  }

  function campaignPanel(data) {
    const c = data.campaign;
    if (!c) return null;
    const status = (s) => MIAShell.act({ kind: "world.campaign_status", params: { campaign_id: c.id, status: s } }, { quick: s === "active" });
    const playing = c.players.length > 0;
    return el("section", { class: "glass lw-campaign", id: "lw-campaign" },
      el("div", { class: "lw-campaign-head" },
        el("div", {},
          el("p", { class: "pw-label" }, c.universe.name + (c.universe.genre ? " · " + c.universe.genre : "")),
          el("h2", { class: "lw-campaign-name" }, c.name)),
        el("span", { class: "lw-state " + c.status }, c.status_word)),
      c.summary ? el("p", { class: "lw-premise" }, c.summary) : null,
      storyPanel(data, c),
      el("div", { class: "lw-campaign-cols" },
        el("div", { class: "lw-col" },
          el("p", { class: "pw-label" }, "Who Plays"),
          playing ? el("div", { class: "lw-players" }, ...c.players.map(player))
            : data.character ? button("Bring " + data.character.name + " In", () => make("version", data.character.name + " in " + c.name, "world.version_add", { campaign_id: c.id }), "btn-green")
              : el("p", { class: "dim" }, "Make your character first.")),
        el("div", { class: "lw-col" },
          el("p", { class: "pw-label" }, "Quests"),
          c.quests.length ? el("div", { class: "lw-quests" }, ...c.quests.map((q) => el("div", { class: "lw-quest" + (q.status === "done" ? " done" : "") },
            el("div", {},
              el("p", { class: "lw-quest-name" }, q.name),
              q.objective ? el("p", { class: "dim lw-quest-obj" }, q.objective) : null,
              el("p", { class: "dim lw-quest-by" }, (q.status === "done" ? "Finished " + day(q.done_at) + " · " : "") + "Set by " + q.by)),
            q.status === "open" ? button("Finished", () => MIAShell.act({ kind: "world.quest_done", params: { quest_id: q.id } }, { quick: true })) : null)))
            : el("p", { class: "dim" }, "No quests yet."),
          el("div", { class: "row-buttons" }, button("Set a Quest", () => make("quest", "A Quest in " + c.name, "world.quest_add", { campaign_id: c.id }))))),
      el("p", { class: "dim lw-phase" }, data.phase_note),
      el("div", { class: "row-buttons lw-status" },
        c.status === "active" ? button("Pause", () => status("paused")) : button("Pick It Back Up", () => status("active")),
        c.status !== "ended" ? button("End It", () => status("ended"), "btn-quiet") : null));
  }

  let last = null;
  function paint(data) {
    last = data;
    if (!data.available) {
      $("lw-sub").textContent = "Living Worlds isn't set up on this MIA yet.";
      $("panel").replaceChildren();
      return;
    }
    forms = data.forms;
    if (!current && data.campaign) current = data.campaign.id;
    $("lw-sub").textContent = data.worlds.length
      ? "Your worlds, your campaigns, and who you are in each. Fiction only: nothing here touches real XP."
      : "Make a world, begin a campaign in it, and bring your character in.";
    $("panel").replaceChildren(...[
      characterCard(data),
      campaignPanel(data),
      el("div", { class: "lw-worlds-head" },
        el("p", { class: "pw-label" }, data.worlds.length ? "Your Worlds" : "No Worlds Yet"),
        button("Make a World", () => make("universe", "Make a World", "world.universe_add"), data.worlds.length ? "btn-ghost" : "btn-green")),
      data.worlds.length ? el("section", { class: "lw-worlds" }, ...data.worlds.map(worldCard)) : null,
      el("p", { class: "dim lw-say" }, "Say \"what worlds do I have?\", \"make a world called…\", \"start a campaign in…\", " +
        "\"set a quest: find the lost cartographer\", \"in my campaign I pick the lock\" or \"pause the campaign\" any time."),
    ].filter(Boolean));
  }

  MIAShell.start(async () => { paint(await MIA.worlds(current)); }, { refreshOnChange: true });
})();
