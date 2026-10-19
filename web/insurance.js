/*
 * insurance.js — the insurance check-up (claude, 2026-10-19, DEC-0034).
 * Renders MIA.insurance() (core/insurance.py) in tabs: My Policies (each
 * policy, what it costs a year, what's worth a look), Shop It (what an
 * agent asks for, the quote request MIA drafts, the quotes side by side
 * against what you have; a cheaper quote that covers less says so), and
 * Add (read a policy's PDF or photo into the form, or type one in).
 * Every change is an action (core/insurance_actions.py). Formatting only.
 */
(function () {
  "use strict";
  const { el, act, form, say } = MIAShell;
  const $ = (id) => document.getElementById(id);
  const TABS = [["policies", "My Policies"], ["shop", "Shop It"], ["add", "Add"]];
  let page = null;
  let tab = TABS.some(([t]) => t === location.hash.slice(1)) ? location.hash.slice(1) : "policies";

  const btn = (label, cls, onclick) => el("button", { type: "button", class: "btn " + cls, onclick }, label);
  const section = (title, actions, ...body) =>
    el("section", { class: "glass money-section" }, el("div", { class: "sect" }, el("h2", {}, title), actions), ...body);
  // The currency symbol comes from the engine (the person's country).
  const fmt = (n) => (n < 0 ? "-" : "") + ((page && page.summary.currency_symbol) || "$") +
    Math.abs(Number(n || 0)).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  const day = (iso) => iso ? new Date(iso + "T12:00:00").toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" }) : "";
  const extra = () => ({ assets: page.assets, policies: page.policies.map((p) => ({ id: p.id, name: p.name + " · " + p.insurer })) });

  // ------------------------------------------------------------ changes
  async function editPolicy(p, values) {
    const v = await form(p ? "Change " + p.name : "Add A Policy", page.forms.policy.fields,
      p ? Object.fromEntries(page.forms.policy.fields.map((f) => [f.name, p[f.name]])) : (values || {}), extra());
    if (!v) return;
    await act({ kind: p ? "insurance_policy.edit" : "insurance_policy.add", params: p ? Object.assign({ policy_id: p.id }, v) : v });
  }
  async function addQuote(p) {
    const v = await form("A Quote For " + p.name, page.forms.quote.fields,
      { policy_id: p.id, every: p.every, coverage: p.coverage }, extra());
    if (v) await act({ kind: "insurance_quote.add", params: v });
  }

  // Read a policy's PDF (or a photo of its first page) into the Add form.
  function readPolicy() {
    const pick = el("input", { type: "file", accept: "application/pdf,image/*,.txt", hidden: true });
    pick.onchange = async () => {
      const file = pick.files[0];
      pick.remove();
      if (!file) return;
      say("Reading " + file.name + "…");
      try {
        const got = await MIA.upload("/api/insurance/read", file);
        say(got.message);
        await editPolicy(null, got.values);
      } catch (e) { say(e.message); }
    };
    document.body.append(pick);
    pick.click();
  }

  // ------------------------------------------------------------ views
  function checksOf(p) {
    return p.checks.length ? el("ul", { class: "ins-checks" }, p.checks.map((c) => el("li", { class: "ins-check " + c.tone }, c.text))) : null;
  }

  function policyCard(p) {
    const chosen = p.chosen_quote_id && p.compare.quotes.find((q) => q.id === p.chosen_quote_id);
    return el("article", { class: "glass ins-card" },
      el("div", { class: "ins-head" },
        el("div", {}, el("div", { class: "row-title" }, p.icon + " " + p.name),
          el("div", { class: "row-sub" }, [p.insurer, p.covers || null, p.policy_number ? "#" + p.policy_number : null].filter(Boolean).join(" · "))),
        el("div", { class: "ins-cost" }, el("strong", {}, fmt(p.per_year)), el("span", { class: "dim" }, " a year"))),
      el("p", { class: "dim ins-terms" }, [fmt(p.premium) + " every " + p.every.toLowerCase(),
        p.deductible ? fmt(p.deductible) + " deductible" : null, p.renews ? "renews " + day(p.renews) : "no renewal date yet"].filter(Boolean).join(" · ")),
      p.coverage_lines.length ? el("div", { class: "ins-cover" }, p.coverage_lines.map((c) =>
        el("span", { class: "ins-tag" + (c.included ? "" : " off") }, c.name + ": " + c.limit))) : null,
      checksOf(p),
      chosen ? el("p", { class: "ins-switch" }, "Switching to " + chosen.insurer + ".",
        btn("I Switched", "btn-amber btn-small", () => act({ kind: "insurance.switched", params: { quote_id: chosen.id } }))) : null,
      el("div", { class: "row-buttons" },
        btn("Shop It", "btn-ghost btn-small", () => { tab = "shop"; history.replaceState(null, "", "#shop"); draw(); }),
        btn("Change", "btn-ghost btn-small", () => editPolicy(p)),
        btn("Delete", "btn-ghost btn-small", () => act({ kind: "insurance_policy.delete", params: { policy_id: p.id } }))));
  }

  function policies() {
    if (!page.policies.length) return [section("No Policies Yet", null,
      el("p", {}, "Put in your car, home or renters insurance, and MIA keeps the renewal dates, what you pay a year, and what's worth a look."),
      el("div", { class: "row-buttons" }, btn("Read A Policy", "btn-amber", readPolicy), btn("Type One In", "btn-ghost", () => editPolicy(null))))];
    return page.policies.map(policyCard);
  }

  // One card per quote, cheapest honest one first: what it costs a year, what it saves,
  // and line by line where its coverage differs from yours (a phone has no room for a wide table).
  function sideBySide(p) {
    const c = p.compare;
    if (!c.quotes.length) return el("p", { class: "empty" }, "No quotes yet. Draft a request, send it to a few insurers, and put in what they send back.");
    return el("div", { class: "ins-quotes" }, el("p", { class: "dim" }, "Now: " + p.insurer + ", " + fmt(c.per_year) + " a year" +
        (p.deductible ? ", " + fmt(p.deductible) + " deductible" : "") + "."),
      ...c.quotes.map((q) => {
        const differs = c.rows.map((r, i) => ({ name: r.name, now: r.current, theirs: r.quotes[c.quotes.indexOf(q)] }))
          .filter((r) => r.theirs !== r.now && !(r.theirs === "—" && /^(no|none|excluded|declined|—)/i.test(r.now)))
          .map((r) => Object.assign(r, { theirs: r.theirs === "—" ? "not listed" : r.theirs }));
        return el("article", { class: "ins-quote" + (q.id === c.best ? " best" : "") },
          el("div", { class: "ins-head" }, el("div", { class: "row-title" }, (q.id === c.best ? "★ " : "") + q.insurer),
            el("div", { class: "ins-cost" }, el("strong", {}, fmt(q.per_year)), el("span", { class: "dim" }, " a year"))),
          el("p", { class: q.saves > 0 ? "ins-same" : "dim" }, q.saves > 0 ? "Saves " + fmt(q.saves) + " a year" :
            q.saves < 0 ? fmt(-q.saves) + " more a year" : "The same price"),
          q.covers_less.length ? el("p", { class: "ins-less" }, "⚠ Covers less: " + q.covers_less.join("; ")) :
            q.unknown_coverage ? el("p", { class: "dim" }, "Coverage not put in: check it covers the same before you switch.") :
            el("p", { class: "ins-same" }, "✓ Same coverage as now"),
          !q.unknown_coverage && differs.length ? el("ul", { class: "ins-diff" }, differs.map((r) =>
            el("li", {}, r.name + ": " + r.theirs + " (you have " + r.now + ")"))) : null,
          el("div", { class: "row-buttons" },
            q.chosen ? btn("I Switched", "btn-amber btn-small", () => act({ kind: "insurance.switched", params: { quote_id: q.id } }))
              : btn("Switch To This", "btn-ghost btn-small", () => act({ kind: "insurance.choose", params: { quote_id: q.id } })),
            btn("Remove", "btn-ghost btn-small", () => act({ kind: "insurance_quote.delete", params: { quote_id: q.id } }))));
      }));
  }

  function shop() {
    if (!page.policies.length) return policies();
    return page.policies.map((p) => section(p.icon + " " + p.name, el("div", { class: "row-buttons" },
        btn("Draft A Quote Request", "btn-ghost btn-small", () => act({ kind: "insurance.request", params: { policy_id: p.id } })),
        btn("Add A Quote", "btn-amber btn-small", () => addQuote(p))),
      checksOf(p),
      sideBySide(p),
      el("details", { class: "ins-list" }, el("summary", {}, "What an agent will ask for"),
        el("ul", {}, p.checklist.map((line) => el("li", {}, line))))));
  }

  function add() {
    return [section("Read A Policy", null,
        el("p", {}, "Pick the policy's PDF or a photo of its first page (the declarations page). MIA reads the insurer, price, dates, deductible and coverage into the form for you to check."),
        el("div", { class: "row-buttons" }, btn("Read A Policy", "btn-amber", readPolicy))),
      section("Type One In", null, el("p", { class: "dim" }, "Coverage goes one per line, the way your policy says it: “Bodily injury: 100,000/300,000”, “Collision: included”."),
        el("div", { class: "row-buttons" }, btn("Add A Policy", "btn-ghost", () => editPolicy(null)))),
      el("p", { class: "dim" }, "MIA compares what you get; she never shops for you or fills in an insurer's website, and she isn't a licensed agent. You decide.")];
  }

  const VIEWS = { policies, shop, add };

  function draw() {
    const s = page.summary;
    $("strip").replaceChildren(
      el("div", { class: "cell ok" }, el("span", { class: "n" }, s.policies), el("span", { class: "t" }, "Policies")),
      el("div", { class: "cell ok" }, el("span", { class: "n" }, fmt(s.per_year)), el("span", { class: "t" }, "A Year")),
      el("div", { class: "cell " + (s.renewing_soon ? "soon" : "ok") }, el("span", { class: "n" }, s.renewing_soon), el("span", { class: "t" }, "Renewing Soon")),
      el("div", { class: "cell ok" }, el("span", { class: "n" }, fmt(s.could_save)), el("span", { class: "t" }, "Could Save")));
    $("tabs").hidden = false;
    $("tabs").replaceChildren(...TABS.map(([id, l]) => el("button", { type: "button", role: "tab", "aria-selected": String(id === tab),
      onclick: () => { tab = id; history.replaceState(null, "", "#" + id); draw(); } }, l)));
    $("panel").replaceChildren(...[].concat(VIEWS[tab]()));
  }

  MIAShell.start(async () => {
    page = await MIA.insurance();
    if (!page.available) { $("panel").replaceChildren(el("p", { class: "empty" }, "Insurance isn't set up on this MIA.")); return; }
    draw();
  });
})();
