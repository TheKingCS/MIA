/*
 * why.js — My Why (claude, 2026-11-07; DEC-0125: the why chain was voice-only).
 * Renders MIA.why() (core/web_why.py): each chain of reasons as links from what
 * you do up to what it's all for, the reason in your own words, the facts behind
 * each from your records, done links marked; then what changed and recent wins.
 * Link Two Goals / Unlink / Achieved are why.* actions, as "the reason I work at
 * the factory is to pay off debt" does by voice. Formatting only.
 */
(function () {
  "use strict";
  const { el, act, form } = MIAShell;
  const $ = (id) => document.getElementById(id);
  let page = null;

  async function link(goal) {
    const v = await form(goal ? "What " + goal.name + " Is For" : "Link Two Goals", [
      ...(goal ? [] : [{ name: "goal", label: "What you're doing", type: "text", required: true }]),
      { name: "serves", label: "What it's for", type: "text", required: true },
      { name: "reason", label: "Why, in your words (optional)", type: "textarea" }], {});
    if (v) act({ kind: "why.link", params: Object.assign(goal ? { goal_id: goal.id } : {}, v) });
  }

  function linkCard(l, i, chain) {
    const goal = page.goals.find((g) => g.id === l.id) || {};
    const last = i === chain.length - 1;
    return el("li", { class: "why-link" + (l.done ? " done" : "") },
      el("div", { class: "why-name" }, el("span", {}, l.name), l.done ? el("span", { class: "chip chip-ok" }, "Done") : null),
      l.reason ? el("p", { class: "why-reason" }, "“" + l.reason + "”") : null,
      l.done && l.done_because ? el("p", { class: "dim" }, "Done: " + l.done_because + ".") : null,
      l.evidence.length ? el("ul", { class: "why-facts" }, l.evidence.map((f) => el("li", {}, f))) : null,
      el("div", { class: "row-buttons" },
        last ? el("button", { type: "button", class: "btn btn-ghost btn-small", onclick: () => link(l) }, "What It's For") : null,
        goal.serves ? el("button", { type: "button", class: "btn btn-ghost btn-small", onclick: () => act({ kind: "why.unlink", params: { goal_id: l.id } }) }, "Unlink") : null,
        !l.done ? el("button", { type: "button", class: "btn btn-ghost btn-small", onclick: () => act({ kind: "why.achieve", params: { goal_id: l.id } }) }, "Achieved") : null));
  }

  function draw() {
    $("why-sub").textContent = page.chains.length ? "Your reasons, in your words." : "Nothing here yet.";
    const parts = [];
    if (!page.chains.length) {
      parts.push(el("section", { class: "glass money-section" },
        el("p", {}, "Tell MIA why you do what you do, and she'll keep it here with the facts behind it."),
        el("p", { class: "dim" }, "Say “the reason I'm working this job is to pay off my debt”, or link two goals below.")));
    }
    page.chains.forEach((chain) => parts.push(el("section", { class: "glass why-chain", "aria-label": chain.map((l) => l.name).join(" to ") },
      el("p", { class: "pw-label" }, chain.map((l) => l.name).join(" → ")),
      el("ol", { class: "why-links" }, chain.map(linkCard)))));
    if (page.changes.length) parts.push(el("section", { class: "glass money-section" }, el("h2", {}, "Since You Started"),
      el("ul", {}, page.changes.map((c) => el("li", {}, c)))));
    if (page.wins.length) parts.push(el("section", { class: "glass money-section" }, el("h2", {}, "Recent Wins"),
      el("ul", { class: "why-wins" }, page.wins.map((w) => el("li", {}, w)))));
    parts.push(el("div", { class: "row-buttons" }, el("button", { type: "button", class: "btn btn-amber", onclick: () => link(null) }, "Link Two Goals")));
    $("panel").replaceChildren(...parts);
  }

  MIAShell.start(async () => {
    page = await MIA.why();
    if (!page.available) { $("panel").replaceChildren(el("p", { class: "empty" }, "Goals aren't on this MIA.")); return; }
    draw();
  }, { refreshOnChange: true });
})();
