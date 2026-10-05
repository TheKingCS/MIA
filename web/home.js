/*
 * home.js — MIA's Home (muse, 2026-10-05).
 *
 * Home is presence-only (Q-0004): one ambient state on the orb — an earned
 * celebration (loud, DEC-0014), the one due item (calm), or quiet (the
 * default). The briefing is one tap away (progression first, needs second,
 * context last). Talk lives on this same screen — no separate Ask page.
 *
 * Data flow (kept from the scaffold): everything shown comes from Life
 * State via MIA.state(); every change goes Propose -> visible
 * confirmation (the engine's summary) -> Approve -> Undo. No business
 * logic here: no totals, no date math, no permissions (DEC-0004).
 * Talk posts to /api/voice/text with the same session the engine client
 * uses; TODO(claude): promote this into mia.js as MIA.talk().
 */
(function () {
  "use strict";
  const $ = (id) => document.getElementById(id);
  const arr = (v) => (Array.isArray(v) ? v : []);

  /* The newest win we've already celebrated, so a re-render (e.g. a live
     update from another device) doesn't celebrate twice. */
  let lastWinSeen = null;
  try { lastWinSeen = localStorage.getItem("mia.lastWin"); } catch (e) { /* private mode */ }
  function markWinSeen(at) {
    lastWinSeen = at;
    try { localStorage.setItem("mia.lastWin", at); } catch (e) { /* private mode */ }
  }

  /* ---------- status line + undo ---------- */
  function say(text, undoable) {
    const status = $("status");
    status.replaceChildren();
    if (!text) return;
    status.append(document.createTextNode(text));
    if (undoable) {
      const button = document.createElement("button");
      button.textContent = "Undo";
      button.onclick = async () => {
        try { await MIA.undo(undoable.proposal_id); say("Undone."); }
        catch (e) { say(e && e.message ? e.message : "Couldn't undo that."); }
      };
      status.append(button);
    }
  }

  /* ---------- propose -> confirm -> approve ---------- */
  function confirmWith(text) {
    return new Promise((resolve) => {
      const dialog = $("confirm");
      $("confirm-text").textContent = text;
      dialog.onclose = () => resolve(dialog.returnValue === "yes");
      $("confirm-yes").onclick = () => dialog.close("yes");
      $("confirm-no").onclick = () => dialog.close("no");
      dialog.showModal();
      $("confirm-yes").focus();
    });
  }

  async function act(action) {
    try {
      const proposal = await MIA.propose(action.kind, action.params || {}); // 1. Propose
      const ok = await confirmWith(proposal.summary + "?");                 // 2. Approve?
      if (!ok) { await MIA.reject(proposal.proposal_id); return; }
      const done = await MIA.approve(proposal.proposal_id);                 // 3-4. Execute, record
      say(done.result || "Done.", done.undoable ? done : null);             // 5. Undo offered
    } catch (e) {
      say(e && e.message ? e.message : "That didn't go through.");
    }
  }

  /* ---------- presence: celebrate > the one thing > quiet ---------- */
  function presenceMood(state) {
    const wins = arr(state.recent_wins && state.recent_wins.latest);
    const counts = (state.recent_wins && state.recent_wins.counts) || {};
    const known = wins.filter((w) => Object.keys(counts).includes(w.type));
    const newest = known[0] || null;
    const due = arr(state.due && state.due.items)
      .filter((i) => i.when === "overdue" || i.when === "today");
    return { newest, first: due[0] || null };
  }

  function renderPresence(state) {
    const presence = $("presence");
    const line = $("presence-line");
    const sub = $("presence-sub");
    const { newest, first } = presenceMood(state);

    if (newest && newest.at !== lastWinSeen) {
      // Earned progression: loud, game-like (DEC-0014). Never punishing.
      presence.dataset.mood = "celebrate";
      line.textContent = (newest.summary || "Something worth celebrating") + "!";
      sub.hidden = false;
      sub.textContent = "MIA noticed. That's the whole point of the game layer.";
      markWinSeen(newest.at);
    } else if (first) {
      // The one thing — calm, factual, one line.
      presence.dataset.mood = "needs-you";
      line.textContent = first.when === "overdue" ? "One thing needs you." : "One thing for today.";
      sub.hidden = true;
    } else {
      // Quiet is the default. No words needed.
      presence.dataset.mood = "quiet";
      line.textContent = "";
      sub.hidden = true;
    }
  }

  /* ---------- the focus card: the one due item + its action ---------- */
  function renderFocus(state) {
    const { first } = presenceMood(state);
    const focus = $("focus");
    focus.hidden = !first;
    if (!first) return;
    $("focus-kicker").textContent = first.when === "overdue" ? "Overdue" : "Today";
    $("focus-title").textContent = first.title || "";
    $("focus-detail").textContent = first.detail || "";
    const actions = $("focus-actions");
    actions.replaceChildren();
    if (first.action && first.action.kind) {
      const button = document.createElement("button");
      button.className = "primary";
      button.textContent = first.action.label || "Do it";
      button.onclick = () => act(first.action);
      actions.append(button);
    }
  }

  /* ---------- briefing: one tap away ---------- */
  function li(text, className) {
    const item = document.createElement("li");
    item.textContent = text;
    if (className) item.className = className;
    return item;
  }
  function stag(status) {
    const s = document.createElement("span");
    s.className = "stag";
    s.textContent = status || "STATIC";
    return s;
  }
  function sectionEl(title, status, items) {
    if (!items.length) return null;
    const wrap = document.createElement("div");
    wrap.className = "briefing-section";
    const heading = document.createElement("h3");
    heading.append(document.createTextNode(title), stag(status));
    const list = document.createElement("ul");
    items.forEach((i) => list.append(i));
    wrap.append(heading, list);
    return wrap;
  }

  function renderBriefing(state) {
    const body = $("briefing-body");
    body.replaceChildren();
    const isChild = !!(state.person && state.person.child);
    const { first } = presenceMood(state);
    const wins = arr(state.recent_wins && state.recent_wins.latest).slice(0, 5);
    const friction = arr(state.friction && state.friction.items);
    const chains = arr(state.goals && state.goals.chains);
    const signals = arr(state.missions_and_skills && state.missions_and_skills.signals);
    const plan = state.finances && state.finances.monthly_plan;
    const sections = [];

    // 1. The one due item.
    if (first) {
      sections.push(sectionEl("Now", state.due && state.due.status, [
        li((first.title || "") + (first.detail ? " — " + first.detail : "")),
      ]));
    }
    // 2. Wins: progression first, celebratory (DEC-0014).
    if (wins.length) {
      sections.push(sectionEl("Wins", state.recent_wins && state.recent_wins.status,
        wins.map((w) => li(w.summary || "", "win"))));
    }
    // 3. Friction: calm, one line each.
    if (friction.length) {
      sections.push(sectionEl("In the way", state.friction && state.friction.status,
        friction.map((f) => li(f.text || "", "calm"))));
    }
    // 4. Questline position.
    if (chains.length) {
      sections.push(sectionEl("Questline", state.goals && state.goals.status,
        chains.map((c) => li(arr(c).join(" → "), "chain"))));
    }
    // 5. Skill/mission signals, only if present.
    if (signals.length) {
      sections.push(sectionEl("Signals", state.missions_and_skills && state.missions_and_skills.status,
        signals.map((s) => li(typeof s === "string" ? s : (s.text || s.summary || ""), "calm"))));
    }
    // 6. Money gap: only if negative; children get the honest empty state.
    if (isChild || (state.finances && state.finances.hidden)) {
      sections.push(sectionEl("Money", "STATIC", [
        li("That one's for grown-ups. Ask a parent if you need it.", "muted"),
      ]));
    } else if (plan && plan.gap < 0) {
      sections.push(sectionEl("Money", state.finances && state.finances.status, [
        li(plan.note || "Planned monthly outflow is more than expected income.", "calm"),
      ]));
    }
    // Properties are drill-down only — never on the briefing (Q-0004).

    if (!sections.length) {
      const empty = document.createElement("p");
      empty.className = "muted";
      empty.textContent = "Nothing to brief. It's quiet — that's allowed.";
      body.append(empty);
      return;
    }
    sections.filter(Boolean).forEach((s) => body.append(s));
  }

  function render(state) {
    renderPresence(state);
    renderFocus(state);
    renderBriefing(state);
  }

  /* ---------- Talk: conversation lives on Home ---------- */
  function threadBubble(text, who) {
    const thread = $("talk-thread");
    const bubble = document.createElement("div");
    bubble.className = "bubble " + who;
    bubble.textContent = text;
    thread.append(bubble);
    thread.scrollTop = thread.scrollHeight;
    return bubble;
  }

  async function talk(text) {
    // Same session the engine client uses; promoted to MIA.talk() later.
    let token = null;
    try { token = sessionStorage.getItem("mia.token"); } catch (e) { /* private mode */ }
    if (MIA.demo || !token) {
      throw new Error("Talk needs MIA running — this is the placeholder demo.");
    }
    const res = await fetch("/api/voice/text", {
      method: "POST",
      headers: { Authorization: "Bearer " + token, "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.detail || res.statusText || "MIA didn't answer.");
    return data.reply_text || arr(data.replies).join("\n") || "…";
  }

  function wireTalk() {
    const form = $("talk-form");
    const input = $("talk-input");
    const note = $("talk-note");
    const presence = $("presence");
    if (MIA.demo) {
      note.hidden = false;
      note.textContent = "Talk is off in the demo — it needs MIA running.";
      input.disabled = true;
      $("talk-send").disabled = true;
      return;
    }
    form.onsubmit = async (event) => {
      event.preventDefault();
      const text = input.value.trim();
      if (!text) return;
      input.value = "";
      threadBubble(text, "you");
      const thinking = threadBubble("…", "mia thinking");
      presence.dataset.mood = "thinking";
      try {
        const reply = await talk(text);
        thinking.classList.remove("thinking");
        thinking.textContent = reply;
      } catch (e) {
        thinking.classList.remove("thinking");
        thinking.textContent = e && e.message ? e.message : "MIA didn't answer.";
      } finally {
        refresh(); // the turn may have changed the state; presence follows
      }
    };
  }

  /* ---------- briefing sheet ---------- */
  function wireBriefing() {
    const sheet = $("briefing");
    const toggle = $("briefing-toggle");
    const close = $("briefing-close");
    function open() {
      sheet.hidden = false;
      toggle.setAttribute("aria-expanded", "true");
      close.focus();
    }
    function shut() {
      sheet.hidden = true;
      toggle.setAttribute("aria-expanded", "false");
      toggle.focus();
    }
    toggle.onclick = open;
    close.onclick = shut;
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && !sheet.hidden) shut();
    });
  }

  /* ---------- boot ---------- */
  async function refresh() {
    try { render(await MIA.state()); }
    catch (e) {
      if (e && e.status === 401) { // signed out (MIA restarted): sign in again
        try { sessionStorage.removeItem("mia.token"); } catch (x) { /* private mode */ }
        location.reload();
      } else {
        say(e && e.message ? e.message : "Couldn't reach MIA.");
      }
    }
  }

  function start() {
    $("sign-in").hidden = true;
    $("home").hidden = false;
    $("talk").hidden = false;
    if (MIA.demo) say("Demo: placeholder data; actions are off.");
    wireBriefing();
    wireTalk();
    refresh();
    MIA.onChange(refresh); // live: re-read the state whenever MIA's data changes
  }

  // Boot: hidden until we know the sign-in state.
  $("home").hidden = true;
  $("talk").hidden = true;
  if (!MIA.signedIn) {
    // The phone: sign in like the phone app (the desktop signs in for you).
    const form = $("sign-in");
    form.hidden = false;
    form.onsubmit = async (event) => {
      event.preventDefault();
      try { await MIA.signIn($("who").value.trim(), $("password").value); say(""); start(); }
      catch (e) { say(e && e.message ? e.message : "Couldn't sign in."); }
    };
    return;
  }
  start();
})();
