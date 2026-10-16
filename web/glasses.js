/* MIA on Display glasses — one card at a time (muse, 2026-10-06, DEC-0016).
   Moments: glance (her + one focus), apps, quest, voice, nudge, levelup.
   Apps (H-0041; Zac 2026-10-16): she boots to her orb; swipe to flip
   through the person's app cards, select one for its quick action menu
   (core/glasses.py), select an item for its panel, and approve a change
   with a second select.
   Look: the Stark engineering language (DEC-0023) — cyan on black, mono
   labels. Data: MIA.dashboard() and MIA.shell(); voice goes through
   MIA.talk(); apps come from MIA.glasses(). In the demo (public preview)
   it reads the placeholder examples, says so, and voice answers from a
   tiny local script. Nothing here invents facts: every line on a card
   comes from the engine or is labeled demo. */
(function () {
  "use strict";
  const $ = (id) => document.getElementById(id);
  const card = $("card"), orbWrap = $("orb-wrap"), wave = $("wave");
  const demo = MIA.demo;
  $("demo-tag").hidden = !demo;

  let dash = null, shell = null, glassesData = null, moment = "glance", questDone = false;
  let appIndex = 0;

  function el(tag, cls, html) {
    const n = document.createElement(tag);
    if (cls) n.className = cls;
    if (html != null) n.innerHTML = html;
    return n;
  }
  const esc = (s) => String(s == null ? "" : s).replace(/[&<>"]/g, (c) => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));

  function person() { return (shell && shell.person) || {}; }
  function xpLine() {
    const p = person();
    return "lvl " + (p.level || "–") + " · " + (p.total_xp || 0) + " XP";
  }
  function paintXp() {
    const p = person();
    $("xp-label").textContent = xpLine();
    const pct = p.xp_for_level ? Math.max(2, Math.round(100 * p.xp_into_level / p.xp_for_level)) : 0;
    requestAnimationFrame(() => { $("xp-fill").style.width = pct + "%"; });
  }
  function setOrb(mode) {
    orbWrap.classList.toggle("listening", mode === "listening");
    orbWrap.classList.toggle("happy", mode === "happy");
    wave.hidden = mode !== "speaking";
  }

  // ------------------------------------------------------------ moments
  function glance() {
    setOrb("idle"); showFinder(false);
    const f = (dash && dash.focus && dash.focus[0]) || null;
    const box = el("div", "g-card");
    box.append(
      el("p", "g-kicker", "Now"),
      el("p", "g-title", esc((dash && dash.greeting) || "MIA")),
      el("p", "g-sub", f ? esc(f.title) + (f.detail ? " · " + esc(f.detail) : "") : "Nothing needs you. Enjoy it."),
      el("p", "g-say", 'say <b>"what\'s next"</b>'));
    card.replaceChildren(box);
    $("voice-input").placeholder = 'say "what\'s next"';
  }

  function quest() {
    setOrb("idle"); showFinder(false);
    const items = ((dash && dash.focus) || []).slice(0, 4);
    const first = items[0];
    const box = el("div", "g-card epic");
    const list = el("ul", "g-lines");
    items.forEach((it, i) => {
      const li = document.createElement("li");
      li.className = "g-check" + (questDone && i === 0 ? " done" : "");
      li.append(el("span", "box", questDone && i === 0 ? "✓" : ""), document.createTextNode(it.title));
      list.append(li);
    });
    const verb = first && first.action ? first.action.label.toLowerCase() : "done";
    const pct = questDone ? 100 : Math.round(100 / Math.max(1, items.length));
    box.append(
      el("p", "g-kicker", "World quest"),
      el("p", "g-title", esc(first ? first.title : "Today's quest")),
      list,
      el("div", "g-bar", '<i style="width:' + pct + '%"></i>'),
      demo ? el("p", "g-reward", "✦ +250 XP") : null,
      el("p", "g-say", questDone ? "complete — well done." : 'say <b>"' + esc(verb) + '"</b> to finish it'));
    card.replaceChildren(box);
    $("voice-input").placeholder = questDone ? 'say "what\'s next"' : 'say "' + verb + '"';
  }

  function voice() {
    setOrb("speaking"); showFinder(false);
    const wrap = el("div", "g-voice");
    wrap.append(
      el("p", "g-say", "She's listening —"),
      el("p", "g-say", 'say <b>"what\'s next"</b> · <b>"remind me"</b> · <b>"done"</b>'));
    card.replaceChildren(wrap);
    $("voice-input").placeholder = 'say "what\'s next"';
    if (demo) $("voice-input").focus();
  }

  function nudge() {
    const late = ((dash && dash.focus) || []).find((f) => f.when === "overdue" || (f.days != null && f.days < 0));
    const it = late || ((dash && dash.focus) || [])[0];
    setOrb("idle"); showFinder(false);
    const box = el("div", "g-card nudge");
    box.append(
      el("p", "g-kicker", "Needs you"),
      el("p", "g-title", esc(it ? it.title : "Nothing needs you")),
      el("p", "g-sub", esc(it && it.detail ? it.detail : "Enjoy the quiet.")),
      el("p", "g-say", 'say <b>"remind me"</b> · <b>"details"</b>'));
    card.replaceChildren(box);
    $("voice-input").placeholder = 'say "remind me"';
  }

  function see() {
    setOrb("idle"); showFinder(true);
    const box = el("div", "g-card see");
    if (demo) {
      box.append(
        el("p", "g-kicker", "See"),
        el("p", "g-title", "Tomato Plant"),
        el("p", "g-sub", "Healthy · Est. harvest: 4–6 days"),
        el("p", "g-say", "demo — the real glasses name what you look at"));
    } else {
      box.append(
        el("p", "g-kicker", "See"),
        el("p", "g-sub", "Look at something and ask her about it."),
        el("p", "g-say", 'say <b>"what am I looking at"</b>'));
    }
    card.replaceChildren(box);
    $("voice-input").placeholder = 'say "what am I looking at"';
  }

  // ------------------------------------------------------------ apps (H-0041; menus: Zac 2026-10-16)
  // Cards -> an app's quick action menu -> a panel (a short readout, some
  // lines of which can be acted on) -> confirm -> done. Every level is
  // engine data (core/glasses.py, MIA.glasses / MIA.glassesPanel); a
  // change is proposed, shown as MIA's own sentence, and approved with a
  // second select (two-gesture approve, H-0008/H-0012). Back undoes a step.
  let level = "cards", menuIndex = 0, lineIndex = 0, panel = null, proposal = null, resultText = "", busy = false;
  let after = "menu";  // where back goes from a result: the menu (an ask) or the refreshed panel (a change)

  function cards() { return (glassesData && glassesData.apps) || []; }
  function currentApp() { return cards()[appIndex] || null; }
  function actionable() { return panel ? panel.lines.map((l, i) => (l.action ? i : -1)).filter((i) => i >= 0) : []; }
  function compact(on) { $("stage").classList.toggle("compact", on); }

  function apps() {
    setOrb("idle"); showFinder(false);
    const list = cards();
    const app = currentApp();
    compact(level !== "cards");
    const box = el("div", "g-card");
    if (!list.length || !app) {
      box.append(el("p", "g-kicker", "Apps"), el("p", "g-title", "Apps aren't available yet"),
        el("p", "g-sub", "MIA couldn't load your apps."));
      card.replaceChildren(box);
      return;
    }
    const letter = (app.name || "?").trim().charAt(0).toUpperCase();
    if (level === "cards") {
      box.append(
        el("p", "g-kicker", "Apps"),
        el("div", "g-app-badge", esc(letter)),
        el("p", "g-title", esc(app.name)),
        el("p", "g-sub" + (app.tone === "attention" ? " g-attn" : ""), esc(app.status || app.tagline || "")),
        el("p", "g-app-pos", (appIndex + 1) + " of " + list.length),
        el("p", "g-say", "swipe for more · select to open"));
    } else if (level === "menu") {
      const ul = el("ul", "g-menu");
      app.menu.forEach((m, i) => {
        const li = el("li", i === menuIndex ? "sel" : "", esc(m.label) + (m.type === "ask" ? '<span class="g-tag">ask</span>' : ""));
        li.onclick = (e) => { e.stopPropagation(); menuIndex = i; select(); };
        ul.append(li);
      });
      box.append(el("p", "g-kicker", esc(app.name)), ul, el("p", "g-say", "swipe to choose · select · back"));
    } else if (level === "panel") {
      const item = app.menu[menuIndex] || {};
      box.append(el("p", "g-kicker", esc(app.name) + " · " + esc(item.label || "")));
      if (!panel) {
        box.append(el("p", "g-sub", "Loading…"));
      } else if (!panel.lines.length) {
        box.append(el("p", "g-sub", esc(panel.empty || "Nothing here.")));
      } else {
        const ul = el("ul", "g-rows");
        const sel = actionable()[lineIndex];
        panel.lines.forEach((l, i) => {
          const li = el("li", [l.tone ? "t-" + l.tone : "", l.action ? "can" : "", i === sel ? "sel" : ""].join(" ").trim());
          li.append(el("span", "g-row-text", esc(l.text)));
          if (l.detail) li.append(el("span", "g-row-detail", esc(l.detail)));
          if (l.action) li.append(el("span", "g-row-act", esc(l.action.label)));
          if (l.action) li.onclick = (e) => { e.stopPropagation(); lineIndex = actionable().indexOf(i); select(); };
          ul.append(li);
        });
        box.append(ul);
        if (panel.more) box.append(el("p", "g-app-pos", "+ " + panel.more + " more on your phone"));
      }
      box.append(el("p", "g-say", actionable().length ? "swipe to choose · select to do it · back" : "back to the menu"));
    } else if (level === "confirm") {
      box.append(el("p", "g-kicker", "Confirm"),
        el("p", "g-sub g-confirm", esc(proposal ? proposal.summary : "")),
        el("p", "g-say", "select again to approve · back to cancel"));
    } else {
      box.append(el("p", "g-kicker", esc(app.name)), el("div", "g-sub", ""),
        el("p", "g-say", "back to the menu"));
      box.querySelector("div.g-sub").textContent = resultText;
    }
    card.replaceChildren(box);
  }

  async function openPanel() {
    const app = currentApp(), item = app && app.menu[menuIndex];
    if (!item) return;
    if (item.type === "ask") {
      level = "result"; after = "menu"; resultText = "…"; apps(); setOrb("listening");
      try {
        const turn = await MIA.talk(item.say);
        resultText = turn.reply_text || "Done.";
        setOrb("speaking"); setTimeout(() => setOrb("idle"), 1400);
      } catch (err) { resultText = err.message; setOrb("idle"); }
      if (level === "result") apps();
      return;
    }
    level = "panel"; panel = null; lineIndex = 0; apps();
    try { panel = await MIA.glassesPanel(app.id, item.id); }
    catch (err) { panel = { lines: [], empty: err.message, more: 0 }; }
    if (level === "panel") apps();
  }

  async function select() {
    if (busy) return;
    const app = currentApp();
    if (!app) return;
    busy = true;
    try {
      if (level === "cards") { level = "menu"; menuIndex = 0; apps(); }
      else if (level === "menu") { await openPanel(); }
      else if (level === "panel") {
        const line = panel && panel.lines[actionable()[lineIndex]];
        if (!line) return;
        try { proposal = await MIA.propose(line.action.kind, line.action.params); level = "confirm"; }
        catch (err) { level = "result"; after = "panel"; resultText = err.message; }
        apps();
      } else if (level === "confirm") {
        try {
          const done = await MIA.approve(proposal.proposal_id);
          resultText = done.result || done.summary || "Done.";
          setOrb("happy"); setTimeout(() => setOrb("idle"), 1600);
        } catch (err) { resultText = err.message; }
        proposal = null; level = "result"; after = "panel"; apps();
      } else if (level === "result") { back(); }
    } finally { busy = false; }
  }

  function move(dir) {
    const app = currentApp();
    if (level === "cards") {
      const n = cards().length;
      if (n) { appIndex = (appIndex + dir + n) % n; apps(); }
    } else if (level === "menu" && app) {
      const n = app.menu.length;
      if (n) { menuIndex = (menuIndex + dir + n) % n; apps(); }
    } else if (level === "panel") {
      const n = actionable().length;
      if (n) { lineIndex = (lineIndex + dir + n) % n; apps(); }
    }
  }

  function back() {
    if (level === "confirm") {
      if (proposal) MIA.reject(proposal.proposal_id).catch(() => {});
      proposal = null; level = "panel"; apps(); return;
    }
    if (level === "result" && after === "panel") { setOrb("idle"); openPanel(); return; }
    if (level === "result" || level === "panel") { setOrb("idle"); panel = null; level = "menu"; apps(); return; }
    if (level === "menu") { level = "cards"; apps(); return; }
    compact(false);
    go("glance");
  }

  function levelup(xpText, sub) {
    setOrb("happy");
    $("burst-title").textContent = "LEVEL UP";
    $("burst-sub").textContent = (xpText || "") + (sub ? " — " + sub : "");
    $("burst").hidden = false;
  }
  $("burst-ok").onclick = () => { $("burst").hidden = true; go("glance"); };

  const MOMENTS = [
    ["glance", "Now", glance],
    ["apps", "Apps", apps],
    ["quest", "Quest", quest],
    ["voice", "Talk", voice],
    ["nudge", "Needs you", nudge],
    ["see", "See", see],
  ];
  function drawDots() {
    $("dots").replaceChildren(...MOMENTS.map(([id, label]) => {
      const b = document.createElement("button");
      b.type = "button"; b.title = label; b.setAttribute("aria-label", label);
      b.setAttribute("aria-current", String(id === moment));
      b.onclick = () => go(id);
      return b;
    }));
  }
  function go(id) {
    moment = id;
    if (id === "apps") level = "cards"; else compact(false);
    const m = MOMENTS.find(([k]) => k === id);
    if (m) m[2]();
    drawDots();
  }

  // ------------------------------------------------------------ voice
  function answer(text) {
    const t = text.toLowerCase();
    const items = ((dash && dash.focus) || []).slice(0, 3);
    if (/\b(done|did it|finished)\b/.test(t)) {
      questDone = true;
      setOrb("speaking");
      reply("Marked done. Nice work." + (demo ? "" : ""), () => levelup(demo ? "+250 XP" : "", "quest complete"));
      return;
    }
    if (/remind/.test(t)) { reply("I'll remind you. Anything else?"); return; }
    const openMatch = t.match(/\bopen\s+(.+?)\s*$/);
    if (openMatch) {
      const want = openMatch[1].replace(/^the\s+/, "");
      const idx = cards().findIndex((a) => [a.name, a.full_name, a.id].some((n) => (n || "").toLowerCase() === want));
      if (idx >= 0) { appIndex = idx; go("apps"); level = "menu"; menuIndex = 0; apps(); return; }
      if (/^apps?$/.test(want)) { go("apps"); return; }
    }
    if (/\bback\b/.test(t)) { if (moment === "apps") back(); return; }
    if (/next|today|priority/.test(t)) {
      const lines = items.map((f) => "<li>" + esc(f.title) + "</li>").join("");
      reply("Your top priority today:<ul class='g-lines'>" + lines + "</ul>", null, true);
      return;
    }
    reply(demo ? "Heard. (Demo: talk needs MIA running.)" : "Heard.");
  }
  function reply(html, after, isHtml) {
    setOrb("speaking");
    const box = el("div", "g-card");
    box.append(el("p", "g-kicker", "MIA"), el("div", "g-sub", ""));
    box.querySelector(".g-sub").innerHTML = isHtml ? html : esc(html);
    box.append(el("p", "g-say", 'say <b>"what\'s next"</b>'));
    card.replaceChildren(box);
    setTimeout(() => { setOrb("idle"); if (after) after(); }, 1400);
  }
  $("demo-console").addEventListener("submit", async (e) => {
    e.preventDefault();
    const input = $("voice-input");
    const text = input.value.trim();
    if (!text) return;
    input.value = "";
    setOrb("listening");
    if (demo) { setTimeout(() => answer(text), 600); return; }
    try {
      const turn = await MIA.talk(text);
      reply(turn.reply_text || "Done.");
    } catch (err) { reply(err.message); }
  });

  // ------------------------------------------------------------ swipe + keys
  // From her glance, a swipe opens the app cards; in the apps, swipe moves
  // (cards, menu items, the lines you can act on), select goes in, back
  // comes out. Arrow keys and Enter/Escape in the preview; the Neural
  // Band's scroll and pinch on the glasses.
  // On a touchscreen a swipe down is back.
  let touchX = null, touchY = null;
  $("stage").addEventListener("touchstart", (e) => {
    if (e.changedTouches.length) { touchX = e.changedTouches[0].clientX; touchY = e.changedTouches[0].clientY; }
  }, { passive: true });
  $("stage").addEventListener("touchend", (e) => {
    if (touchX == null || !e.changedTouches.length) return;
    const dx = e.changedTouches[0].clientX - touchX, dy = e.changedTouches[0].clientY - touchY;
    touchX = touchY = null;
    if (dy > 50 && Math.abs(dy) > Math.abs(dx)) { if (moment === "apps") back(); return; }
    if (Math.abs(dx) < 40) return;
    if (moment === "glance") { go("apps"); return; }
    if (moment === "apps") move(dx < 0 ? 1 : -1);
  }, { passive: true });
  $("card").addEventListener("click", () => { if (moment === "apps") select(); });
  document.addEventListener("keydown", (e) => {
    if (e.target && e.target.id === "voice-input") return;
    if (moment === "glance" && (e.key === "ArrowRight" || e.key === "Enter")) { e.preventDefault(); go("apps"); return; }
    if (moment !== "apps") return;
    if (e.key === "ArrowRight" || e.key === "ArrowDown") { e.preventDefault(); move(1); }
    else if (e.key === "ArrowLeft" || e.key === "ArrowUp") { e.preventDefault(); move(-1); }
    else if (e.key === "Enter") { e.preventDefault(); select(); }
    else if (e.key === "Escape" || e.key === "Backspace") { e.preventDefault(); back(); }
  });

  function showFinder(on) { $("finder").hidden = !on; }

  // ------------------------------------------------------------ boot
  (async () => {
    if (demo) {
      document.body.classList.add("demo");
      $("demo-console").hidden = false;
    }
    // the waveform's bars, each on its own phase
    for (let i = 0; i < 44; i++) {
      const b = document.createElement("i");
      b.style.animationDelay = (Math.random() * -1.4).toFixed(2) + "s";
      wave.append(b);
    }
    try { dash = await MIA.dashboard(); } catch (e) { dash = null; }
    try { shell = await MIA.shell(); } catch (e) { shell = null; }
    try { glassesData = await MIA.glasses(); } catch (e) { glassesData = null; }
    paintXp();
    go("glance");
  })();
})();
