/* MIA on Display glasses — one card at a time (muse, 2026-10-06, DEC-0016).
   Moments: glance (her + one focus), apps, quest, voice, nudge, levelup.
   Apps (H-0041, Phase 1): swipe through the first app cards (Kitchen,
   Workout, Missions, Money), select one for its detail. The action menu
   arrives with the engine's per-app glance actions (Phase 2); the detail
   card shows the app's real description and example command until then.
   Look: the Stark engineering language (DEC-0023) — cyan on black, mono
   labels. Data: MIA.dashboard() and MIA.shell(); voice goes through
   MIA.talk(); apps come from MIA.apps(). In the demo (public preview)
   it reads the placeholder examples, says so, and voice answers from a
   tiny local script. Nothing here invents facts: every line on a card
   comes from the engine or is labeled demo. */
(function () {
  "use strict";
  const $ = (id) => document.getElementById(id);
  const card = $("card"), orbWrap = $("orb-wrap"), wave = $("wave");
  const demo = MIA.demo;
  $("demo-tag").hidden = !demo;

  let dash = null, shell = null, appsData = null, moment = "glance", questDone = false;
  let appIndex = 0, appDetail = false;

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

  // ------------------------------------------------------------ apps (H-0041, Phase 1)
  const FIRST_APPS = ["kitchen", "workout", "missions", "budget"];
  function firstApps() {
    const all = (appsData && appsData.groups ? appsData.groups : []).flatMap((g) => g.apps || []);
    const shown = all.filter((a) => a.shown !== false);
    const picked = FIRST_APPS.map((id) => shown.find((a) => a.id === id)).filter(Boolean);
    return picked.length ? picked : shown.slice(0, 4);
  }
  function apps() {
    setOrb("idle"); showFinder(false);
    const list = firstApps();
    const box = el("div", "g-card");
    if (!list.length) {
      box.append(
        el("p", "g-kicker", "Apps"),
        el("p", "g-title", "Apps aren't available yet"),
        el("p", "g-sub", "MIA couldn't load the app list."));
      card.replaceChildren(box);
      $("voice-input").placeholder = 'say "what\'s next"';
      return;
    }
    appIndex = Math.max(0, Math.min(appIndex, list.length - 1));
    const app = list[appIndex];
    const letter = (app.name || "?").trim().charAt(0).toUpperCase();
    const ask = app.ask || ("open " + (app.name || ""));
    if (appDetail) {
      box.append(
        el("p", "g-kicker", "Apps · " + esc(app.name || "")),
        el("div", "g-app-badge", esc(letter)),
        el("p", "g-title", esc(app.name || "")),
        el("p", "g-sub", esc(app.description || app.tagline || "")),
        el("p", "g-say", 'say <b>"' + esc(ask) + '"</b>'),
        el("p", "g-say", "select to go back"));
    } else {
      box.append(
        el("p", "g-kicker", "Apps"),
        el("div", "g-app-badge", esc(letter)),
        el("p", "g-title", esc(app.name || "")),
        el("p", "g-sub", esc(app.tagline || "")),
        el("p", "g-say", 'say <b>"' + esc(ask) + '"</b>'),
        el("p", "g-app-pos", (appIndex + 1) + " of " + list.length),
        el("p", "g-say", "swipe for more · select for details"));
    }
    card.replaceChildren(box);
    $("voice-input").placeholder = 'say "open kitchen"';
  }
  function appNext(dir) {
    const list = firstApps();
    if (!list.length) return;
    if (appDetail) appDetail = false;
    appIndex = (appIndex + dir + list.length) % list.length;
    apps();
  }
  function appSelect() {
    if (!firstApps().length) return;
    appDetail = !appDetail;
    apps();
  }
  function appBack() {
    if (appDetail) { appDetail = false; apps(); return; }
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
    if (id === "apps") appDetail = false;
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
    const openMatch = t.match(/\bopen\s+(kitchen|workout|missions|money|budget|apps?)\b/);
    if (openMatch) {
      const want = openMatch[1].replace("money", "budget").replace(/^apps?$/, "");
      const list = firstApps();
      if (want) {
        const idx = list.findIndex((a) => a.id === want);
        if (idx >= 0) appIndex = idx;
      }
      go("apps");
      return;
    }
    if (/\bback\b/.test(t)) { appBack(); return; }
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

  // ------------------------------------------------------------ swipe + keys (apps carousel)
  let touchX = null;
  $("stage").addEventListener("touchstart", (e) => {
    if (e.changedTouches.length) touchX = e.changedTouches[0].clientX;
  }, { passive: true });
  $("stage").addEventListener("touchend", (e) => {
    if (touchX == null || !e.changedTouches.length) return;
    const dx = e.changedTouches[0].clientX - touchX;
    touchX = null;
    if (moment !== "apps" || Math.abs(dx) < 40) return;
    appNext(dx < 0 ? 1 : -1);
  }, { passive: true });
  $("card").addEventListener("click", () => { if (moment === "apps") appSelect(); });
  document.addEventListener("keydown", (e) => {
    if (moment !== "apps") return;
    if (e.key === "ArrowRight") appNext(1);
    else if (e.key === "ArrowLeft") appNext(-1);
    else if (e.key === "Enter") appSelect();
    else if (e.key === "Escape") appBack();
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
    try { appsData = await MIA.apps(); } catch (e) { appsData = null; }
    paintXp();
    go("glance");
  })();
})();
