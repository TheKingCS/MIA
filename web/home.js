/*
 * home.js — SCAFFOLD Home (claude, 2026-10-05), following Muse's Q-0004
 * answer: Home is presence-only (celebrate a new win, else the one most
 * urgent due item, else quiet); the briefing is one tap away (wins →
 * friction → questline → money gap). Everything shown comes from Life
 * State; every change goes Propose → Approve → (engine) → live update.
 * Muse replaces the look; keep the data flow.
 */
(function () {
  "use strict";
  const $ = (id) => document.getElementById(id);
  let lastWinSeen = null;
  try { lastWinSeen = localStorage.getItem("mia.lastWin"); } catch (e) { /* fine */ }

  function say(text, undoProposal) {
    const status = $("status");
    status.textContent = text;
    if (undoProposal) {
      const button = document.createElement("button");
      button.textContent = "Undo";
      button.onclick = async () => {
        try { await MIA.undo(undoProposal.proposal_id); say("Undone."); }
        catch (e) { say(e.message); }
      };
      status.appendChild(button);
    }
  }

  function confirmWith(text) {
    return new Promise((resolve) => {
      const dialog = $("confirm");
      $("confirm-text").textContent = text;
      dialog.onclose = () => resolve(dialog.returnValue === "yes");
      dialog.showModal();
    });
  }

  async function act(action) {
    try {
      const proposal = await MIA.propose(action.kind, action.params);         // 1. Propose
      if (!(await confirmWith(proposal.summary + "?"))) {                       // 2. Approve?
        await MIA.reject(proposal.proposal_id);
        return;
      }
      const done = await MIA.approve(proposal.proposal_id);                     // 3-4. Execute, record
      say(done.result, done.undoable ? done : null);                            // 5. Undo offered
    } catch (e) {
      say(e.message);
    }
  }

  function li(text, className) {
    const item = document.createElement("li");
    item.textContent = text;
    if (className) item.className = className;
    return item;
  }

  function section(title, items) {
    if (!items.length) return null;
    const wrap = document.createElement("div");
    const heading = document.createElement("h2");
    heading.textContent = title;
    const list = document.createElement("ul");
    items.forEach((item) => list.appendChild(item));
    wrap.append(heading, list);
    return wrap;
  }

  function render(state) {
    const name = (state.person && state.person.name) || "";
    const wins = state.recent_wins.latest.filter((e) => Object.keys(state.recent_wins.counts).includes(e.type));
    const newest = wins[0];
    const due = state.due.items.filter((i) => i.when === "overdue" || i.when === "today");
    const presence = $("presence");

    // Presence: celebrate a new win > the one thing that needs you > quiet.
    if (newest && newest.at !== lastWinSeen) {
      presence.dataset.mood = "celebrate";
      $("presence-line").textContent = newest.summary + "!";
      lastWinSeen = newest.at;
      try { localStorage.setItem("mia.lastWin", newest.at); } catch (e) { /* fine */ }
    } else if (due.length) {
      presence.dataset.mood = "needs-you";
      $("presence-line").textContent = name ? `${name}, one thing:` : "One thing:";
    } else {
      presence.dataset.mood = "quiet";
      $("presence-line").textContent = "All quiet.";
    }

    // The one due item (overdue first), with the action the engine suggests.
    const focus = $("focus");
    const first = due[0];
    focus.hidden = !first;
    if (first) {
      $("focus-title").textContent = first.title;
      $("focus-detail").textContent = first.detail;
      const actions = $("focus-actions");
      actions.replaceChildren();
      if (first.action) {
        const button = document.createElement("button");
        button.className = "primary";
        button.textContent = first.action.label;
        button.onclick = () => act(first.action);
        actions.appendChild(button);
      }
    }

    // The briefing: progression first, needs second, context last.
    const body = $("briefing-body");
    body.replaceChildren(...[
      section("Wins this week", wins.slice(0, 5).map((e) => li(e.summary))),
      section("In the way", state.friction.items.map((f) => li(f.text))),
      section("Questline", (state.goals.chains || []).map((c) => li(c.join(" → "), "chain"))),
      state.finances.monthly_plan && state.finances.monthly_plan.gap < 0
        ? section("Money", [li("Planned monthly outflow is more than expected income")]) : null,
    ].filter(Boolean));
  }

  async function refresh() {
    try { render(await MIA.state()); }
    catch (e) { say(e.status === 401 ? "Open MIA's Home from the desktop app to sign in." : e.message); }
  }

  if (!MIA.signedIn) {
    say("Open MIA's Home from the desktop app (or add ?demo to see the example).");
    return;
  }
  if (MIA.demo) say("Demo: placeholder data; actions are off.");
  refresh();
  MIA.onChange(refresh); // live: re-read the state whenever MIA's data changes
})();
