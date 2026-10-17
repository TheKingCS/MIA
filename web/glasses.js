/* MIA on Display glasses (DEC-0016; Muse's composition H-0041/H-0043;
   Zac's layout, 2026-10-16; pins DEC-0024).

   One fixed 600x600 composition scaled to the screen: nothing scrolls,
   nothing is cut off. Two moves do everything:
     move   (swipe, ← → ↑ ↓, the Neural Band's scroll)  next / previous
     select (tap, Enter, the Band's pinch)              do what's selected
   Every list ends with a Back row, so those two are enough; Esc or a
   swipe down is a shortcut for back.

   Home is her orb alone. Select it and she listens (rings like
   Saturn's); her answer shows under her for a moment, then she's alone
   again. "Hey MIA" will start the same listening through the phone
   companion (H-0041 Phase 3): it calls MIAGlasses.listen().

   From the orb, move to your pinned apps (your favorites), then "All
   apps". Select an app for its quick actions (core/glasses.py). A change
   shows MIA's sentence and needs a second select (two-gesture approve).
   Every word on a screen comes from the engine, or says it's the demo. */
(function () {
  "use strict";
  const $ = (id) => document.getElementById(id);
  const home = $("home"), screen = $("screen"), caption = $("caption");
  const demo = MIA.demo;
  $("demo-tag").hidden = !demo;

  const esc = (s) => String(s == null ? "" : s).replace(/[&<>"]/g, (c) => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
  function el(tag, cls, html) {
    const n = document.createElement(tag);
    if (cls) n.className = cls;
    if (html != null) n.innerHTML = html;
    return n;
  }

  // ------------------------------------------------------------ fit the 600x600 stage to the screen
  function fit() {
    const v = window.visualViewport;
    const w = v ? v.width * v.scale : innerWidth, h = v ? v.height * v.scale : innerHeight;
    document.documentElement.style.setProperty("--fit", String(Math.min(w, h) / 600));
  }
  addEventListener("resize", fit);
  if (window.visualViewport) visualViewport.addEventListener("resize", fit);
  fit();

  // ------------------------------------------------------------ state
  const store = {
    get(k) { try { return localStorage.getItem(k); } catch (e) { return null; } },
    set(k, v) { try { localStorage.setItem(k, v); } catch (e) { /* private window: just don't remember */ } },
  };
  let data = null;           // MIA.glasses(): {apps, others, pinned, hint}
  let view = "home";         // home | cards | menu | panel | confirm | result | reward
  let showingAll = false;    // browsing the apps that aren't pinned
  let appIndex = 0, row = 0;
  let panel = null, proposal = null, resultText = "", after = "menu", busy = false;
  let reward = null, rewardTimer = null;
  let mission = store.get("mia.glasses.mission") || "";

  async function load() {
    try { data = await MIA.glasses(mission); } catch (e) { data = data || { apps: [], others: [] }; }
    if (!data || !Array.isArray(data.apps)) data = { apps: [], others: [] };
    if (window.MIASound && !load.sound) {  // the person's sound settings, once
      load.sound = true;
      MIA.shell().then((s) => MIASound.configure(s.sound)).catch(() => {});
    }
  }

  const ALL = { id: "__all", name: "All Apps" };
  const BACK_CARD = { id: "__back", name: "Back", status: "To your pinned apps" };
  function cards() {
    const d = data || {};
    if (showingAll) return (d.others || []).concat([BACK_CARD]);
    const list = d.apps || [];
    return d.pinned && (d.others || []).length
      ? list.concat([Object.assign({}, ALL, { status: d.others.length + " more apps" })]) : list;
  }
  function app() { return cards()[appIndex] || null; }

  // ------------------------------------------------------------ home: her orb
  let voiceState = "idle", recorder = null, chunks = [], captionTimer = null;
  function orbState(state) {
    voiceState = state;
    home.className = state === "idle" ? "" : state;
  }
  function answer(text, seconds) {
    clearTimeout(captionTimer);
    caption.textContent = text;
    orbState("answered");
    captionTimer = setTimeout(() => { if (voiceState === "answered") orbState("idle"); }, (seconds || 7) * 1000);
  }
  function wav(samples, rate) {
    const buffer = new ArrayBuffer(44 + samples.length * 2);
    const v = new DataView(buffer);
    const str = (o, s) => [...s].forEach((c, i) => v.setUint8(o + i, c.charCodeAt(0)));
    str(0, "RIFF"); v.setUint32(4, 36 + samples.length * 2, true); str(8, "WAVE"); str(12, "fmt ");
    v.setUint32(16, 16, true); v.setUint16(20, 1, true); v.setUint16(22, 1, true); v.setUint32(24, rate, true);
    v.setUint32(28, rate * 2, true); v.setUint16(32, 2, true); v.setUint16(34, 16, true); str(36, "data");
    v.setUint32(40, samples.length * 2, true);
    samples.forEach((x, i) => v.setInt16(44 + i * 2, Math.max(-1, Math.min(1, x)) * 0x7fff, true));
    return new Blob([buffer], { type: "audio/wav" });
  }
  async function toWav(blob) {
    const ctx = new AudioContext();
    const audio = await ctx.decodeAudioData(await blob.arrayBuffer());
    ctx.close();
    const rate = 16000;
    const offline = new OfflineAudioContext(1, Math.ceil(audio.duration * rate), rate);
    const source = offline.createBufferSource();
    source.buffer = audio; source.connect(offline.destination); source.start();
    return wav((await offline.startRendering()).getChannelData(0), rate);
  }
  // Start listening (select on the orb, or "Hey MIA" from the companion later); select again to stop.
  async function listen() {
    if (view !== "home") show("home");
    if (voiceState === "listening") { if (recorder && recorder.state === "recording") recorder.stop(); return; }
    if (voiceState === "thinking") return;
    clearTimeout(captionTimer);
    if (demo) {
      orbState("listening");
      demoTimer = setTimeout(() => {
        orbState("thinking");
        demoTimer = setTimeout(() => answer("This is the demo: talking to her needs MIA running."), 900);
      }, 2600);
      return;
    }
    if (!navigator.mediaDevices || !window.MediaRecorder) { answer("This screen can't use a microphone. \"Hey MIA\" comes with the phone companion."); return; }
    let stream;
    try { stream = await navigator.mediaDevices.getUserMedia({ audio: true }); }
    catch (e) { answer("MIA needs permission to use the microphone."); return; }
    chunks = [];
    recorder = new MediaRecorder(stream);
    recorder.ondataavailable = (e) => chunks.push(e.data);
    cancelled = false;
    recorder.onstop = async () => {
      stream.getTracks().forEach((t) => t.stop());
      if (cancelled) { cancelled = false; return; }
      orbState("thinking");
      try {
        const turn = await MIA.voice(await toWav(new Blob(chunks)));
        if (turn.audio_wav_base64) {
          const audio = new Audio("data:audio/wav;base64," + turn.audio_wav_base64);
          audio.play().catch(() => {});
        }
        answer(turn.reply_text || "Done.", 9);
        load();
      } catch (err) { answer(err.message); }
    };
    recorder.start();
    orbState("listening");
    setTimeout(() => { if (recorder && recorder.state === "recording") recorder.stop(); }, 8000);
  }
  // Move away while she listens: stop without sending anything.
  let cancelled = false, demoTimer = null;
  function stopListening() {
    clearTimeout(demoTimer); clearTimeout(captionTimer);
    if (recorder && recorder.state === "recording") { cancelled = true; recorder.stop(); }
    orbState("idle");
  }
  window.MIAGlasses = { listen };

  // ------------------------------------------------------------ screens
  function hint(selectWhat) {
    return el("p", "hint", "<b>◀ ▶</b> move &nbsp;·&nbsp; <b>●</b> " + esc(selectWhat));
  }
  function badge(a) {
    const icon = window.MIAIcons && MIAIcons.svg(a.id === "__all" ? "apps" : a.id === "__back" ? "mia" : a.id);
    const b = el("div", "badge");
    if (icon) b.append(icon); else b.textContent = (a.name || "?").trim().charAt(0).toUpperCase();
    return b;
  }
  function kicker(left, right) {
    const k = el("p", "k");
    k.append(el("span", "", esc(left)));
    if (right) k.append(el("span", "pos", esc(right)));
    return k;
  }
  // A window of five rows around the selection: the selection moves it, nothing scrolls.
  function rowsOf(items, sel) {
    const n = items.length, start = Math.max(0, Math.min(sel - 2, n - 5));
    const ul = el("ul", "rows");
    items.slice(start, start + 5).forEach((it, k) => {
      const i = start + k;
      const li = el("li", [i === sel ? "sel" : "", it.back ? "back" : "", it.cap ? "cap" : "", it.tone ? "t-" + it.tone : ""].join(" ").trim());
      li.append(el("span", "t", esc(it.back ? "‹ " + it.text : it.text)));
      if (it.detail) li.append(el("span", "d", esc(it.detail)));
      if (it.verb) li.append(el("span", "v", esc(it.verb)));
      li.dataset.row = String(i);
      ul.append(li);
    });
    const more = el("p", "more", (start > 0 ? "▲ " + start + " above" : "") + (start > 0 && start + 5 < n ? " · " : "") +
      (start + 5 < n ? "▼ " + (n - start - 5) + " more" : ""));
    return [ul, more];
  }
  const BACK_ROW = { text: "Back", back: true, kind: "back" };

  function menuRows(a) {
    return (a.menu || []).map((m) => ({ text: (m.type === "action" ? "★ " : "") + m.label, cap: true,
      verb: m.type === "ask" ? "ask" : m.type === "action" ? "" : "›" }))
      .concat([BACK_ROW]);
  }
  // Sorting a list by Past Due / Due Today / Due Soon (Zac, 2026-10-16):
  // its first row; select cycles the sort, the rows follow.
  let sortIndex = 0;
  function sorts() { return (panel && panel.filters) || null; }
  function panelRows() {
    if (!panel) return [BACK_ROW];
    const rows = [];
    const f = sorts();
    const want = f ? f[sortIndex % f.length].id : null;
    if (f) {
      const cur = f[sortIndex % f.length];
      rows.push({ kind: "sort", text: "Sort: " + cur.label + " (" + cur.count + ")", verb: "Sort", cap: true });
    }
    panel.lines.forEach((l) => {
      if (want && l.bucket !== want) return;
      rows.push({ kind: "line", line: l, text: l.text, detail: l.detail, tone: l.tone,
        verb: l.action ? l.action.label : l.pick ? l.pick.label : l.recipe ? "Open" : "" });
    });
    return rows.concat([BACK_ROW]);
  }
  function isCarousel() { return !!(panel && panel.lines.length && panel.lines[0].recipe); }

  // A recipe on the glasses: its picture first, then its ingredients
  // (six to a page) and its steps (one to a page). Move pages; select goes back.
  let recipe = null, page = 0;
  function recipePages(r) {
    const pages = [{ kind: "cover" }];
    for (let i = 0; i < r.ingredients.length; i += 6) pages.push({ kind: "ingredients", items: r.ingredients.slice(i, i + 6), at: i });
    r.steps.forEach((step, i) => pages.push({ kind: "step", text: step, n: i + 1 }));
    return pages;
  }
  function recipePhoto(r, cls) {
    const box = el("div", cls);
    const icon = window.MIAIcons && MIAIcons.svg("kitchen");
    if (icon) box.append(icon);
    if (r.photo) MIA.image(r.photo).then((url) => {
      if (url) { const img = el("img"); img.src = url; img.alt = ""; box.replaceChildren(img); }
    });
    return box;
  }

  function show(v) {
    view = v;
    home.hidden = v !== "home";
    screen.hidden = v === "home";
    if (v !== "home") render();
  }

  function render() {
    const a = app();
    const parts = [];
    if (view === "cards") {
      const list = cards();
      if (!a) {
        parts.push(kicker("Apps"), el("div", "body", '<p class="empty">MIA couldn\'t load your apps.</p>'), hint("back"));
      } else if (a.id === "missions" && a.mission !== undefined) {
        parts.push(kicker(a.name, (appIndex + 1) + " / " + list.length), missionCard(a.mission), hint("select mission"));
      } else {
        const d = data || {};
        const where = showingAll ? "All Apps" : d.pinned ? "Pinned" : "Apps";
        const body = el("div", "body");
        const card = el("div", "card");
        card.append(badge(a), el("p", "name", esc(a.name)));
        const line = a.status || a.tagline || (!d.pinned && d.hint && !showingAll ? d.hint : "");
        if (line) card.append(el("p", "status" + (a.tone === "attention" ? " attn" : ""), esc(line)));
        body.append(card);
        parts.push(kicker(where, (appIndex + 1) + " / " + list.length), body,
          hint(a.id === "__all" ? "browse" : a.id === "__back" ? "go back" : "open"));
      }
    } else if (view === "menu") {
      const rows = menuRows(a);
      const body = el("div", "body");
      body.append(...rowsOf(rows, row));
      parts.push(kicker(a.name), body, hint(rows[row] && rows[row].back ? "go back" : "choose"));
    } else if (view === "panel" && isCarousel()) {
      const item = (a.menu || [])[menuIndexOf()] || {};
      const rows = panelRows(), r = rows[row];
      const body = el("div", "body");
      if (r.back) body.append(el("div", "card", '<p class="name">Back</p><p class="status">to the Kitchen menu</p>'));
      else {
        const rec = r.line.recipe;
        const card = el("div", "recipe-card");
        card.append(recipePhoto(rec, "photo"), el("p", "r-name", esc(rec.name)));
        if (r.detail) card.append(el("p", "status", esc(r.detail)));
        body.append(card);
      }
      parts.push(kicker(a.name + " · " + (item.label || ""), (row + 1) + " / " + rows.length), body,
        hint(r.back ? "go back" : "open recipe"));
    } else if (view === "recipe") {
      const pages = recipePages(recipe), pg = pages[page];
      const body = el("div", "body");
      if (pg.kind === "cover") {
        const card = el("div", "recipe-card");
        card.append(recipePhoto(recipe, "photo"), el("p", "r-name", esc(recipe.name)));
        card.append(el("p", "status", esc(recipe.ingredients.length + " ingredients · " + recipe.steps.length + " steps")));
        body.append(card);
      } else if (pg.kind === "ingredients") {
        body.append(el("p", "title", "Ingredients"));
        const ul = el("ul", "r-list");
        pg.items.forEach((t) => ul.append(el("li", "", esc(t))));
        body.append(ul);
      } else {
        body.append(el("p", "title", "Step " + pg.n + " Of " + recipe.steps.length), el("p", "r-step" + (pg.text.length > 180 ? " long" : ""), esc(pg.text)));
      }
      parts.push(kicker(recipe.name, (page + 1) + " / " + pages.length), body, hint("back to recipes"));
    } else if (view === "panel") {
      const item = (a.menu || [])[menuIndexOf()] || {};
      const body = el("div", "body");
      const rows = panelRows();
      if (!panel) body.append(el("p", "empty", "…"));
      else {
        if (panel.title && panel.title !== item.label) body.append(el("p", "title", esc(panel.title)));
        if (!panel.lines.length) body.append(el("p", "empty", esc(panel.empty || "Nothing here.")));
        else if (rows.length === (sorts() ? 2 : 1)) body.append(el("p", "empty", "Nothing here."));
        body.append(...rowsOf(rows, row));
        if (panel.more) body.append(el("p", "more", "+ " + panel.more + " more on your phone"));
      }
      const r = rows[row] || BACK_ROW;
      const line = r.line;
      parts.push(kicker(a.name + " · " + (item.label || "")), body,
        hint(r.back ? "go back" : r.kind === "sort" ? "change sort" : line && (line.action || line.pick) ? (line.action || line.pick).label : "—"));
    } else if (view === "confirm") {
      const body = el("div", "body");
      body.append(el("p", "say", esc(proposal ? proposal.summary : "")));
      body.append(...rowsOf([{ text: "Approve", verb: "✓" }, { text: "Cancel", kind: "cancel" }], row));
      parts.push(kicker("Confirm"), body, hint(row === 0 ? "approve" : "cancel"));
    } else if (view === "result") {
      const body = el("div", "body");
      body.append(el("p", "say small", esc(resultText)));
      parts.push(kicker(a ? a.name : "MIA"), body, hint("continue"));
    } else if (view === "reward") {
      parts.push(rewardScreen(reward), hint("continue"));
    }
    screen.replaceChildren(...parts);
  }

  // The reward (Zac's concept, 2026-10-16): "Objective Complete ☆ +30 XP
  // ✓ Quest Complete" in a HUD frame. From the engine's proposal.reward
  // (core/actions.reward_for); the XP counts up, then select continues.
  function rewardScreen(r) {
    const box = el("div", "reward" + (r.level_up ? " level-up" : ""));
    ["tl", "tr", "bl", "br"].forEach((c) => box.append(el("i", "rc " + c)));
    box.append(el("p", "r-head", esc(r.headline)), el("p", "r-star", "☆"));
    const big = r.xp ? "+" + r.xp + " XP" : r.credits ? "+" + r.credits + " Credits" : "✓";
    const amount = el("p", "r-xp", esc(big));
    box.append(amount);
    if (r.xp) {  // count up
      const start = performance.now(), total = r.xp;
      const step = (now) => {
        const t = Math.min(1, (now - start) / 900);
        amount.textContent = "+" + Math.round(total * (1 - Math.pow(1 - t, 3))) + " XP";
        if (t < 1 && view === "reward") requestAnimationFrame(step);
      };
      amount.textContent = "+0 XP";
      requestAnimationFrame(step);
    }
    const label = r.headline === "Mission Complete" ? "Quest Complete" : r.ready ? "All Objectives Done · Claim It"
      : r.total ? r.done + " / " + r.total + " Objectives" : r.headline;
    const pct = r.headline === "Mission Complete" || r.ready ? 100 : r.total ? Math.round(100 * r.done / r.total) : 100;
    const bar = el("div", "r-bar");
    const fill = el("span", "r-fill");
    fill.style.width = pct + "%";
    bar.append(fill, el("span", "r-label", "✓ " + esc(label)));
    box.append(bar);
    const sub = [r.name && r.name !== r.headline ? r.name : null, r.credits && r.xp ? "+" + r.credits + " credits" : null,
      r.level_up ? "Level " + r.level + "!" : null].filter(Boolean).join(" · ");
    if (sub) box.append(el("p", "r-sub", esc(sub)));
    return box;
  }

  function missionCard(m) {
    const body = el("div", "body");
    const box = el("div", "mission");
    if (!m) {
      box.append(el("p", "m-name", "No active mission"), el("p", "m-more", "Start one on your phone or ask MIA."));
    } else {
      box.append(el("p", "m-name", esc((m.icon ? m.icon + " " : "") + m.name)));
      const objs = el("ul", "m-objs");
      const shown = m.objectives.length > 4 ? 3 : 4;
      m.objectives.slice(0, shown).forEach((o) => {
        const li = el("li", o.done ? "done" : "");
        li.append(el("i", "box", o.done ? "✓" : ""), el("span", "", esc(o.text)));
        if (!o.done && o.target && o.target !== 1) li.append(el("em", "", (o.progress || 0) + "/" + o.target));
        objs.append(li);
      });
      box.append(objs);
      if (m.objectives.length > shown) box.append(el("p", "m-more", "+ " + (m.objectives.length - shown) + " more objectives"));
      const pct = m.total ? Math.round(100 * m.done / m.total) : 0;
      box.append(el("div", "m-bar", '<i style="width:' + pct + '%"></i>'));
    }
    box.append(el("div", "m-button", "Select Mission"));
    body.append(box);
    return body;
  }

  // ------------------------------------------------------------ the two moves (and back)
  let menuIndex = 0;
  function menuIndexOf() { return menuIndex; }

  function move(dir) {
    if (busy) return;
    if (view === "home") {
      if (voiceState === "listening" || voiceState === "thinking") stopListening();
      const list = cards();
      if (!list.length) {  // the apps didn't load (a bad connection, a half-updated page): try again
        load().then(() => {
          if (cards().length) move(dir);
          else answer("MIA couldn't load your apps. Check the connection and try again.", 5);
        });
        return;
      }
      appIndex = dir > 0 ? 0 : list.length - 1;
      show("cards");
      return;
    }
    if (view === "cards") {
      const n = cards().length;
      const next = appIndex + dir;
      if (!showingAll && (next < 0 || next >= n)) { show("home"); return; }  // the orb sits between the ends
      appIndex = (next + n) % n;
      render();
      return;
    }
    if (view === "recipe") {
      const n = recipePages(recipe).length;
      page = Math.max(0, Math.min(n - 1, page + dir)); render(); return;
    }
    const count = view === "menu" ? menuRows(app()).length : view === "panel" ? (panel ? panelRows().length : 0)
      : view === "confirm" ? 2 : 0;
    if (count) { row = (row + dir + count) % count; render(); }
  }

  async function select() {
    if (busy) return;
    busy = true;
    try { await doSelect(); } finally { busy = false; }
  }
  async function doSelect() {
    const a = app();
    if (view === "home") { listen(); return; }
    if (view === "cards") {
      if (!a) return;
      if (a.id === "__all") { showingAll = true; appIndex = 0; render(); return; }
      if (a.id === "__back") { showingAll = false; appIndex = Math.max(0, cards().length - 1); render(); return; }
      menuIndex = 0; row = 0; show("menu");
      return;
    }
    if (view === "menu") {
      const rows = menuRows(a);
      if (rows[row].back) { row = 0; show("cards"); return; }
      menuIndex = row;
      const item = a.menu[row];
      if (item.type === "ask") {
        resultText = "…"; after = "menu"; show("result");
        try { const turn = await MIA.talk(item.say); resultText = turn.reply_text || "Done."; }
        catch (err) { resultText = err.message; }
        render();
        return;
      }
      if (item.type === "action") { await propose(item.action, "reload"); return; }
      await openPanel();
      return;
    }
    if (view === "recipe") { row = Math.max(0, row); show("panel"); return; }
    if (view === "panel") {
      if (!panel) return;
      const rows = panelRows();
      if (rows[row].back) { row = menuIndex; panel = null; show("menu"); return; }
      if (rows[row].kind === "sort") { sortIndex = (sortIndex + 1) % sorts().length; render(); return; }
      const line = rows[row].line;
      if (line.recipe) { recipe = line.recipe; page = 0; show("recipe"); return; }
      if (line.pick) {  // which mission the Missions card shows
        mission = line.pick.mission; store.set("mia.glasses.mission", mission);
        await load();
        const at = cards().findIndex((c) => c.id === "missions");
        if (at >= 0) appIndex = at;
        panel = null; row = 0; show("cards");
        return;
      }
      if (line.action) await propose(line.action, "panel");
      return;
    }
    if (view === "confirm") {
      if (row === 1) { cancel(); return; }
      try {
        const done = await MIA.approve(proposal.proposal_id);
        resultText = done.result || done.summary || "Done.";
        if (done.status === "executed" && done.reward) {
          reward = done.reward; proposal = null; show("reward");
          if (window.MIASound) MIASound.celebrate(reward);  // a quest-complete chime on the glasses (DEC-0028 #11)
          clearTimeout(rewardTimer);
          rewardTimer = setTimeout(() => { if (view === "reward") leaveResult(); }, 6000);
          return;
        }
      } catch (err) { resultText = err.message; }
      proposal = null; show("result");
      return;
    }
    if (view === "result" || view === "reward") { clearTimeout(rewardTimer); await leaveResult(); }
  }

  async function propose(action, then) {
    try { proposal = await MIA.propose(action.kind, action.params); after = then; row = 0; show("confirm"); }
    catch (err) { resultText = err.message; after = then === "reload" ? "menu" : "panel"; show("result"); }
  }
  function cancel() {
    if (proposal) MIA.reject(proposal.proposal_id).catch(() => {});
    proposal = null;
    if (after === "reload") { row = menuIndex; show("menu"); } else { row = 0; show("panel"); }
  }
  async function openPanel() {
    const a = app(), item = a && a.menu[menuIndex];
    panel = null; row = 0; sortIndex = 0; show("panel");
    try { panel = await MIA.glassesPanel(a.id, item.id, mission); }
    catch (err) { panel = { lines: [], empty: err.message, more: 0 }; }
    row = 0;
    if (view === "panel") render();
  }
  async function leaveResult() {
    if (after === "panel") { await load(); await openPanel(); return; }
    if (after === "reload") {  // pins changed: re-read the cards, stay with this app
      const id = (app() || {}).id;
      await load();
      const d = data || {};
      showingAll = !!d.pinned && !(d.apps || []).some((c) => c.id === id);
      const at = cards().findIndex((c) => c.id === id);
      appIndex = at >= 0 ? at : 0; row = 0; show("cards");
      return;
    }
    row = menuIndex; show("menu");
  }

  function back() {
    if (busy) return;
    if (view === "home") { if (voiceState === "answered") orbState("idle"); return; }
    if (view === "confirm") { cancel(); return; }
    if (view === "result" || view === "reward") { clearTimeout(rewardTimer); leaveResult(); return; }
    if (view === "recipe") { show("panel"); return; }
    if (view === "panel") { row = menuIndex; panel = null; show("menu"); return; }
    if (view === "menu") { row = 0; show("cards"); return; }
    if (showingAll) { showingAll = false; appIndex = Math.max(0, cards().length - 1); render(); return; }
    show("home");
  }

  // ------------------------------------------------------------ input
  document.addEventListener("keydown", (e) => {
    const k = e.key;
    if (k === "ArrowRight" || k === "ArrowDown") { e.preventDefault(); move(1); }
    else if (k === "ArrowLeft" || k === "ArrowUp") { e.preventDefault(); move(-1); }
    else if (k === "Enter" || k === " ") { e.preventDefault(); select(); }
    else if (k === "Escape" || k === "Backspace") { e.preventDefault(); back(); }
  });
  // Touch and mouse: each gesture is either a tap (select; a tapped row is
  // chosen first; an edge arrow moves) or a swipe (left/right/up move,
  // down goes back). Decided on release, so no tap is ever lost.
  let px = null, py = null;
  addEventListener("pointerdown", (e) => { px = e.clientX; py = e.clientY; });
  addEventListener("pointerup", (e) => {
    if (px == null) return;
    const dx = e.clientX - px, dy = e.clientY - py;
    px = py = null;
    if (Math.max(Math.abs(dx), Math.abs(dy)) >= 40) {
      if (Math.abs(dx) >= Math.abs(dy)) move(dx < 0 ? 1 : -1);
      else if (dy > 0) back();
      else move(1);
      return;
    }
    const target = e.target instanceof Element ? e.target : null;
    if (target && target.closest("#prev")) { move(-1); return; }
    if (target && target.closest("#next")) { move(1); return; }
    const li = target && target.closest("li[data-row]");
    if (li) row = Number(li.dataset.row);
    select();
  });
  addEventListener("pointercancel", () => { px = py = null; });
  addEventListener("dblclick", (e) => e.preventDefault());

  // ------------------------------------------------------------ boot: her orb
  (async () => {
    await load();
    show("home");
  })();
})();
