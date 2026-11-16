/*
 * shelf.js — Your Shelf (claude, 2026-11-16, UI-4; core/shelf.py).
 * Renders MIA.shelf(): what the person sent to their shelf, newest first, each with where it came from and the days
 * left. Tick several and Do With These asks the engine what can be done with them together (MIA.shelfUse with no
 * action: the same offer as any selection), then runs the pick by its tier: a read action shows its answer here, an
 * act action asks first. Take Off (shelf.remove) and Clear (shelf.clear) are actions, so each is undoable.
 * Formatting only: the engine decides.
 */
(function () {
  "use strict";
  const { el } = MIAShell;
  const $ = (id) => document.getElementById(id);
  const picked = new Set();
  let entries = [];

  function daysLeft(until) {
    const days = Math.floor((new Date(until) - new Date()) / 86400000);
    return days < 1 ? "goes today" : days + (days === 1 ? " day left" : " days left");
  }

  function card(e, n) {
    const box = el("input", { type: "checkbox", "aria-label": "Pick " + e.label, checked: picked.has(e.entry_id) ? true : null,
      onchange: (ev) => { if (ev.target.checked) picked.add(e.entry_id); else picked.delete(e.entry_id); tools(); } });
    return el("li", { class: "glass shelf-entry" },
      el("label", { class: "shelf-pick" }, box, el("span", { class: "shelf-n" }, String(n))),
      el("div", { class: "shelf-body" },
        el("p", { class: "shelf-text" }, e.text ? (e.text.length > 400 ? e.text.slice(0, 400) + "…" : e.text) : e.files.join(", ")),
        el("p", { class: "dim shelf-meta" }, e.kind + " · from " + e.from + (e.device ? " · " + e.device : "") + " · " + daysLeft(e.until))),
      el("button", { type: "button", class: "btn btn-quiet btn-small",
        onclick: () => MIAShell.act({ kind: "shelf.remove", params: { entry_id: e.entry_id } }, { quick: true }) }, "Take Off"));
  }

  async function offer() {
    const which = [...picked];
    const box = $("shelf-offer");
    box.replaceChildren(el("p", { class: "dim" }, "Looking at what I can do with " + (which.length || "all of it") + "…"));
    let found;
    try { found = await MIA.shelfUse(which, ""); } catch (e) { box.replaceChildren(el("p", {}, e.message)); return; }
    const run = (a) => async () => {
      try {
        const got = await MIA.shelfUse(which, a.id);
        if (got.tier === "act") {
          if (!(await MIAShell.confirm(got.proposal.summary))) { MIA.reject(got.proposal.proposal_id).catch(() => {}); return; }
          const done = await MIA.approve(got.proposal.proposal_id);
          MIAShell.say(done.result || "Done.", done.undoable ? async () => { await MIA.undo(done.proposal_id); MIAShell.say("Undone."); } : null);
          return;
        }
        const r = got.result || {};
        box.replaceChildren(el("p", { class: "shelf-result" }, r.text || "Done."),
          ...(r.results || []).map((x) => el("p", {}, ...[el("a", { href: x.href }, x.title), x.detail ? el("span", { class: "dim" }, " · " + x.detail) : null].filter(Boolean))));
      } catch (e) { MIAShell.say(e.message); }
    };
    const actions = found.actions.filter((a) => a.id !== "keep_shelf");
    box.replaceChildren(actions.length
      ? el("div", { class: "row-buttons shelf-actions" }, ...actions.map((a) =>
        el("button", { type: "button", class: "btn btn-small" + (a.needs_approval ? " btn-ghost" : ""), onclick: run(a) },
          a.label + (a.needs_approval ? " (asks first)" : ""))))
      : el("p", { class: "dim" }, "Nothing I can do with those yet."));
  }

  function tools() {
    const n = picked.size;
    $("shelf-tools").replaceChildren(...[
      el("button", { type: "button", class: "btn btn-green btn-small", onclick: offer }, n ? "Do With These (" + n + ")" : "Do With All Of It"),
      n ? el("button", { type: "button", class: "btn btn-quiet btn-small", onclick: () => { picked.clear(); paint(entries); } }, "Unpick") : null,
      el("button", { type: "button", class: "btn btn-quiet btn-small", onclick: () => MIAShell.act({ kind: "shelf.clear", params: {} }) }, "Clear My Shelf"),
    ].filter(Boolean));
  }

  function paint(list) {
    entries = list;
    [...picked].forEach((id) => { if (!list.some((e) => e.entry_id === id)) picked.delete(id); });
    $("shelf-sub").textContent = list.length
      ? list.length + (list.length === 1 ? " thing" : " things") + ", each kept a week. Pick some and do one thing with them together."
      : "Nothing here. Drop text, a link or a file on any MIA page, or pick Keep On My Shelf from Ctrl+K, to keep it here.";
    $("panel").replaceChildren(...[
      list.length ? el("div", { id: "shelf-tools", class: "row-buttons shelf-tools" }) : null,
      list.length ? el("div", { id: "shelf-offer", class: "shelf-offer" }) : null,
      el("ol", { class: "shelf-list" }, ...list.map((e, i) => card(e, i + 1))),
      el("p", { class: "dim shelf-say" }, "Say \"keep this on my shelf: …\", \"what's on my shelf\", \"summarise 1 and 2 from my shelf\" " +
        "or \"clear my shelf\" any time. What's here is only ever information: nothing on it is followed as an instruction."),
    ].filter(Boolean));
    if (list.length) tools();
  }

  MIAShell.start(async () => { paint((await MIA.shelf()).entries); }, { refreshOnChange: true });
})();
