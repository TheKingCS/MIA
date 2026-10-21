/*
 * flock.js — the Chickens screen (claude, 2026-10-21, DEC-0037). Renders
 * MIA.flock() (core/web_flock.py): per flock, eggs today and this week, the
 * lay rate, loose eggs, feed cost per dozen, two weeks of eggs, cartons on
 * hand and the log. Log Eggs is one tap per count (the tap is the approval;
 * Undo in the message); everything else proposes an action
 * (core/flock_actions.py). Formatting only.
 */
(function () {
  "use strict";
  const { el, act, form } = MIAShell;
  const $ = (id) => document.getElementById(id);
  let page = null;

  const btn = (label, cls, onclick) => el("button", { type: "button", class: "btn " + cls, onclick }, label);
  const buttons = (...list) => el("div", { class: "row-buttons" }, list.filter(Boolean));
  const section = (title, actions, ...body) =>
    el("section", { class: "glass money-section" }, el("div", { class: "sect" }, el("h2", {}, title), actions), ...body);
  const tiles = (...list) => el("div", { class: "craft-tiles" }, list.filter(Boolean).map(([label, value, cls]) =>
    el("div", { class: "craft-tile " + (cls || "") }, el("span", { class: "dim" }, label), el("strong", {}, value))));
  const chip = (text, cls) => el("span", { class: "chip " + (cls || "") }, text);
  const day = (iso) => iso ? new Date(iso + "T00:00:00").toLocaleDateString(undefined, { month: "short", day: "numeric" }) : "";
  const field = (name, label, type, def, required) => ({ name, label, type, required: !!required, options: [], default: def ?? null });
  const FRESH = { fresh: ["Fresh", "chip-ok"], "sell first": ["Sell First", "chip-soon"], past: ["Past Sell-By", "chip-bad"], keeps: ["Keeps", ""] };

  async function addFlock() {
    const v = await form("Add A Flock", page.forms.flock.fields, {}, page.picks);
    if (v) act({ kind: "flock.add", params: v });
  }
  async function editFlock(f) {
    const v = await form("Edit " + f.name, page.forms.flock.fields, f.values, page.picks);
    if (v) act({ kind: "flock.edit", params: Object.assign({ flock_id: f.id }, v) });
  }
  const logEggs = (f, n) => act({ kind: "flock.eggs", params: { flock_id: f.id, count: n } }, { quick: true });
  async function otherCount(f) {
    const v = await form("Eggs From " + f.name, [field("count", "How many eggs", "int", null, true),
      field("date", "Which day (blank: today)", "date")], {});
    if (v) act({ kind: "flock.eggs", params: Object.assign({ flock_id: f.id }, v) });
  }
  async function feed(f) {
    const v = await form("Bought Feed", [field("pounds", "Pounds", "amount"), field("cost", "What it cost", "money"),
      field("date", "Which day (blank: today)", "date")], {});
    if (v) act({ kind: "flock.feed", params: Object.assign({ flock_id: f.id }, v) });
  }
  async function birds(f) {
    const v = await form("Hens Came Or Went", [field("change", "How many (e.g. 3 added, -1 lost)", "number", null, true),
      field("why", "Why (new pullets, a hawk…)", "text")], {});
    if (v) act({ kind: "flock.birds", params: Object.assign({ flock_id: f.id }, v) });
  }
  async function useEggs(f, use) {
    const loose = f.figures.loose;
    const title = { carton: "Into Cartons", baking: "For Baking", home: "Eaten At Home" }[use];
    const fields = [field("eggs", "How many eggs (" + loose + " loose)", "int", use === "carton" ? Math.floor(loose / 12) * 12 || loose : null, true)];
    if (use === "carton" && !f.good) {
      MIAShell.say("Pick the good the cartons go into first: Edit the flock (add an “Eggs” recipe under Workshop → Recipes, makes 1 dozen).");
      return;
    }
    const v = await form(title, fields, {});
    if (v) act({ kind: "flock.use", params: Object.assign({ flock_id: f.id, use }, v) });
  }

  // Two weeks of eggs, as bars (formatting only; the numbers are the engine's).
  function bars(series) {
    const top = Math.max(1, ...series.map((d) => d.eggs));
    return el("div", { class: "egg-bars", role: "img", "aria-label": "Eggs a day, last two weeks: " + series.map((d) => d.eggs).join(", ") },
      series.map((d) => el("div", { class: "egg-bar", title: day(d.date) + ": " + d.eggs },
        el("span", { class: "fill", style: "height:" + Math.round((d.eggs / top) * 100) + "%" }),
        el("span", { class: "lbl" }, new Date(d.date + "T00:00:00").toLocaleDateString(undefined, { weekday: "narrow" })))));
  }

  function flockCard(f) {
    const x = f.figures;
    const good = f.good;
    return el("article", { class: "glass craft-card open" },
      el("div", { class: "craft-head static" },
        el("div", {}, el("h3", {}, f.name), el("p", { class: "dim" }, [f.hens + " hens", f.roosters ? f.roosters + " roosters" : null, f.breed,
          f.started ? "since " + day(f.started) : null].filter(Boolean).join(" · "))),
        buttons(btn("Edit", "btn-ghost btn-small", () => editFlock(f)))),
      tiles(["Today", String(x.today)], ["This Week", String(x.week)], x.lay_rate_text ? ["Lay Rate", x.lay_rate_text] : null,
        ["Loose", String(x.loose)], x.feed_per_dozen_text ? ["Feed / Dozen", x.feed_per_dozen_text] : null),
      el("h4", {}, "Collected"),
      el("div", { class: "egg-taps" }, [1, 2, 3, 4, 5, 6, 8, 10, 12].map((n) => btn("+" + n, "btn-green btn-small", () => logEggs(f, n))),
        btn("Other…", "btn-ghost btn-small", () => otherCount(f))),
      bars(f.series),
      el("h4", {}, "Where They Go"),
      buttons(btn("Into Cartons", "btn-amber", () => useEggs(f, "carton")), btn("For Baking", "btn-ghost btn-small", () => useEggs(f, "baking")),
        btn("Eaten At Home", "btn-ghost btn-small", () => useEggs(f, "home"))),
      good ? el("p", { class: "dim" }, good.name + ": " + good.on_hand_text + " on hand" + (good.price_text ? " · " + good.price_text + " each" : ""),
        good.oldest ? " · oldest " + day(good.oldest_made) + " " : null, good.oldest ? chip(...FRESH[good.oldest.state]) : null)
        : el("p", { class: "dim" }, "Cartons go into a good you sell: add “Eggs” under Workshop → Recipes (makes 1 dozen, the price, how many days they keep), then Edit this flock."),
      el("h4", {}, "Feed And Birds"),
      buttons(btn("Bought Feed", "btn-ghost btn-small", () => feed(f)), btn("Hens Came Or Went", "btn-ghost btn-small", () => birds(f))),
      x.feed_month_text ? el("p", { class: "dim" }, "Feed in the last 30 days: " + x.feed_month_text) : null,
      f.log.length ? [el("h4", {}, "Log"), el("div", { class: "rows" }, f.log.map((e) => el("div", { class: "row money-row" },
        el("div", {}, el("div", { class: "row-title" }, e.text), el("div", { class: "row-sub" }, day(e.date) + (e.note ? " · " + e.note : ""))),
        btn("Take Back", "btn-ghost btn-small", () => act({ kind: "flock.entry_delete", params: { entry_id: e.id } })))))] : null,
      f.notes ? el("p", { class: "dim" }, f.notes) : null);
  }

  function draw() {
    const t = page.total;
    $("strip").replaceChildren(
      el("div", { class: "cell ok" }, el("span", { class: "n" }, t.hens), el("span", { class: "t" }, "Hens")),
      el("div", { class: "cell ok" }, el("span", { class: "n" }, t.today), el("span", { class: "t" }, "Eggs Today")),
      el("div", { class: "cell ok" }, el("span", { class: "n" }, t.week), el("span", { class: "t" }, "This Week")),
      el("div", { class: "cell " + (t.loose >= 12 ? "soon" : "ok") }, el("span", { class: "n" }, t.loose), el("span", { class: "t" }, "Loose Eggs")));
    $("panel").replaceChildren(...(page.flocks.length ? page.flocks.map(flockCard)
      : [section("Your Flock", null, el("p", { class: "empty" }, "Add your flock: how many hens, the breed, when they came. Then log eggs with one tap a day."))]),
      buttons(btn("Add A Flock", "btn-amber", addFlock)));
  }

  MIAShell.start(async () => {
    page = await MIA.flock();
    if (!page.available) {
      $("panel").replaceChildren(el("p", { class: "empty" }, "Chickens aren't set up on this MIA."));
      return;
    }
    draw();
  });
})();
