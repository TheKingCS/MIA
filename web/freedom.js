/*
 * freedom.js — the Freedom screen (claude, 2026-10-21, DEC-0038). Renders
 * MIA.freedom() (core/freedom.py): the estimated day and how far along the
 * fund is, progress today / this week / this month, what a shift buys, how
 * the fund adds up (each number with where it came from), what moves the
 * day, the builds, six months of history and the person's own reasons.
 * H-0067: the estimate as a range, the green-week streak, which accounts
 * are the fund, builds in the person's order with the next one marked.
 * Formatting only: every number is the engine's.
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
  const field = (name, label, type, def) => ({ name, label, type, required: false, options: [], default: def ?? null });
  const longDay = (iso) => iso ? new Date(iso + "T00:00:00").toLocaleDateString(undefined, { month: "long", year: "numeric" }) : "";
  const SVG = "http://www.w3.org/2000/svg";

  async function setPlan() {
    const s = page.settings;
    const v = await form("Your Plan", [
      field("monthly_needs", "What a month of living takes (blank: from your spending)", "money", s["freedom.monthly_needs"] || null),
      field("cushion_months", "Cushion: months of the gap to have saved", "int", s["freedom.cushion_months"]),
      field("saved", "Saved so far (until your bank is connected)", "money", s["freedom.saved"] || null),
      field("monthly_saving", "Saved a month (blank: from income minus spending)", "money", s["freedom.monthly_saving"] || null)], {});
    if (v) act({ kind: "freedom.plan", params: v });
  }
  async function addBuild() {
    const v = await form("Add A Build", [field("name", "What (greenhouse, chicken coop, solar, root cellar…)", "text"),
      field("budget", "About what it will cost", "money"), field("description", "Notes", "text")], {});
    if (v) act({ kind: "freedom.build", params: v });
  }
  async function editBuild(b) {
    const v = await form("Edit " + b.name, [field("name", "What", "text", b.name), field("budget", "About what it will cost", "money", b.budget),
      { name: "status", label: "Where it's at", type: "choice", required: true, options: ["Planning", "Active", "On Hold", "Complete"], default: b.status }], {});
    if (v) act({ kind: "freedom.build_edit", params: Object.assign({ project_id: b.id }, v) });
  }

  // The fund as a ring: how much of it is saved.
  function ring(pct) {
    const r = 54, c = 2 * Math.PI * r, p = Math.max(0, Math.min(100, pct || 0));
    const svg = document.createElementNS(SVG, "svg");
    svg.setAttribute("viewBox", "0 0 128 128");
    svg.setAttribute("class", "free-ring");
    svg.setAttribute("aria-hidden", "true");
    const circle = (cls, dash) => {
      const n = document.createElementNS(SVG, "circle");
      n.setAttribute("cx", "64"); n.setAttribute("cy", "64"); n.setAttribute("r", String(r));
      n.setAttribute("class", cls);
      if (dash != null) { n.setAttribute("stroke-dasharray", dash + " " + c); n.setAttribute("transform", "rotate(-90 64 64)"); }
      return n;
    };
    svg.append(circle("track"), circle("fill", (p / 100) * c));
    return svg;
  }

  function hero() {
    const p = page.plan, t = p.text;
    const big = p.ready ? "You're there." : p.days != null ? "~" + p.days.toLocaleString() + " days" : "—";
    const r = page.range || {};
    const sub = p.ready ? "The fund is full. Time to plan the jump."
      : r.earliest ? "Between " + longDay(r.earliest) + " and " + (r.latest ? longDay(r.latest) : "later") +
        " at your pace (" + (t.pace || "") + " a month). An estimate, not a promise."
      : p.why_no_date;
    return el("section", { class: "glass free-hero" },
      el("div", { class: "free-ring-wrap" }, ring(p.progress_pct),
        el("div", { class: "free-ring-label" }, el("strong", {}, p.progress_pct != null ? Math.floor(p.progress_pct) + "%" : "—"), el("span", { class: "dim" }, "of the fund"))),
      el("div", { class: "free-hero-text" },
        el("div", { class: "free-big" }, big),
        el("p", { class: "dim" }, sub),
        el("p", {}, el("strong", {}, t.saved), " saved of ", el("strong", {}, t.goal), p.left ? " · " + t.left + " to go" : ""),
        p.covered_pct != null ? el("div", { class: "free-cover" },
          el("div", { class: "free-cover-bar" }, el("span", { style: "width:" + Math.min(100, p.covered_pct) + "%" })),
          el("span", { class: "dim" }, "The homestead covers " + p.covered_pct + "% of a month")) : null));
  }

  function streakLine() {
    const weeks = page.weeks || [];
    if (!weeks.length) return null;
    const last = weeks[weeks.length - 1];
    const text = page.streak ? page.streak + (page.streak === 1 ? " green week" : " green weeks in a row") +
      ". Keep it going." : last < 0 ? "Last week went red. It happens; this week is a fresh one." : "Last week was flat.";
    return el("div", { class: "free-streak" },
      el("span", { class: "free-weeks", "aria-hidden": "true" }, weeks.map((w) => el("span", { class: w > 0 ? "g" : w < 0 ? "r" : "" }))),
      el("span", { class: "dim" }, text));
  }

  function periodTiles() {
    return el("div", { class: "fact-tiles nw-row" }, page.periods.map((x) =>
      el("div", { class: "glass nw-tile" + (x.total < 0 ? " bad" : "") }, el("span", { class: "dim" }, x.label), el("strong", {}, x.total_text),
        x.homestead ? el("span", { class: "dim free-small" }, "homestead " + x.homestead_text) : null)));
  }

  function shiftCard() {
    const s = page.shift;
    if (!s) return section("Tonight's Shift", el("a", { class: "btn btn-ghost btn-small", href: "dungeon.html" }, "Set Up Your Pay"),
      el("p", { class: "dim" }, "Put your pay and shift length in the Dungeon, and MIA shows what each shift buys you."));
    return el("section", { class: "glass free-shift" },
      el("div", { class: "dim" }, "Tonight's shift · " + s.hours + " hours"),
      el("div", { class: "free-shift-line" }, el("strong", {}, s.pay_text),
        s.days_of_living != null ? [" → ", el("strong", {}, s.days_of_living + " days"), " of living"] : null),
      s.of_goal != null ? el("p", { class: "dim" }, (Math.round(s.of_goal * 1000) / 10) + "% of the fund. Every shift is a step out.") : null,
      el("p", { class: "dim" }, "Pay from " + s.source + (s.take_home ? ", take-home" : ", before taxes") + "."));
  }

  function breakdown() {
    const p = page.plan, t = p.text, src = page.sources;
    const line = (label, value, source, cls) => el("div", { class: "free-line " + (cls || "") },
      el("span", {}, label, source ? el("span", { class: "dim free-src" }, " · " + source) : null), el("strong", {}, value));
    return section("How The Fund Adds Up", btn("Your Plan", "btn-ghost btn-small", setPlan),
      line("A month of living", t.needs || "not set", src.needs),
      line("The homestead earns", t.homestead + " a month", src.homestead || "no sales yet"),
      line("The gap", t.gap + " a month", "", "sum"),
      line("× a cushion of " + page.cushion_months + " months", t.cushion, ""),
      line("+ builds still to pay for", t.builds_left, page.builds.length ? page.builds.length + " builds" : "none yet"),
      line("The freedom fund", t.goal, "", "total"),
      line("Saved so far", t.saved, src.saved || "not set"),
      line("Saved a month", t.pace || "not set", src.pace),
      page.levers.length ? el("div", { class: "free-levers" }, page.levers.map((lv) =>
        el("p", { class: "dim" }, "+" + lv.amount_text + " " + lv.what + " → ", el("strong", {}, lv.days_sooner + " days sooner")))) : null);
  }

  const move = (b, direction) => act({ kind: "freedom.build_move", params: { project_id: b.id, direction } }, { quick: true });
  function buildsSection() {
    const nextId = page.next_build && page.next_build.id;
    return section("The Builds", btn("Add A Build", "btn-amber", addBuild),
      page.builds.length ? el("div", { class: "rows" }, page.builds.map((b, i) => el("div", { class: "row money-row" },
        el("div", { class: "free-build" }, el("div", { class: "row-title" }, b.name, " ", el("span", { class: "chip" }, b.status),
          b.id === nextId ? el("span", { class: "chip chip-ok" }, "Next") : null),
          el("div", { class: "free-cover-bar" }, el("span", { style: "width:" + Math.min(100, b.budget ? (b.spent / b.budget) * 100 : 0) + "%" })),
          el("div", { class: "row-sub" }, b.spent_text + " of " + b.budget_text + " · " + b.left_text + " to go")),
        el("div", { class: "row-buttons" },
          i > 0 ? btn("↑", "btn-ghost btn-small", () => move(b, "up")) : null,
          i < page.builds.length - 1 ? btn("↓", "btn-ghost btn-small", () => move(b, "down")) : null,
          btn("Edit", "btn-ghost btn-small", () => editBuild(b))))))
        : el("p", { class: "empty" }, "Add what you're building toward: the greenhouse, the coop, solar, the root cellar, with about what each costs. Tag spending to a build in Money and it counts down."));
  }

  function accountsSection() {
    const list = page.accounts || [];
    if (!list.length) return null;
    const toggle = (a) => act({ kind: "freedom.fund_account", params: { account_id: a.id, in_fund: !a.in_fund } }, { quick: true });
    return section("Which Accounts Are The Fund", null,
      el("p", { class: "dim" }, page.accounts_picked ? "Only these count toward what you've saved." : "All checking and savings count until you pick."),
      el("ul", { class: "pres-list" }, list.map((a) => el("li", { class: "pres-item" + (a.in_fund ? " progress" : "") },
        el("span", { class: "pres-kind" }, a.in_fund ? "fund" : "not"),
        el("span", { class: "what" }, (a.bank ? a.bank + " · " : "") + a.name + (a.mask ? " ····" + a.mask : ""), el("small", {}, a.balance_text)),
        btn(a.in_fund ? "Leave Out" : "Count It", "btn-ghost btn-small", () => toggle(a))))));
  }

  function historySection() {
    const h = page.history;
    if (!h.some((m) => m.saved || m.homestead)) return null;
    const top = Math.max(1, ...h.map((m) => Math.max(Math.abs(m.saved), Math.abs(m.homestead))));
    return section("The Last Six Months", null,
      el("div", { class: "free-bars" }, h.map((m) => el("div", { class: "free-month", title: m.label + ": saved " + m.saved + ", homestead " + m.homestead },
        el("div", { class: "free-cols" },
          el("span", { class: "col saved" + (m.saved < 0 ? " neg" : ""), style: "height:" + Math.round(Math.abs(m.saved) / top * 100) + "%" }),
          el("span", { class: "col home", style: "height:" + Math.round(Math.abs(m.homestead) / top * 100) + "%" })),
        el("span", { class: "dim" }, m.label)))),
      el("p", { class: "dim free-small" }, "Left bar: saved (income minus spending). Right bar: the homestead's profit."));
  }

  function whySection() {
    if (!page.why.length && !page.wins.length) return section("Remember Why", null,
      el("p", { class: "dim" }, "Tell MIA why you're doing this, in your own words (“the job pays off the debt, paying it off buys my time back”), and it shows here."));
    return section("Remember Why", null,
      page.why.map((chain) => el("ol", { class: "free-why" }, chain.map((link) => el("li", { class: link.done ? "done" : "" },
        el("strong", {}, link.name), link.reason ? el("span", { class: "dim" }, " — " + link.reason) : null)))),
      page.wins.length ? el("p", { class: "dim" }, "Lately: " + page.wins.join(" · ")) : null);
  }

  function draw() {
    $("panel").replaceChildren(...[hero(), periodTiles(), streakLine(), shiftCard(), breakdown(), buildsSection(), accountsSection(),
      historySection(), whySection(),
      !page.bank_connected ? el("p", { class: "dim free-small" }, "Your bank isn't connected yet: the numbers fill in by themselves once it is (Money → Bank). Until then, Your Plan takes your own.") : null]
      .filter(Boolean));
  }

  MIAShell.start(async () => {
    page = await MIA.freedom();
    if (!page.available) {
      $("panel").replaceChildren(el("p", { class: "empty" }, "Freedom is a grown-up's plan."));
      return;
    }
    draw();
  });
})();
