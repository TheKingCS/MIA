/* MIA on Display glasses — one card at a time (muse, 2026-10-06, DEC-0016).
   Moments: glance (her + one focus), quest, voice, nudge, levelup.
   Data: MIA.dashboard() and MIA.shell(); voice goes through MIA.talk().
   In the demo (public preview) it reads the placeholder examples, says so,
   and voice answers from a tiny local script. Nothing here invents facts:
   every line on a card comes from the engine or is labeled demo. */
(function () {
  "use strict";
  const $ = (id) => document.getElementById(id);
  const card = $("card"), orbWrap = $("orb-wrap"), wave = $("wave");
  const demo = MIA.demo;
  $("demo-tag").hidden = !demo;

  let dash = null, shell = null, moment = "glance", questDone = false;

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

  function levelup(xpText, sub) {
    setOrb("happy");
    $("burst-title").textContent = "LEVEL UP";
    $("burst-sub").textContent = (xpText || "") + (sub ? " — " + sub : "");
    $("burst").hidden = false;
  }
  $("burst-ok").onclick = () => { $("burst").hidden = true; go("glance"); };

  const MOMENTS = [
    ["glance", "Now", glance],
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
    paintXp();
    go("glance");
  })();
})();
