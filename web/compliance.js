/*
 * compliance.js — the Compliance screen (claude, 2026-10-21, DEC-0040).
 * Renders MIA.compliance() (core/web_compliance.py): Overdue, Next 30 Days,
 * Later, To Check and Done. Every change proposes an action
 * (core/obligation_actions.py): add, edit, verify (the only way an
 * obligation becomes verified), where it stands, starters to check.
 * Formatting only.
 */
(function () {
  "use strict";
  const { el, act, form } = MIAShell;
  const $ = (id) => document.getElementById(id);
  let page = null;
  let openId = null;

  const btn = (label, cls, onclick) => el("button", { type: "button", class: "btn " + cls, onclick }, label);
  const buttons = (...list) => el("div", { class: "row-buttons" }, list.filter(Boolean));
  const section = (title, actions, ...body) =>
    el("section", { class: "glass money-section" }, el("div", { class: "sect" }, el("h2", {}, title), actions), ...body);
  const chip = (text, cls) => el("span", { class: "chip " + (cls || "") }, text);
  const day = (iso) => iso ? new Date(iso + "T00:00:00").toLocaleDateString(undefined, { weekday: "short", month: "short", day: "numeric", year: "numeric" }) : "";
  const field = (name, label, type, def, extra) => Object.assign({ name, label, type, required: false, options: [], default: def ?? null }, extra || {});

  async function add() {
    const v = await form("Add An Obligation", page.forms.obligation.fields, {});
    if (v) act({ kind: "obligation.add", params: v });
  }
  async function edit(c) {
    const v = await form("Edit " + c.title, page.forms.obligation.fields, c.values);
    if (v) act({ kind: "obligation.edit", params: Object.assign({ obligation_id: c.id }, v) });
  }
  async function verify(c) {
    const v = await form("Verify: " + c.title, [
      field("source_url", "The official page you checked (link)", "text", c.source_url),
      field("how", "Or: who you asked and what they said", "text"),
      field("verified_on", "When you checked (blank: today)", "date"),
      field("applies", "Does it apply to you?", "choice", "yes", { options: ["yes", "no"], required: true })], {});
    if (v) act({ kind: "obligation.verify", params: Object.assign({ obligation_id: c.id }, v) });
  }
  async function setStatus(c) {
    const v = await form(c.title + ": Where It Stands", [
      field("status", "Status", "choice", c.status === "to verify" ? "applies" : c.status, { options: page.statuses, required: true }),
      field("proof", "Proof (a confirmation number, a receipt)", "text", c.proof)], {});
    if (v) act({ kind: "obligation.status", params: Object.assign({ obligation_id: c.id }, v) });
  }
  async function starters() {
    if (!page.starters.length) { MIAShell.say("Every starter is already on your list."); return; }
    const v = await form("Add Things To Check", page.starters.map((s) =>
      field("s_" + s.id, s.name + " (" + s.jurisdiction + ")", "choice", "no", { options: ["no", "yes"] })), {});
    if (v) act({ kind: "obligation.starters", params: v });
  }

  function when(c) {
    if (!c.due) return "No date yet";
    const d = c.days;
    const rel = d < 0 ? (-d) + " days overdue" : d === 0 ? "due today" : d === 1 ? "due tomorrow" : "in " + d + " days";
    return day(c.due) + " · " + rel;
  }

  function card(c) {
    const open = openId === c.id;
    const head = el("button", { type: "button", class: "craft-head", "aria-expanded": String(open), onclick: () => { openId = open ? null : c.id; draw(); } },
      el("div", {}, el("h3", {}, c.title),
        el("p", { class: "dim" }, [c.authority, c.applies_to, c.period].filter(Boolean).join(" · ")),
        el("p", { class: "ob-when " + c.where }, when(c))),
      el("div", { class: "ob-chips" },
        c.verified ? chip(c.stale ? "Check Again" : "Verified", c.stale ? "chip-soon" : "chip-ok") : chip("To Verify", "chip-soon"),
        c.status !== "to verify" && c.status !== "applies" ? chip(c.status) : null));
    if (!open) return el("article", { class: "glass craft-card ob-card " + c.where }, head);
    const line = (label, value) => value ? el("p", {}, el("span", { class: "dim" }, label + ": "), value) : null;
    return el("article", { class: "glass craft-card ob-card open " + c.where }, head,
      !c.verified ? el("p", { class: "ob-warn" }, "Not verified: check the official source before relying on this date or fee.") : null,
      c.moved.length ? el("p", { class: "dim" }, "Moved to the next business day (" + c.moved.join(" and ") + "): the stated date " + c.stated_due + " falls on a weekend or holiday.") : null,
      c.extended_to ? el("p", { class: "dim" }, "Extended to file until " + day(c.file_on) + ". The money is still due " + day(c.pay_on) + ": an extension to file isn't one to pay.") : null,
      line("File / renew by", c.file_on ? day(c.file_on) : ""), line("Pay by", c.pay_on && c.pay_on !== c.file_on ? day(c.pay_on) : ""),
      line("Fee", c.fee_text), line("Expected to owe", c.estimate_text), line("Documents", c.documents),
      line("Next step", c.next_action), line("Rule", c.rule), line("Repeats", c.recurrence),
      line("Checked", c.verified_on ? day(c.verified_on) : ""), line("Proof", c.proof),
      c.source_url ? el("p", {}, el("a", { href: c.source_url, target: "_blank", rel: "noopener" }, c.source_title || c.source_url)) : null,
      c.notes ? el("p", { class: "dim" }, c.notes) : null,
      buttons(btn(c.verified ? "Check Again" : "Verify", c.verified ? "btn-ghost btn-small" : "btn-amber", () => verify(c)),
        btn("Where It Stands", "btn-green btn-small", () => setStatus(c)), btn("Edit", "btn-ghost btn-small", () => edit(c)),
        btn("Delete", "btn-ghost btn-small", () => act({ kind: "obligation.delete", params: { obligation_id: c.id } }))));
  }

  function group(title, list, empty) {
    if (!list.length && !empty) return null;
    return section(title + (list.length ? " · " + list.length : ""), null,
      list.length ? el("div", { class: "craft-grid" }, list.map(card)) : el("p", { class: "empty" }, empty));
  }

  function draw() {
    const c = page.counts, g = page.groups;
    $("strip").replaceChildren(
      el("div", { class: "cell " + (c.overdue ? "bad" : "ok") }, el("span", { class: "n" }, c.overdue), el("span", { class: "t" }, "Overdue")),
      el("div", { class: "cell " + (c.soon ? "soon" : "ok") }, el("span", { class: "n" }, c.soon), el("span", { class: "t" }, "Next 30 Days")),
      el("div", { class: "cell " + (c.unverified ? "soon" : "ok") }, el("span", { class: "n" }, c.unverified), el("span", { class: "t" }, "To Verify")),
      el("div", { class: "cell ok" }, el("span", { class: "n" }, page.fees_soon_text || "—"), el("span", { class: "t" }, "Fees Soon")));
    $("panel").replaceChildren(...[
      buttons(btn("Add An Obligation", "btn-amber", add), btn("Things To Check", "btn-ghost btn-small", starters)),
      !c.open ? section("Start Here", null, el("p", { class: "empty" },
        "Nothing on the list yet. “Things To Check” offers the usual tax and licence deadlines, each with where to check it; nothing is assumed to apply until you verify it. Or add one from a letter or notice you got.")) : null,
      group("Overdue", g.overdue), group("Next 30 Days", g.soon), group("Later", g.later), group("To Check", g.check), group("Done", g.done),
      el("p", { class: "dim free-small" }, "MIA keeps the list and reminds you (90, 60, 30, 14 and 7 days before, on the day, and weekly when overdue). She never files, pays or signs anything, and a date she hasn't seen verified always says so."),
    ].filter(Boolean));
  }

  MIAShell.start(async () => {
    page = await MIA.compliance();
    if (!page.available) {
      $("panel").replaceChildren(el("p", { class: "empty" }, "Compliance is for a grown-up."));
      return;
    }
    draw();
  });
})();
