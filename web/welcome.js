/*
 * welcome.js — Home (DEC-0018, claude; the canvas's Home, DEC-0113). Renders
 * MIA.dashboard() and the frame's shell data: the date and greeting, the
 * status strip, MIA's one finding, the focus rows (each with its kind;
 * ticking runs the item's action: confirm, undo), what's upcoming, the
 * level; and on a wide screen MIA's column (MIA.history, things to ask).
 * "Hear It" says the day aloud in MIA's voice (the engine's `briefing`,
 * spoken by /api/heavy/speak on the home computer).
 */
(function () {
  "use strict";
  const { el, act } = MIAShell;
  const $ = (id) => document.getElementById(id);
  if (window.MIAIcons) MIAIcons.badge($("gear"), "settings");  // the line icon (DEC-0023)

  function focusRow(item) {
    return el("li", { class: item.when },
      el("button", { type: "button", class: "tick", disabled: !item.action,
        "aria-label": item.action ? item.action.label + ": " + item.title : item.title,
        title: item.action ? item.action.label : "Open it to deal with this", onclick: () => act(item.action) }),
      el("span", { class: "what" },
        item.page ? el("a", { href: item.page }, item.title) : item.title,
        item.detail ? el("small", {}, item.detail) : null),
      item.kind ? el("span", { class: "kind " + (item.tone || "") }, item.kind) : null);
  }

  // The status strip (DEC-0113): three counts from the engine, white values, a colored index bar.
  function strip(tiles) {
    return (tiles || []).map((t) => el("div", { class: "stat " + (t.tone || "") },
      el("span", {}, el("span", { class: "stat-label" }, t.label), el("span", { class: "stat-value" }, String(t.value)))));
  }

  // MIA Noticed: the one cross-app finding Home leads with, its why, how sure, what she used, and where to act.
  function finding(f) {
    const sure = { REAL: "Fact", DERIVED: "Calculation", SIMULATED: "Estimate" }[f.sure] || "";
    return [
      el("div", { class: "finding-body" },
        el("div", { class: "finding-head" }, el("span", { class: "finding-label" }, "MIA Noticed"),
          sure ? el("span", { class: "kind" }, sure) : null),
        el("h2", { id: "finding-h" }, f.title),
        el("p", { class: "finding-why" }, [f.claim, f.why].filter(Boolean).join(" ")),
        f.next ? el("p", { class: "finding-next" }, f.next) : null,
        f.app_name ? el("p", { class: "used" }, "Used: ", el("b", {}, f.app_name)) : null),
      f.page ? el("div", { class: "finding-actions" },
        el("a", { class: "btn btn-green", href: f.page }, "Open " + (f.app_name || "It"))) : null,
    ];
  }

  // MIA's column on a wide screen: the last thing said, things to ask, a talk box that opens the chat.
  const ASK = ["What should I focus on today?", "What's due this week?", "How are my finances?"];
  // The life cards (DEC-0129, core/web_surfaces.life_cards): what's playing, today's good news, the current or next
  // trip, and the newest pictures kept at home. Each opens its app; a card with nothing to show isn't drawn.
  function life(l) {
    const box = $("life");
    if (!l) { box.hidden = true; return; }
    const card = (href, label, title, sub) => el("a", { class: "glass life-card", href },
      el("span", { class: "pw-label" }, label), el("strong", {}, title), sub ? el("span", { class: "dim" }, sub) : null);
    const cards = [
      l.music ? card("music.html", l.music.playing ? "Now Playing" : "Paused", l.music.title, l.music.artist) : null,
      l.news ? card("news.html", "Good News", l.news.title, l.news.count > 1 ? l.news.count + " stories today" : l.news.tag) : null,
      l.trip ? card("expeditions.html", "Trip · " + l.trip.words, l.trip.name, l.trip.when) : null,
    ].filter(Boolean);
    let strip = null;
    if (l.pictures && l.pictures.length) {
      strip = el("a", { class: "glass life-pictures", href: "vault.html", "aria-label": "Recent pictures, open the Memory Vault" },
        el("span", { class: "pw-label" }, "Recent Pictures"),
        el("div", { class: "life-thumbs" }, l.pictures.map((p) => {
          const img = el("img", { alt: "", loading: "lazy" });
          MIA.image(p.url).then((u) => { if (u) img.src = u; else img.remove(); });
          return img;
        })));
    }
    box.hidden = !cards.length && !strip;
    box.replaceChildren(cards.length ? el("div", { class: "life-cards" }, cards) : null, strip);
  }

  async function miaColumn() {
    const log = $("home-mia-log");
    if (!log) return;
    let messages = [];
    try {
      const t = await MIA.history(4);
      messages = (t && (t.messages || t.thread || t)) || [];
      if (!Array.isArray(messages)) messages = [];
    } catch (e) { messages = []; }
    log.replaceChildren(...messages.slice(-2).map((m) => el("div", { class: "home-mia-msg " + (m.role === "user" ? "me" : "mia") },
      String(m.content || m.text || ""))));
    $("home-mia-ask").replaceChildren(...ASK.map((q) => el("a", { class: "btn btn-ghost", href: "assistant.html?ask=" + encodeURIComponent(q) }, q)));
  }

  // DEC-0130: the Nexus opens first. Opening MIA (a new session, not a link from inside her) goes on to the Nexus;
  // "Today" from the Nexus or the sidebar (index.html?today=1) stays here.
  function nexusFirst() {
    const q = new URLSearchParams(location.search);
    if (q.has("today")) return false;
    if (MIAShell.look && MIAShell.look() !== "spatial") return false;  // the cards look opens here (DEC-0135)
    let seen = null;
    try { seen = sessionStorage.getItem("mia.nexus.opened"); sessionStorage.setItem("mia.nexus.opened", "1"); } catch (e) { return false; }
    if (seen) return false;
    location.replace("nexus.html" + (q.has("demo") ? "?demo" : ""));
    return true;
  }

  async function render() {
    if (nexusFirst()) return;
    const [home, shell] = await Promise.all([MIA.dashboard(), MIA.shell()]);
    $("greeting").textContent = home.greeting;
    hearIt(home.briefing);
    $("subtitle").textContent = home.focus.length
      ? (home.focus.length === 1 ? "One thing needs you today." : home.focus.length + " things need you today.") + " The rest can wait."
      : home.subtitle;
    $("date").textContent = home.date || "";
    $("strip").replaceChildren(...strip(home.strip));
    $("finding").hidden = !home.finding;
    if (home.finding) $("finding").replaceChildren(...finding(home.finding));
    $("focus").replaceChildren(...home.focus.slice(0, 6).map(focusRow));
    $("focus-empty").hidden = home.focus.length > 0;
    // MIA Remembers (DEC-0029): what you told her, as it's about to matter.
    life(home.life);
    const remember = home.remember || [];
    $("remember").hidden = !remember.length;
    $("remember-list").replaceChildren(...remember.map((r) => el("li", {},
      el("a", { href: r.page }, el("span", { "aria-hidden": "true" }, r.icon + " "), r.title),
      ...r.lines.map((line) => el("small", {}, line)))));
    $("upcoming").replaceChildren(...home.upcoming.map(focusRow));
    $("upcoming-empty").hidden = home.upcoming.length > 0;
    const p = shell.person;
    const pct = p.xp_for_level ? Math.round((100 * p.xp_into_level) / p.xp_for_level) : 0;
    $("level").replaceChildren(
      el("span", { class: "home-avatar", "aria-hidden": "true" }, "🧙"),
      el("span", { class: "home-level-text" }, el("strong", {}, "lvl " + p.level), el("small", {}, p.total_xp + " XP")),
      el("span", { class: "xpbar" }, el("span", { class: "xpbar-track" }, el("span", { class: "xpbar-fill", style: "width:" + pct + "%" }))));
  }

  // The spoken briefing: one button beside the greeting; her voice comes from the home computer.
  function hearIt(text) {
    let b = $("hear-it");
    if (!text) { if (b) b.remove(); return; }
    if (!b) {
      b = el("button", { type: "button", class: "btn btn-ghost btn-small home-hear", id: "hear-it", "aria-label": "Hear today's briefing" }, "▶ Hear It");
      $("subtitle").after(b);
    }
    b.onclick = async () => {
      b.disabled = true;
      try { const said = await MIA.speak(text); await new Audio("data:audio/wav;base64," + said.audio_wav_base64).play(); }
      catch (e) { MIAShell.say(e.message || "MIA's voice isn't available right now."); }
      finally { b.disabled = false; }
    };
  }

  // The gear: Profile, Settings, Log out (Zac, 2026-10-07).
  const gear = $("gear"), menu = $("account-dropdown");
  const openMenu = (open) => { menu.hidden = !open; gear.setAttribute("aria-expanded", String(open)); };
  gear.addEventListener("click", (e) => { e.stopPropagation(); openMenu(menu.hidden); });
  document.addEventListener("click", (e) => { if (!menu.hidden && !menu.contains(e.target)) openMenu(false); });
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") openMenu(false); });
  $("logout").addEventListener("click", async () => {
    await MIA.signOut();
    location.replace("index.html");  // no #token: back to sign-in
  });

  MIAShell.start(render);
  miaColumn();
})();
