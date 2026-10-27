/*
 * dungeon.js — The Dungeon (claude, 2026-10-27, DEC-0046). Renders
 * MIA.dungeon() (core/web_dungeon.py) in tabs: Today (clear today's run and
 * say what made it hard mode, the overtime line, planned runs, make a hard
 * day a quest), Loot (this week earned and projected, the month, the year at
 * this pace, banked paychecks, the next dungeon), Record (the hard-mode
 * record with its dates, recent runs) and Setup (the job and its pay).
 * Every change is an action (core/dungeon_actions.py). Formatting only.
 */
(function () {
  "use strict";
  const { el, act, form, say } = MIAShell;
  const $ = (id) => document.getElementById(id);
  const TABS = [["today", "Today"], ["loop", "Loop"], ["loot", "Loot"], ["record", "Record"], ["setup", "Setup"]];
  let page = null;
  let tab = TABS.some(([t]) => t === location.hash.slice(1)) ? location.hash.slice(1) : "today";
  const picked = new Set();  // today's hard-mode modifiers, before the run is cleared
  let calledIn = false;

  const btn = (label, cls, onclick) => el("button", { type: "button", class: "btn " + cls, onclick }, label);
  const buttons = (...list) => el("div", { class: "row-buttons" }, list.filter(Boolean));
  const section = (title, actions, ...body) =>
    el("section", { class: "glass money-section" }, el("div", { class: "sect" }, el("h2", {}, title), actions), ...body);
  const tiles = (...list) => el("div", { class: "craft-tiles" }, list.filter(Boolean).map(([label, value, cls]) =>
    el("div", { class: "craft-tile " + (cls || "") }, el("span", { class: "dim" }, label), el("strong", {}, value))));
  const chip = (text, cls) => el("span", { class: "chip " + (cls || "") }, text);
  const day = (iso) => iso ? new Date(iso + "T00:00:00").toLocaleDateString(undefined, { weekday: "short", month: "short", day: "numeric" }) : "";
  const field = (name, label, type, def, required, options) => ({ name, label, type, required: !!required, options: options || [], default: def ?? null });
  const bar = (pct) => el("div", { class: "bar", role: "progressbar", "aria-valuenow": String(pct), "aria-valuemin": "0", "aria-valuemax": "100" },
    el("div", { class: "bar-fill", style: "width:" + Math.max(0, Math.min(100, pct)) + "%" }));
  const go = (id) => { tab = id; history.replaceState(null, "", "#" + id); draw(); };

  // ------------------------------------------------------------ changes
  async function setUp(d) {
    const v = await form(d ? "Change " + d.name : "Set Up Your Dungeon", page.forms.dungeon.fields, d ? d.values : {}, page.picks);
    if (v) act({ kind: d ? "dungeon.edit" : "dungeon.add", params: d ? Object.assign({ dungeon_id: d.id }, v) : v });
  }
  async function planRun(d) {
    const v = await form("Plan A Run", [field("date", "Which day", "date", null, true),
      field("hours", "Hours (blank: a usual shift, " + d.values.shift_hours + ")", "amount"),
      field("overtime", "A called-in overtime shift?", "choice", "no", false, ["no", "yes"])], {});
    if (v) act({ kind: "dungeon.plan", params: Object.assign({ dungeon_id: d.id }, v) });
  }
  async function clearPast(d, r) {
    const v = await form("Clear The Run On " + day(r.date), [field("hours", "Hours worked", "amount", r.hours, true)], {});
    if (v) act({ kind: "dungeon.run", params: { dungeon_id: d.id, date: r.date, hours: v.hours } });
  }
  const remove = (r) => act({ kind: "dungeon.run_delete", params: { run_id: r.id } });
  const quest = (affix) => act({ kind: "dungeon.quest", params: { challenge: affix.id || affix.name } });

  function clearToday(d, hoursInput, noteInput) {
    act({ kind: "dungeon.run", params: { dungeon_id: d.id, hours: hoursInput.value, hard_mode: [...picked].join(","),
      overtime: calledIn ? "yes" : "", note: noteInput.value } }).then((done) => { if (done) { picked.clear(); calledIn = false; } });
  }

  // ------------------------------------------------------------ views
  function runLine(d, r, extra) {
    return el("li", { class: "dg-run" + (r.boss ? " boss" : "") + (r.affixes.length ? " hard" : "") },
      el("div", {}, el("div", { class: "row-title" }, (r.boss ? "⚔ Boss · " : "") + day(r.date) + " · " + r.hours + " h"),
        el("div", { class: "row-sub" }, [r.loot_text && r.loot_text + " loot", r.bonus_text && r.bonus_text + " boss bonus",
          r.status === "cleared" ? "+" + r.xp + " XP" : null, r.note].filter(Boolean).join(" · ")),
        r.affixes.length ? el("div", { class: "dg-affixes" }, r.affixes.map((a) => chip(a.name, "chip-soon"))) : null),
      extra || null);
  }

  function enter(d) {
    const t = d.today;
    if (t && t.status === "cleared") {
      return section("Run Cleared", null, el("ul", { class: "dg-runs" }, runLine(d, t)),
        t.affixes.length ? el("p", { class: "dim" }, "Cleared on hard mode. Want it as a quest too?") : null,
        t.affixes.length ? buttons(...t.affixes.map((a) => btn("Make " + a.name + " A Quest", "btn-ghost btn-small", () => quest(a)))) : null);
    }
    const hours = el("input", { type: "number", step: "any", min: "0", inputmode: "decimal", id: "dg-hours",
      value: String(t ? t.hours : d.values.shift_hours || 8) });
    const note = el("input", { type: "text", id: "dg-note", placeholder: "Anything to remember (optional)" });
    const chips = page.affixes.map((a) => {
      const b = el("button", { type: "button", class: "chip-button dg-affix", "aria-pressed": String(picked.has(a.id)), title: a.line,
        onclick: () => { picked.has(a.id) ? picked.delete(a.id) : picked.add(a.id); b.setAttribute("aria-pressed", String(picked.has(a.id))); lines(); } },
        a.name);
      return b;
    });
    const boss = el("button", { type: "button", class: "chip-button dg-affix", "aria-pressed": String(calledIn),
      onclick: () => { calledIn = !calledIn; boss.setAttribute("aria-pressed", String(calledIn)); } }, "⚔ Called-in overtime");
    const gm = el("div", { class: "dg-gm", "aria-live": "polite" });
    function lines() {
      const on = page.affixes.filter((a) => picked.has(a.id));
      gm.replaceChildren(...on.map((a) => el("p", {}, el("strong", {}, a.name + " (" + a.real + "): "), a.line, el("span", { class: "dim" }, " +" + a.xp + " XP"))),
        on.length ? buttons(...on.map((a) => btn("Make " + a.name + " A Quest", "btn-ghost btn-small", () => quest(a)))) : "");
    }
    lines();
    return section(t ? "Today's Planned Run" : "Enter The Dungeon", null,
      el("label", { class: "form-row", for: "dg-hours" }, el("span", {}, "Hours"), hours),
      el("p", { class: "dim" }, "Hard mode today? Tap what made it hard: MIA keeps the dates, and it's worth more XP."),
      el("div", { class: "dg-affixes" }, ...chips), gm,
      el("div", { class: "dg-affixes dg-overtime" }, boss),
      el("label", { class: "form-row", for: "dg-note" }, el("span", {}, "Note (optional)"), note),
      buttons(btn("Clear The Run", "btn-amber", () => clearToday(d, hours, note))));
  }

  function overtimeLine(d) {
    const o = d.overtime_now;
    if (!d.set_up || !o.hour_text) return null;
    return el("p", { class: "dg-ot" }, o.in_overtime ? "⚔ You're in overtime this week: every hour is boss loot, " + o.hour_text + " an hour."
      : o.hours_to_overtime + " h until overtime this week. Past that, every hour is boss loot at " + o.hour_text + ".");
  }

  function today() {
    if (!page.dungeons.length) {
      return [section("No Dungeon Yet", null,
        el("p", {}, "Put in your job and its pay. Every shift becomes a run you clear: the loot it earns, overtime as boss fights, and what made the day hard mode."),
        buttons(btn("Set Up Your Dungeon", "btn-amber", () => setUp(null))))];
    }
    return page.dungeons.map((d) => el("div", { class: "dg-dungeon" },
      page.dungeons.length > 1 ? el("h2", { class: "dg-name" }, d.name) : null,
      !d.set_up ? el("p", { class: "dim" }, "Put in the pay an hour (Setup) to see the loot.") : null,
      enter(d), overtimeLine(d),
      d.waiting.length ? section("Did These Happen?", null, el("p", { class: "dim" }, "Planned runs from past days. Clear the ones you worked; remove the rest, nothing's lost."),
        el("ul", { class: "dg-runs" }, d.waiting.map((r) => runLine(d, r, buttons(btn("Clear It", "btn-green btn-small", () => clearPast(d, r)),
          btn("Remove", "btn-ghost btn-small", () => remove(r))))))) : null,
      section("Coming Up", buttons(btn("Plan A Run", "btn-ghost btn-small", () => planRun(d))),
        d.planned.length ? el("ul", { class: "dg-runs" }, d.planned.map((r) => runLine(d, r, buttons(btn("Remove", "btn-ghost btn-small", () => remove(r))))))
          : el("p", { class: "empty" }, "Nothing planned. Put your shifts in to see the week's projected loot."))));
  }

  function loot() {
    if (!page.dungeons.length) return today();
    const out = page.dungeons.map((d) => {
      const w = d.week, m = d.month, p = d.pace, b = d.banked;
      return el("div", { class: "dg-dungeon" },
        page.dungeons.length > 1 ? el("h2", { class: "dg-name" }, d.name) : null,
        section("This Week", el("span", { class: "dim" }, day(w.start) + " – " + day(w.end)),
          tiles(["Earned", w.earned_text], ["Projected", w.projected_text, "ok"], ["Hours", w.hours + " h"],
            w.bonus_text || w.projected_bonus_text ? ["Boss Bonus", w.bonus_text || w.projected_bonus_text, "soon"] : null,
            w.projected_net_text ? ["Take-Home (Est.)", w.projected_net_text] : null),
          overtimeLine(d),
          d.overtime_now.boss_shift_text ? el("p", { class: "dim" }, "One more " + d.overtime_now.boss_shift_hours + "-hour run this week: " + d.overtime_now.boss_shift_text + ".") : null),
        section("This Month", null, tiles(["Earned", m.earned_text], ["Projected", m.projected_text, "ok"],
          m.projected_net_text ? ["Take-Home (Est.)", m.projected_net_text] : null)),
        section("At This Pace", null, p.weeks ? tiles(["A Week", p.weekly_text], ["A Year", p.yearly_text, "ok"],
          p.yearly_net_text ? ["A Year, Take-Home", p.yearly_net_text] : null)
          : el("p", { class: "empty" }, "Clear a few weeks of runs and the pace shows here."),
          p.weeks ? el("p", { class: "dim" }, "From the last " + p.weeks + " week" + (p.weeks === 1 ? "" : "s") + " worked, before taxes.") : null),
        section("Banked", null,
          b.latest ? tiles(["This Month", b.month_text], ["Last 30 Days", b.last_30_text],
            b.share_pct != null ? ["Reaches The Bank", b.share_pct + "%"] : null) : null,
          b.latest ? el("p", { class: "dim" }, "Latest: " + b.latest.amount_text + " on " + day(b.latest.date) + (b.latest.from_bank ? " (from the bank)" : "") +
            ". Counting " + b.matching + "." + (b.share_source ? " The take-home share is from " + b.share_source + "." : ""))
            : el("p", { class: "empty" }, "No paychecks found yet (" + b.matching + "). Connect the bank under Money, or put in the words the paycheck shows (Setup).")));
    });
    const n = page.next_dungeon;
    if (n) {
      out.push(section("The Next Dungeon", el("a", { class: "btn btn-ghost btn-small", href: "freedom.html" }, "Freedom"),
        n.ready ? [el("p", {}, n.unlocked ? "Unlocked: the Freedom plan is reached." : n.progress_pct + "% unlocked · " + n.left_text + " to go of " + n.goal_text),
          bar(n.progress_pct),
          n.run_text ? el("p", { class: "dim" }, "One usual run moves it " + n.run_text + " (" + n.run_basis + ")" +
            (n.runs_left ? ": about " + n.runs_left + " more runs of loot." : ".")) : null,
          n.earliest ? el("p", { class: "dim" }, "At your saving pace: " + day(n.earliest) + (n.latest ? " to " + day(n.latest) : "") + ".") : null]
          : el("p", { class: "dim" }, n.line)));
    }
    return out;
  }

  function record() {
    if (!page.dungeons.length) return today();
    return page.dungeons.map((d) => el("div", { class: "dg-dungeon" },
      section("Hard-Mode Record", d.hard_mode.length ? btn("Copy The Dates", "btn-ghost btn-small", () => copy(d)) : null,
        d.hard_mode.length ? el("ul", { class: "dg-record" }, d.hard_mode.map((x) => el("li", {},
          el("div", { class: "row-title" }, x.name + " · " + x.real),
          el("div", { class: "row-sub" }, x.this_month + " this month · " + x.dates.map(day).join(", ")))))
          : el("p", { class: "empty" }, "No hard-mode runs in the last two months."),
        el("p", { class: "dim" }, "Plain dates, no names: if you ever raise it at work, this is the pattern.")),
      section("Recent Runs", null, d.runs.length ? el("ul", { class: "dg-runs" }, d.runs.map((r) =>
        runLine(d, r, buttons(btn("Take Back", "btn-ghost btn-small", () => remove(r))))))
        : el("p", { class: "empty" }, "No runs cleared yet."))));
  }

  function copy(d) {
    const text = d.hard_mode.map((x) => x.real.charAt(0).toUpperCase() + x.real.slice(1) + ": " + x.dates.join(", ")).join("\n");
    (navigator.clipboard ? navigator.clipboard.writeText(text) : Promise.reject()).then(() => say("Dates copied."), () => say(text));
  }

  function setup() {
    return [...page.dungeons.map((d) => section(d.name, buttons(btn("Change", "btn-ghost btn-small", () => setUp(d)),
        btn("Delete", "btn-ghost btn-small", () => act({ kind: "dungeon.delete", params: { dungeon_id: d.id } }))),
      tiles(["Pay An Hour", d.rates.hourly_text || "—"], ["Overtime", d.rates.overtime_text ? d.rates.overtime_text + " after " + d.rates.after + " h" : "—"],
        ["Pay Week Starts", d.rates.week_starts], ["Paycheck Says", d.values.payer || "—"]))),
      buttons(btn(page.dungeons.length ? "Add Another Dungeon" : "Set Up Your Dungeon", page.dungeons.length ? "btn-ghost" : "btn-amber", () => setUp(null))),
      el("p", { class: "dim" }, "Loot is pay before taxes, worked out from your hours. What reaches the bank comes from the bank sync, never a guess.")];
  }

  // ------------------------------------------------------------ the loop (DEC-0047, core/the_loop.py)
  const MARK = { cleared: "✓", missed: "✗", today: "●", planned: "○", off: "" };
  const SAID = { cleared: "Cleared", missed: "Missed", today: "Today", planned: "Planned", off: "Off" };
  const source = (s) => s === "yours" ? "yours" : s === "learned" ? "learned" : "not known yet";

  async function editRhythm(r) {
    const v = await form(r.name, [field("days", "Days (mon-fri, sun-thu, every day…)", "text", r.days_text, false),
      field("start", "Starts (like 9:30 pm)", "text", r.start_text), field("end", "Ends (like 6 am; blank: none)", "text", r.end_text),
      field("lead_minutes", "Remind this many minutes before", "int", r.lead_minutes),
      field("remind", "Remind me?", "choice", r.remind ? "yes" : "no", false, ["yes", "no"])], {});
    if (!v) return;
    if (v.days === r.days_text) delete v.days;  // unchanged: keep it learned
    if (v.start === r.start_text) delete v.start;
    if (v.end === r.end_text) delete v.end;
    act({ kind: "loop.set", params: Object.assign({ rhythm_id: r.id }, v) });
  }
  async function addRhythm() {
    const v = await form("Something Else That Recurs", [field("name", "What (a walk, the gym, feeding the animals…)", "text", null, true),
      field("days", "Days (mon-fri, every day…)", "text", null, true), field("start", "Starts (like 7 pm)", "text", null, true),
      field("end", "Ends (optional)", "text")], {});
    if (v) act({ kind: "loop.set", params: v });
  }

  function loop() {
    const L = page.loop;
    if (!L || !L.available) return [el("p", { class: "empty" }, "The loop isn't set up on this MIA.")];
    const w = L.week;
    const grid = el("div", { class: "dg-week", role: "table", "aria-label": "This week's loop" },
      el("div", { class: "dg-week-row head", role: "row" }, el("span", { role: "columnheader" }, ""),
        ...w.days.map((d) => el("span", { role: "columnheader", class: d.today ? "now" : "" }, d.label))),
      ...w.rows.map((row) => el("div", { class: "dg-week-row", role: "row" },
        el("span", { role: "rowheader", class: "dg-week-name" }, row.icon + " " + row.name),
        ...row.cells.map((c) => el("span", { role: "cell", class: "dg-cell " + c.status, title: SAID[c.status] + (c.text ? " · " + c.text : ""),
          "aria-label": c.date + ": " + SAID[c.status] + (c.text ? ", " + c.text : "") }, MARK[c.status],
          c.text && row.kind !== "work" ? el("small", {}, c.text) : null)))));
    const scores = w.rows.filter((r) => r.scheduled).map((r) => el("p", { class: "dim" }, r.icon + " " + r.name + ": " +
      (r.so_far ? r.cleared + " of " + r.so_far + " cleared so far (" + r.pct + "%)" : "the week's just starting") +
      (r.to_go ? ", " + r.to_go + " to go" : "") + (r.missed ? ". " + r.missed + " missed" + (r.kind === "work" ? ": nothing earned " + (r.missed === 1 ? "that day" : "those days") : "") + "." : ".")));
    return [section("This Week's Loop", el("a", { class: "btn btn-ghost btn-small", href: "checkin.html" }, "Sunday Check-In"), w.rows.length ? grid : el("p", { class: "empty" }, "Nothing recurring yet."), ...scores),
      section("When Things Happen", buttons(btn("Add Something", "btn-ghost btn-small", addRhythm)),
        el("p", { class: "dim" }, "MIA learns the days and times from what you actually do. What you set is yours; she never overwrites it."),
        el("ul", { class: "dg-runs" }, L.rhythms.map((r) => el("li", { class: "dg-run dg-rhythm" },
          el("div", {}, el("div", { class: "row-title" }, r.icon + " " + r.name),
            el("div", { class: "row-sub" }, r.line + (r.paid_hours != null ? " · " + r.paid_hours + " h paid" +
              (r.break_minutes ? " (" + r.break_minutes + "-min break)" : "") : r.hours ? " · " + r.hours + " h" : "")),
            el("div", { class: "row-sub dim" }, "Days " + source(r.days_source) + " · times " + source(r.start_source) +
              (r.learned_from ? " (from " + r.learned_from + " times)" : "") + " · " +
              (r.remind && r.start ? "reminder " + r.lead_minutes + " min before" : "no reminder"))),
          buttons(btn("Change", "btn-ghost btn-small", () => editRhythm(r)),
            r.start_source === "yours" ? btn("Learn Again", "btn-ghost btn-small", () => act({ kind: "loop.forget", params: { rhythm_id: r.id, what: "times" } })) : null,
            r.kind === "custom" ? btn("Remove", "btn-ghost btn-small", () => act({ kind: "loop.delete", params: { rhythm_id: r.id } })) : null)))))];
  }

  const VIEWS = { today, loop, loot, record, setup };

  function draw() {
    const s = page.summary;
    $("strip").replaceChildren(
      el("div", { class: "cell ok" }, el("span", { class: "n" }, s.week_text), el("span", { class: "t" }, "This Week")),
      el("div", { class: "cell ok" }, el("span", { class: "n" }, s.projected_text), el("span", { class: "t" }, "Projected")),
      el("div", { class: "cell ok" }, el("span", { class: "n" }, s.banked_text), el("span", { class: "t" }, "Banked")),
      el("div", { class: "cell " + (s.hard_this_month ? "soon" : "ok") }, el("span", { class: "n" }, s.hard_this_month), el("span", { class: "t" }, "Hard Mode")));
    $("tabs").hidden = false;
    $("tabs").replaceChildren(...TABS.map(([id, l]) => el("button", { type: "button", role: "tab", "aria-selected": String(id === tab),
      onclick: () => go(id) }, l)));
    $("panel").replaceChildren(...[].concat(VIEWS[tab]()).filter(Boolean));
  }

  MIAShell.start(async () => {
    page = await MIA.dungeon();
    if (!page.available) { $("panel").replaceChildren(el("p", { class: "empty" }, "The Dungeon is for grown-ups.")); return; }
    draw();
  });
})();
