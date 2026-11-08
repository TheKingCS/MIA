/*
 * shell.js — the frame every MIA web screen shares (claude, 2026-10-06, DEC-0017).
 *
 * Function first; the look is Muse's (components.css). Gives each page:
 *   - sign-in when nobody is signed in on this tab;
 *   - the sidebar: the person's own apps from the engine (MIA.shell(): child-safe,
 *     tucked-away apps hidden), the current page highlighted, level and XP at the
 *     bottom, and how many apps are still only in the PC app;
 *   - MIA, everywhere: the orb button opens a Talk panel (MIA.talk), typed or
 *     spoken: its mic records here and sends MIA.voice, and her answer is said
 *     back (DEC-0125: full use by voice on every device, the PC included);
 *   - MIAShell.act(action): the one way a screen changes anything —
 *     propose → the engine's sentence in a confirm → approve → undo toast;
 *   - where you were: the scroll, an open Talk and its half-typed message,
 *     back when the page reopens (after the phone locks, 2026-11-07).
 *
 * A page:  <body data-app="garage"> ... <script src="mia.js"></script>
 *          <script src="shell.js"></script>
 *          MIAShell.start(async () => { ...render...; }, { refreshOnChange: true });
 * No logic about the person's life here: everything shown comes from the engine.
 */
(function () {
  "use strict";

  // ---------------------------------------------------------------- the theme (DEC-0136, core/themes.py)
  // A theme is data: tokens set on the page (every stylesheet follows), a material (themes.css) and the room's light
  // (web/nexus3d.js). It comes with the shell on every page; the last one is kept on this device so the next page
  // opens already themed, before the shell arrives. Meaning colours aren't tokens a theme can set (core checks).
  const THEME_CACHE = "mia.theme";
  let themeApplied = [];
  let themeNow = null;
  function applyTheme(theme) {
    if (!theme || !theme.id) return;
    const root = document.documentElement;
    themeApplied.forEach((k) => root.style.removeProperty(k));
    themeApplied = [];
    Object.entries(theme.tokens || {}).forEach(([k, v]) => {
      if (k.startsWith("--")) { root.style.setProperty(k, v); themeApplied.push(k); }
    });
    root.dataset.theme = theme.id;
    root.dataset.material = theme.material || "solid";
    themeNow = theme;
    try { localStorage.setItem(THEME_CACHE, JSON.stringify(theme)); } catch (e) { /* fine: it applies when the shell comes */ }
  }
  try { applyTheme(JSON.parse(localStorage.getItem(THEME_CACHE) || "null")); } catch (e) { /* no cached theme */ }
  function theme() { return themeNow || { id: "stark", name: "Stark", tokens: {}, material: "solid", room: {} }; }

  const $ = (sel, root) => (root || document).querySelector(sel);

  function el(tag, attrs, ...children) {
    const node = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs || {})) {
      if (v == null || v === false) continue;
      if (k === "class") node.className = v;
      else if (k.startsWith("on")) node.addEventListener(k.slice(2), v);
      else node.setAttribute(k, v === true ? "" : v);
    }
    for (const c of children.flat()) {
      if (c == null || c === false) continue;
      node.append(c instanceof Node ? c : document.createTextNode(String(c)));
    }
    return node;
  }

  // ---------------------------------------------------------------- status + undo
  let statusTimer = null;
  function say(text, undo) {
    let line = $("#mia-status");
    if (!line) {
      line = el("div", { id: "mia-status", class: "status-line", role: "status", "aria-live": "polite" });
      document.body.append(line);
    }
    line.replaceChildren(text || "");
    if (undo) line.append(" ", el("button", { type: "button", onclick: undo }, "Undo"));
    line.hidden = !text;
    clearTimeout(statusTimer);
    if (text) statusTimer = setTimeout(() => { line.hidden = true; }, undo ? 9000 : 5000);
  }

  // ---------------------------------------------------------------- confirm
  function confirmBox(summary) {
    return new Promise((resolve) => {
      let dialog = $("#mia-confirm");
      if (!dialog) {
        dialog = el("dialog", { id: "mia-confirm", class: "confirm", "aria-labelledby": "mia-confirm-text" },
          el("p", { id: "mia-confirm-text" }),
          el("div", { class: "confirm-actions" },
            el("button", { type: "button", class: "btn btn-ghost", id: "mia-confirm-no" }, "Not now"),
            el("button", { type: "button", class: "btn btn-green", id: "mia-confirm-yes" }, "Yes, do it")));
        document.body.append(dialog);
      }
      $("#mia-confirm-text").textContent = summary;
      const done = (answer) => { dialog.close(); resolve(answer); };
      $("#mia-confirm-yes").onclick = () => done(true);
      $("#mia-confirm-no").onclick = () => done(false);
      dialog.oncancel = (e) => { e.preventDefault(); done(false); };
      dialog.showModal();
      $("#mia-confirm-yes").focus();
    });
  }

  /**
   * Propose → confirm → approve → undo toast. Returns the executed proposal, or null.
   * `opts.quick` (a tap at the market stand, DEC-0036): pressing the button is the
   * approval, so no confirm box; the toast says what was done, with Undo.
   */
  async function act(action, opts) {
    if (!action) return null;
    try {
      const proposal = await MIA.propose(action.kind, action.params);
      if (!(opts && opts.quick) && !(await confirmBox(proposal.summary))) {
        MIA.reject(proposal.proposal_id).catch(() => {});
        return null;
      }
      const done = await MIA.approve(proposal.proposal_id);
      if (window.MIASound && done.status === "executed") MIASound.celebrate(done.reward);  // DEC-0028 #11
      say((opts && opts.quick ? proposal.summary + "." : done.result) || "Done.", done.undoable ? async () => {
        try { await MIA.undo(done.proposal_id); say("Undone."); refresh(); } catch (e) { say(e.message); }
      } : null);
      refresh();
      return done;
    } catch (e) {
      say(e.message);
      return null;
    }
  }

  // ---------------------------------------------------------------- forms
  /**
   * Ask for values with the engine's own field list ({name, label, type,
   * required, options, default}; types: text, textarea, money, rate, int,
   * amount, number, date, choice, recurrence, asset — `extra.assets` lists
   * [{id, name}] for that one). Resolves to {name: value} or null if cancelled.
   * Checking the values is the engine's job (the proposal says what's wrong).
   */
  function form(title, fields, values, extra) {
    values = values || {};
    extra = extra || {};
    return new Promise((resolve) => {
      const inputs = {};
      const row = (f) => {
        const id = "f-" + f.name;
        const value = values[f.name] != null ? values[f.name] : (f.default != null ? f.default : "");
        let input;
        if (f.type === "asset" || f.type === "pick") {
          const list = f.type === "asset" ? (extra.assets || []) : (extra[f.options[0]] || []);
          input = el("select", { id, required: f.required || null },
            f.required ? null : el("option", { value: "" }, "—"),
            list.map((a) => el("option", { value: a.id, selected: String(value) === a.id ? true : null }, a.name)));
        } else if (f.type === "choice" || f.type === "recurrence") {
          input = el("select", { id },
            f.options.map((o) => el("option", { value: o, selected: String(value || "none") === o ? true : null },
              o === "none" ? "Doesn't repeat" : o)));
        } else if (f.type === "textarea") {
          input = el("textarea", { id, rows: "2" });
          input.value = value;
        } else {
          const numeric = ["money", "rate", "int", "amount", "number"].includes(f.type);
          const type = f.type === "date" ? "date" : f.type === "password" ? "password" : numeric ? "number" : "text";
          input = el("input", { id, type, step: f.type === "int" ? "1" : numeric ? "any" : null,
            min: numeric && f.type !== "number" ? "0" : null,
            inputmode: type === "number" ? "decimal" : null, required: f.required || null });
          input.value = value;
        }
        inputs[f.name] = input;
        return el("label", { class: "form-row", for: id }, el("span", {}, f.label + (f.required ? "" : " (optional)")), input);
      };
      const dialog = el("dialog", { class: "confirm form-dialog", "aria-label": title });
      const done = (answer) => { dialog.close(); dialog.remove(); resolve(answer); };
      dialog.append(el("form", { method: "dialog", onsubmit: (e) => {
        e.preventDefault();
        const out = {};
        for (const [name, input] of Object.entries(inputs)) out[name] = input.value;
        done(out);
      } },
        el("h3", {}, title),
        ...fields.map(row),
        el("div", { class: "confirm-actions" },
          el("button", { type: "button", class: "btn btn-ghost", onclick: () => done(null) }, "Cancel"),
          el("button", { type: "submit", class: "btn btn-green" }, "Next"))));
      dialog.oncancel = (e) => { e.preventDefault(); done(null); };
      document.body.append(dialog);
      dialog.showModal();
      const first = dialog.querySelector("input, select, textarea");
      if (first) first.focus();
    });
  }

  // ---------------------------------------------------------------- navigation
  // Desktop: the concept's sidebar. Phones: the bottom bar (Home, Apps,
  // Dashboard). No More menu: every app is on the Apps page (Zac, 2026-10-06).
  function levelBlock(p) {
    const pct = p.xp_for_level ? Math.round((100 * p.xp_into_level) / p.xp_for_level) : 0;
    return el("div", { class: "nav-level" },
      el("div", { class: "side-level" },
        el("span", { class: "side-level-n" }, "lvl " + p.level),
        el("span", { class: "side-level-xp" }, p.total_xp + " XP")),
      el("div", { class: "xpbar" }, el("div", { class: "xpbar-track" },
        el("div", { class: "xpbar-fill", style: "width:" + pct + "%" }))));
  }

  /** The concept's level card (avatar, level, XP bar) from a page's `me`
   *  (core.web_progress.level_block); its prestige color shows once earned. */
  function levelCard(node, me) {
    if (!node || !me) return;
    const pct = me.xp_for_level ? Math.round((100 * me.xp_into_level) / me.xp_for_level) : 0;
    node.className = "glass home-level page-level" + (me.prestige_color ? " prestige-" + me.prestige_color : "");
    node.replaceChildren(
      el("span", { class: "home-avatar", "aria-hidden": "true" }, "🧙"),
      el("span", { class: "home-level-text" }, el("strong", {}, "lvl " + me.level + (me.prestige_tier ? " · P" + me.prestige_tier : "")),
        el("small", {}, me.xp_into_level.toLocaleString() + " / " + me.xp_for_level.toLocaleString() + " XP · " + me.credits + " credits")),
      el("span", { class: "xpbar" }, el("span", { class: "xpbar-track" }, el("span", { class: "xpbar-fill", style: "width:" + pct + "%" }))));
  }

  /** The app's line icon (web/icons.js, DEC-0023), or its emoji where there's none. */
  function icon(id, fallback) {
    return (window.MIAIcons && MIAIcons.svg(id)) || fallback || "";
  }

  // The sidebar grouped (Zac, 2026-11-07: a flat list of 46 apps hid what's new): Start Here, the favorites, then
  // each life area as a heading that opens and closes (the one with this page open; what you open is remembered).
  function groupedApps(shell, cls, here) {
    const link = (a) => el("a", { class: cls, href: a.page, "aria-current": a.id === here ? "page" : null },
      el("span", { class: "ico", "aria-hidden": "true" }, icon(a.id, a.icon)), el("span", { class: "label" }, a.name));
    const out = [el("a", { class: cls + " side-start", href: "start.html", "aria-current": here === "start" ? "page" : null },
      el("span", { class: "ico", "aria-hidden": "true" }, "?"), el("span", { class: "label" }, "Start Here"))];
    const home = shell.apps.find((a) => a.id === "web_home");
    if (home) out.push(link(home));
    const favorites = (shell.favorites || []).map((id) => shell.apps.find((a) => a.id === id)).filter(Boolean);
    if (favorites.length) out.push(el("p", { class: "side-heading" }, "Favorites"), ...favorites.map(link));
    for (const group of shell.groups || []) {
      const apps = shell.apps.filter((a) => a.group === group && a.id !== "web_home");
      if (!apps.length) continue;
      const key = "mia.side." + group;
      let open = apps.some((a) => a.id === here);
      try { open = open || localStorage.getItem(key) === "1"; } catch (e) { /* no storage */ }
      const box = el("details", { class: "side-group", open: open || null },
        el("summary", {}, group + " (" + apps.length + ")"), ...apps.map(link));
      box.addEventListener("toggle", () => { try { localStorage.setItem(key, box.open ? "1" : "0"); } catch (e) { /* fine */ } });
      out.push(box);
    }
    return out;
  }

  function appLinks(shell, cls) {
    const here = document.body.dataset.app || "web_home";
    const made = new URLSearchParams(location.search).get("id");
    const apps = shell.groups ? groupedApps(shell, cls, here)
      : shell.apps.map((a) => el("a", { class: cls, href: a.page, "aria-current": a.id === here ? "page" : null },
        el("span", { class: "ico", "aria-hidden": "true" }, icon(a.id, a.icon)), el("span", { class: "label" }, a.name)));
    // What MIA made for this person (core/creations.py, DEC-0091) follows the apps, drawn the same way.
    return apps
      .concat((shell.made || []).map((m) => el("a", { class: cls, href: m.page,
        "aria-current": here === "made" && made === m.id ? "page" : null },
        el("span", { class: "ico", "aria-hidden": "true" }, icon(m.icon, "✦")), el("span", { class: "label" }, m.name))))
      // Pages only the PC's owner has (the council, build plan step 16).
      .concat((shell.owner || []).map((o) => el("a", { class: cls, href: o.page,
        "aria-current": document.body.classList.contains("mod-" + o.id) ? "page" : null },
        el("span", { class: "ico", "aria-hidden": "true" }, icon(o.icon, "✦")), el("span", { class: "label" }, o.name))))
      .concat(shell.person && shell.person.child ? [] : [el("a", { class: cls, href: "made.html",  // ask her for one
        "aria-current": here === "made" && !made ? "page" : null },
        el("span", { class: "ico", "aria-hidden": "true" }, "＋"), el("span", { class: "label" }, "Make Something"))]);
  }

  /** The sidebar as the canvas draws it (DEC-0113): Home and Apps, the person's Pinned apps, then each life area
   *  folded (the one you're in opens), then what MIA made, the owner's pages and Make Something. Every app stays one
   *  click away, as DEC-0045 asks; the groups only stop the list being a wall. */
  function sideLinks(shell) {
    const here = document.body.dataset.app || "web_home";
    const link = (a) => el("a", { class: "nav", href: a.page, "aria-current": a.id === here ? "page" : null },
      el("span", { class: "ico", "aria-hidden": "true" }, icon(a.id, icon(a.icon, a.icon))), el("span", { class: "label" }, a.name));
    const byId = Object.fromEntries(shell.apps.map((a) => [a.id, a]));
    const out = [];
    // Spatial (DEC-0135): the Nexus first (DEC-0130), then Today (the Dashboard, DEC-0129). Cards: Home (the
    // Dashboard) first, the Nexus after it. Then Start Here and Apps.
    const nexus = link({ id: "nexus", name: "Nexus", icon: "mia", page: "nexus.html" });
    if (look() === "cards") {
      if (byId.web_home) out.push(link({ ...byId.web_home, name: "Home", page: "index.html" }));
      out.push(nexus);
    } else {
      out.push(nexus);
      if (byId.web_home) out.push(link({ ...byId.web_home, name: "Today", page: "index.html?today=1" }));
    }
    out.push(el("a", { class: "nav side-start", href: "start.html", "aria-current": here === "start" ? "page" : null },
      el("span", { class: "ico", "aria-hidden": "true" }, "?"), el("span", { class: "label" }, "Start Here")));
    const pinned = (shell.favorites || []).map((id) => byId[id]).filter((a) => a && a.id !== "web_home");
    if (pinned.length) out.push(el("div", { class: "side-section" }, el("span", { class: "side-head" }, "Pinned"), ...pinned.map(link)));
    // The areas (core/web_areas.py): each opens its hub; the one this page belongs to also lists its apps under it.
    const params = new URLSearchParams(location.search);
    const hubHere = location.pathname.endsWith("hub.html") ? params.get("area") : null;
    const page = location.pathname.split("/").pop() + location.search;
    const areas = shell.areas || [];
    const mine = hubHere || (areas.find((a) => a.members.some((m) => m.id === here || m.page === page)) || {}).id;
    if (areas.length) {
      out.push(el("span", { class: "side-head side-areas-head" }, "Areas"));
      areas.forEach((area) => {
        const open = area.id === mine;
        out.push(el("a", { class: "nav side-area" + (open ? " open" : ""), href: area.page, "aria-current": hubHere === area.id ? "page" : null,
          "aria-expanded": String(open) },
          el("span", { class: "ico", "aria-hidden": "true" }, icon(area.icon, "•")), el("span", { class: "label" }, area.name)));
        if (open) out.push(el("div", { class: "side-area-apps" }, area.members.map((m) => el("a", { class: "nav nav-sub", href: m.page,
          "aria-current": m.id === here || m.page === page ? "page" : null }, el("span", { class: "label" }, m.name)))));
      });
    } else {
      out.push(...shell.apps.filter((a) => a.id !== "web_home").map(link));  // older engine: no areas
    }
    // What MIA made, the owner's pages and Make Something keep their place at the end (no groups: just those).
    return out.concat(appLinks({ ...shell, apps: [], groups: null }, "nav"));
  }

  function more(shell) {
    return shell.on_pc_only.length
      ? el("a", { class: "side-more", href: "apps.html", title: shell.on_pc_only.join(", ") },
        shell.on_pc_only.length + " more apps in the PC app for now")
      : null;
  }

  // The person's look (DEC-0135, core/display_style.py): "spatial" (the Nexus and rooms) or "cards" (the Dashboard
  // and cards). "auto" is decided here, since only the page knows it's on a phone.
  const onPhone = () => !!(window.matchMedia && matchMedia("(max-width: 760px)").matches);
  function look() {
    const style = (shellData && shellData.display && shellData.display.style) || "auto";
    return style === "spatial" || style === "cards" ? style : onPhone() ? "cards" : "spatial";
  }

  function renderNav(shell) {
    shellData = shell;
    if (shell.display && shell.display.theme) applyTheme(shell.display.theme);
    document.body.classList.toggle("look-spatial", look() === "spatial");
    document.body.classList.toggle("look-cards", look() === "cards");
    if (window.MIASound) MIASound.configure(shell.sound);
    if (window.MIAPlaces) MIAPlaces.configure(shell.places);  // location quests, checked on this device
    const layout = $(".layout");
    document.body.classList.toggle("has-side", Boolean(layout));
    if (layout) {
      let side = $("nav.side");
      if (!side) {
        side = el("nav", { class: "side", "aria-label": "Apps" });
        layout.prepend(side);
      }
      side.replaceChildren(
        el("a", { class: "brand", href: "index.html" }, el("span", { class: "brand-mark brand-reactor", "aria-hidden": "true" }),
          el("span", {}, "MIA", el("small", {}, "Your Life. In Sync."))),
        el("button", { type: "button", class: "side-search", onclick: () => openSearch(), "aria-keyshortcuts": "Control+K" },
          el("span", {}, "Search"), el("kbd", {}, "Ctrl K")),
        ...sideLinks(shell),
        el("div", { class: "side-foot" }, levelBlock(shell.person), more(shell)));
    }
    // Phone: the concept's bottom bar.
    let bar = $("#mia-bottom-bar");
    if (!bar) {
      bar = el("nav", { id: "mia-bottom-bar", class: "bottom-bar", "aria-label": "Main" });
      document.body.append(bar);
    }
    const here = document.body.dataset.app || "web_home";
    const tab = (href, id, glyph, emoji, label) => el("a", { href, "aria-current": here === id ? "page" : null },
      el("span", { class: "ico", "aria-hidden": "true" }, icon(glyph, emoji)), label);
    const cards = look() === "cards";  // DEC-0135: the cards look's first tab is Home, the spatial look's the Nexus
    bar.replaceChildren(
      cards ? tab("index.html", "web_home", "home", "🏠", "Home") : tab("nexus.html", "nexus", "home", "🏠", "Nexus"),
      cards ? tab("nexus.html", "nexus", "mia", "◎", "Nexus") : tab("index.html?today=1", "web_home", "calendar", "📅", "Today"),
      tab("apps.html", "module_browser", "apps", "▦", "Apps"),
      el("button", { type: "button", class: "bottom-search", onclick: () => openSearch() },
        el("span", { class: "ico", "aria-hidden": "true" }, icon("search", "⌕")), "Search"));
  }

  // ---------------------------------------------------------------- MIA, everywhere
  // Speaking to her (DEC-0125): the browser records, and it's turned into the mono 16 kHz 16-bit WAV her voice
  // path expects (/api/voice/turn). Shared by Talk and the Assistant page.
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
    source.buffer = audio;
    source.connect(offline.destination);
    source.start();
    return wav((await offline.startRendering()).getChannelData(0), rate);
  }

  /** A recorder: start() asks for the microphone and records; stop() resolves to the WAV. Throws a sentence when
   * this browser can't record or the microphone isn't allowed. */
  function voiceRecorder() {
    let recorder = null, stream = null, chunks = [];
    return {
      get recording() { return !!recorder && recorder.state === "recording"; },
      async start() {
        if (!navigator.mediaDevices || !window.MediaRecorder) {
          throw new Error("This browser can't record here. Voice works in MIA's phone app and on the PC.");
        }
        try { stream = await navigator.mediaDevices.getUserMedia({ audio: true }); }
        catch (e) {
          throw new Error(window.isSecureContext ? "MIA needs permission to use the microphone."
            : "The browser only allows the microphone on a secure address. Voice works in MIA's phone app and on the PC.");
        }
        chunks = [];
        recorder = new MediaRecorder(stream);
        recorder.ondataavailable = (e) => chunks.push(e.data);
        recorder.start();
      },
      stop() {
        return new Promise((resolve, reject) => {
          if (!recorder) { reject(new Error("Not recording.")); return; }
          recorder.onstop = async () => {
            stream.getTracks().forEach((t) => t.stop());
            recorder = null;
            try { resolve(await toWav(new Blob(chunks))); } catch (e) { reject(e); }
          };
          recorder.stop();
        });
      },
    };
  }

  /** Her spoken reply, when her computer has a voice. */
  function playReply(turn) {
    if (turn && turn.audio_wav_base64) new Audio("data:audio/wav;base64," + turn.audio_wav_base64).play().catch(() => {});
  }

  function mountTalk() {
    if ($("#mia-orb")) return;
    const log = el("div", { class: "talk-log", id: "talk-log", "aria-live": "polite" });
    const input = el("input", { id: "talk-input", placeholder: "Talk to MIA…", autocomplete: "off", "aria-label": "Message MIA" });
    // One turn, typed or spoken: her reply in the log, what she used, which brain answered, and 👍/👎.
    async function answer(asked, run) {
      const thinking = el("p", { class: "bubble mia thinking" }, "…");
      log.append(thinking);
      log.scrollTop = log.scrollHeight;
      try {
        const turn = await run();
        if (turn.transcript) thinking.before(el("p", { class: "bubble me" }, turn.transcript));  // what she heard
        thinking.textContent = turn.reply_text || "Done.";
        playReply(turn);
        if (turn.open) setTimeout(() => { location.href = turn.open; }, 900);  // e.g. show-off mode's tour
        const used = usedList(turn.used);
        if (used) thinking.after(used);
        // Which brain answered (DEC-0022): the home computer's model or this device's.
        if (turn.level) thinking.append(el("small", { class: "talk-level", title: "Answered by the model on " + turn.level.toLowerCase() }, turn.level));
        thinking.append(notRight(asked || turn.transcript || "", turn.reply_text));
        refresh();
      } catch (err) {
        thinking.textContent = err.message;
      }
      thinking.classList.remove("thinking");
      log.scrollTop = log.scrollHeight;
    }
    // The mic: tap to talk, tap again when done (DEC-0125).
    const recorder = voiceRecorder();
    const mic = el("button", { type: "button", class: "btn btn-ghost chat-mic talk-mic", "aria-label": "Speak to MIA",
      title: "Speak to MIA (tap again when you're done)", onclick: async () => {
        if (recorder.recording) {
          mic.classList.remove("listening");
          mic.setAttribute("aria-label", "Speak to MIA");
          let audio;
          try { audio = await recorder.stop(); } catch (e) { say(e.message); return; }
          await answer("", () => MIA.voice(audio));
          return;
        }
        try { await recorder.start(); } catch (e) { say(e.message); return; }
        mic.classList.add("listening");
        mic.setAttribute("aria-label", "Done speaking");
      } });
    mic.append(icon("mic", "🎙"));
    // Look, from the chat (DEC-0129: "you access Look through the same screen as having a chat"): a photo from the
    // camera or the files, asked about with what's typed (or "What is this?"), answered by the PC's vision model
    // (core/sight.py, /api/sight). The photo shows in this chat only; it isn't kept.
    const look = el("button", { type: "button", class: "btn btn-ghost chat-mic talk-look", "aria-label": "Look: show MIA a photo",
      title: "Show MIA something (a photo, from the camera or your files)", onclick: () => {
        const pick = el("input", { type: "file", hidden: true, accept: "image/*", capture: "environment" });
        pick.addEventListener("change", async () => {
          const file = pick.files && pick.files[0];
          pick.remove();
          if (!file) return;
          const question = input.value.trim() || "What is this?";
          input.value = "";
          const url = URL.createObjectURL(file);
          log.append(el("div", { class: "bubble me talk-photo" }, el("img", { src: url, alt: "Your photo" }), el("span", {}, question)));
          await answer(question, async () => {
            const got = await MIA.upload("/api/sight", file, { "X-Question": encodeURIComponent(question) });
            return { reply_text: got.said || "I couldn't make that out." };
          });
        });
        document.body.append(pick);
        pick.click();
      } });
    look.append(icon("sight", "👁"));
    const panel = el("aside", { class: "talk-panel glass glow", id: "talk-panel", hidden: true, "aria-label": "Talk to MIA" },
      el("div", { class: "talk-head" }, el("span", { class: "mia-line" }, el("span", { class: "mia-dot" }), "MIA"),
        el("span", { class: "row-buttons" },
          el("button", { type: "button", class: "btn btn-ghost btn-small", onclick: async () => {
            try { await MIA.newChat(); log.replaceChildren(el("p", { class: "dim talk-note" }, "New chat. What's on your mind?")); } catch (e) { say(e.message); }
          } }, "New Chat"),
          el("button", { type: "button", class: "btn btn-ghost", onclick: () => toggleTalk(false) }, "Close"))),
      log,
      el("form", { class: "talk-form", onsubmit: async (e) => {
        e.preventDefault();
        const text = input.value.trim();
        if (!text) return;
        input.value = "";
        log.append(el("p", { class: "bubble me" }, text));
        await answer(text, () => MIA.talk(text));
      } }, input, look, mic, el("button", { class: "btn btn-amber", type: "submit" }, "Send")));
    const orb = el("button", { type: "button", id: "mia-orb", class: "mia-orb-button", "aria-label": "Talk to MIA",
      onclick: () => toggleTalk() }, el("span", { class: "mia-orb-core", "aria-hidden": "true" }));
    document.body.append(panel, orb);
  }

  // Rating her answers (DEC-0067): 👍 or 👎 under a reply, kept as a rating
  // for tuning her voice. A 👎 also goes to the Fix-It Log (DEC-0049), with
  // what was wrong if the person wants to say, and it's fixed from there.
  function notRight(asked, reply) {
    const surface = window.MIAAndroid ? "phone" : "pc";
    const done = (text) => box.replaceWith(el("small", { class: "talk-thumb done" }, text));
    const rate = (rating, note) => act({ kind: "answer.rate", params: { rating, prompt: asked, reply: reply || "", surface, note } },
      { quick: true });
    const up = el("button", { type: "button", class: "talk-thumb", title: "That was right", "aria-label": "That was right" }, "👍");
    up.onclick = async () => { if (await rate("up", "")) done("Thanks ✓"); };
    const down = el("button", { type: "button", class: "talk-thumb", title: "That wasn't right", "aria-label": "That wasn't right" }, "👎");
    down.onclick = async () => {
      const v = await form("What Was Wrong?", [{ name: "note", label: "What should she have done? (optional)", type: "textarea" }], {});
      if (!v) return;
      if (await rate("down", v.note)) done("Logged ✓");
    };
    const box = el("span", { class: "talk-thumbs" }, up, down);
    return box;
  }

  // A page that breaks says so itself (the Fix-It Log), a few times per visit at most.
  let pageErrors = 0;
  function reportPageError(message) {
    if (pageErrors >= 3 || !message || !window.MIA || !MIA.pageError) return;
    pageErrors += 1;
    MIA.pageError(location.pathname.split("/").pop() || "index.html", String(message).slice(0, 300)).catch(() => {});
  }
  window.addEventListener("error", (e) => reportPageError(e.message + (e.filename ? " @" + e.filename.split("/").pop() + ":" + e.lineno : "")));
  window.addEventListener("unhandledrejection", (e) => reportPageError("Unhandled: " + ((e.reason && e.reason.message) || e.reason)));

  // What I Used (DEC-0029): the memories MIA's answer was given, under the
  // reply; each can be fixed or forgotten (memory.fix / memory.forget).
  function usedList(used) {
    if (!used || !used.length) return null;
    return el("details", { class: "talk-used" },
      el("summary", {}, "What I used (" + used.length + ")"),
      el("ul", {}, used.map((m) => {
        const li = el("li", {}, el("span", { class: "talk-used-text" }, m.text),
          el("span", { class: "row-buttons" },
            el("button", { type: "button", class: "btn btn-ghost btn-small", onclick: async () => {
              const v = await form("Fix What MIA Remembers", [{ name: "text", label: "Remember this instead", type: "textarea", required: true }], { text: m.text });
              if (v && await act({ kind: "memory.fix", params: { memory_id: m.id, text: v.text } })) li.querySelector(".talk-used-text").textContent = v.text;
            } }, "Fix"),
            el("button", { type: "button", class: "btn btn-ghost btn-small", onclick: async () => {
              if (await act({ kind: "memory.forget", params: { memory_id: m.id } })) li.classList.add("forgotten");
            } }, "Forget")));
        return li;
      })));
  }

  function toggleTalk(open, prefill, quiet) {
    const panel = $("#talk-panel");
    if (!panel) return;
    const show = open == null ? panel.hidden : open;
    panel.hidden = !show;
    if (show && !panel.dataset.loaded) {
      // The same conversation as the desktop, the phone and the glasses (DEC-0029).
      panel.dataset.loaded = "1";
      MIA.thread().then((t) => {
        const log = $("#talk-log");
        if (!t.messages.length || log.children.length) return;
        log.append(...t.messages.map((m) => el("p", { class: "bubble " + (m.role === "user" ? "me" : "mia") }, m.content)));
        log.scrollTop = log.scrollHeight;
      }).catch(() => {});
    }
    if (show) {
      const input = $("#talk-input");
      if (prefill != null) input.value = prefill;
      if (!quiet) input.focus();  // quiet: reopened where you left it, without popping the keyboard up
    }
  }

  // ---------------------------------------------------------------- where you were (Zac, 2026-11-07)
  // "Remembers where you were so you don't lose your place every time the phone locks": each page keeps how far it
  // was scrolled, whether Talk was open and what was half typed there, in this device's own storage (never the
  // engine), and goes back to it when the page opens again within PLACE_HOURS. The phone app reopens the last page
  // itself (MainActivity.remember); this puts you back inside it.
  const PLACE_KEY = "mia.place." + location.pathname + location.search;
  const PLACE_HOURS = 12;
  function keepPlace() {
    try {
      const panel = $("#talk-panel"), input = $("#talk-input");
      localStorage.setItem(PLACE_KEY, JSON.stringify({ y: Math.round(window.scrollY), talk: !!(panel && !panel.hidden),
        draft: input ? input.value : "", at: Date.now() }));
    } catch (e) { /* no storage here: nothing kept */ }
  }
  function backToPlace() {
    let place = null;
    try { place = JSON.parse(localStorage.getItem(PLACE_KEY) || "null"); } catch (e) { place = null; }
    if (!place || !place.at || Date.now() - place.at > PLACE_HOURS * 3600e3) return;
    if (place.y) requestAnimationFrame(() => window.scrollTo(0, place.y));
    if (place.talk) toggleTalk(true, place.draft || null, true);
  }
  let placeTimer = null;
  window.addEventListener("scroll", () => { clearTimeout(placeTimer); placeTimer = setTimeout(keepPlace, 400); }, { passive: true });
  document.addEventListener("visibilitychange", () => { if (document.hidden) keepPlace(); });
  window.addEventListener("pagehide", keepPlace);

  // ---------------------------------------------------------------- start
  let render = null;
  let refreshing = false;
  async function refresh() {
    if (!render || refreshing) return;
    refreshing = true;
    try { await render(); } catch (e) { say(e.message); } finally { refreshing = false; }
  }

  function signInForm(then) {
    let form = $("#sign-in");
    if (!form) {
      // The design canvas's Sign In (DEC-0113): her orb, the wordmark, labelled boxes, one bright button.
      form = el("form", { class: "sign-in sign-in-canvas", id: "sign-in", "aria-label": "Sign in to MIA" },
        el("div", { class: "si-brand" }, el("span", { class: "si-orb", "aria-hidden": "true" }), el("span", { class: "si-word" }, "MIA"),
          el("p", {}, "Sign in to your own MIA.")),
        el("label", { class: "si-field", for: "who" }, el("span", {}, "Email"),
          el("input", { id: "who", type: "email", autocomplete: "username", placeholder: "you@example.com", required: true })),
        el("label", { class: "si-field", for: "password" }, el("span", {}, "Password"),
          el("input", { id: "password", type: "password", autocomplete: "current-password", required: true })),
        // Two-step sign-in (core/two_step.py): shown when the account asks for the authenticator's code.
        el("label", { class: "si-field", for: "two-step-code", id: "two-step-row", hidden: true }, el("span", {}, "Code from your authenticator app"),
          el("input", { id: "two-step-code", type: "text", inputmode: "numeric", autocomplete: "one-time-code", maxlength: "6", pattern: "[0-9]*" })),
        el("button", { class: "btn btn-green si-go", type: "submit" }, "Sign In"),
        el("p", { class: "si-note" }, "Forgot it? Your recovery code resets it on the PC."));
      document.body.prepend(form);
    }
    form.hidden = false;
    form.onsubmit = async (e) => {
      e.preventDefault();
      try { await MIA.signIn($("#who").value.trim(), $("#password").value, $("#two-step-code").value.trim()); form.hidden = true; then(); }
      catch (err) {
        if (err.twoStep) { $("#two-step-row").hidden = false; $("#two-step-code").focus(); }
        say(err.message);
      }
    };
  }

  // ---------------------------------------------------------------- first start: make your account
  // The phone's first start (DEC-0019 Phase 2, 2026-10-07): name, email,
  // password, country and what MIA should help with; then the recovery
  // code, shown once. The engine checks everything (core/first_account.py).
  function setupForm(info, then) {
    const fields = {};
    const input = (name, attrs) => (fields[name] = el("input", Object.assign({ id: "setup-" + name, name }, attrs)));
    const country = el("select", { id: "setup-country", "aria-label": "Country" },
      info.countries.map((c) => el("option", { value: c.code, selected: c.code === "US" ? true : null }, c.name)));
    const picks = info.interests.map((name) => el("label", { class: "setup-chip" },
      el("input", { type: "checkbox", value: name }), el("span", {}, name)));
    const card = el("form", { class: "setup-card glass", id: "setup", "aria-label": "Make your account" },
      el("div", { class: "setup-head" }, el("span", { class: "home-badge", "aria-hidden": "true" }, "✦"),
        el("div", {}, el("h1", {}, "Welcome to MIA"), el("p", { class: "dim" }, "Let's make your account. It lives on this phone."))),
      el("label", { class: "form-row", for: "setup-name" }, el("span", {}, "What should MIA call you?"),
        input("name", { autocomplete: "given-name", required: true })),
      el("label", { class: "form-row", for: "setup-email" }, el("span", {}, "Email (you sign in with it)"),
        input("email", { type: "email", autocomplete: "email", required: true })),
      el("label", { class: "form-row", for: "setup-password" }, el("span", {}, "Password (at least " + info.min_password + " characters)"),
        input("password", { type: "password", autocomplete: "new-password", required: true, minlength: String(info.min_password) })),
      el("label", { class: "form-row", for: "setup-again" }, el("span", {}, "Password again"),
        input("again", { type: "password", autocomplete: "new-password", required: true })),
      el("label", { class: "form-row", for: "setup-country" }, el("span", {}, "Country (for money and help numbers)"), country),
      picks.length ? el("fieldset", { class: "setup-interests" }, el("legend", {}, "What do you want MIA to help with? (optional)"), picks) : null,
      el("button", { class: "btn btn-green setup-go", type: "submit" }, "Create my account"));
    document.body.prepend(card);
    fields.name.focus();
    card.onsubmit = async (e) => {
      e.preventDefault();
      if (fields.password.value !== fields.again.value) return say("The two passwords don't match.");
      try {
        const done = await MIA.setup({
          name: fields.name.value.trim(), email: fields.email.value.trim(), password: fields.password.value,
          country: country.value, interests: picks.map((p) => p.querySelector("input")).filter((i) => i.checked).map((i) => i.value),
        });
        card.replaceChildren(
          el("div", { class: "setup-head" }, el("span", { class: "home-badge", "aria-hidden": "true" }, "✦"),
            el("div", {}, el("h1", {}, "Hi, " + done.name + "!"), el("p", { class: "dim" }, "One more thing before we start."))),
          el("h2", {}, "Your recovery code"),
          el("p", { class: "setup-code" }, done.recovery_code || ""),
          el("p", {}, "Write it down somewhere safe. If you ever forget your password, it's the way back in. MIA shows it only now."),
          el("button", { class: "btn btn-green setup-go", type: "button", onclick: () => { card.remove(); then(); } }, "I've saved it. Let's go"));
      } catch (err) { say(err.message); }
    };
  }

  async function start(renderPage, options) {
    render = renderPage;
    // The header plate (DEC-0023, H-0036): the app's line icon in the badge,
    // and drawn large and faint as the plate's schematic (no photos).
    if (window.MIAIcons) {
      const glyph = document.body.dataset.icon || document.body.dataset.app;
      MIAIcons.badge($('.hero h1 > span[aria-hidden="true"]:first-child'), glyph);
      const hero = $(".hero");
      const drawing = MIAIcons.svg(glyph);
      if (hero && drawing && !$(".plate-motif", hero)) hero.append(el("span", { class: "plate-motif", "aria-hidden": "true" }, drawing));
    }
    const go = async () => {
      const app = $("#app") || $(".layout");
      if (app) app.hidden = false;
      let shell = null;
      try { shell = await MIA.shell(); renderNav(shell); } catch (e) { say(e.message); }
      if (!options || options.talk !== false) { mountTalk(); if (shell) sayLine(shell); }
      if (MIA.pageOpened) MIA.pageOpened(location.pathname.split("/").pop() || "index.html").catch(() => {});  // a count (page-usage audit)
      await refresh();
      backToPlace();  // the scroll and Talk you left, after the phone locked or the app was closed
      if (!options || options.refreshOnChange !== false) {
        MIA.onChange(async () => {
          try { renderNav(await MIA.shell()); } catch (e) { /* keep the old one */ }
          refresh();
        });
      }
      if (MIA.demo) say("Demo: placeholder data. Actions and Talk need MIA running.");
    };
    if (MIA.signedIn) return go();
    const info = await MIA.setupStatus();
    if (info.needed) setupForm(info, go);
    else signInForm(go);
  }

  // Every screen's voice twin (DEC-0125): "Say: …" under the title, the page's own phrase (<body data-say>, for a page
  // inside an app, like Projects in the Workshop) or else the app's ask; a tap puts it in Talk.
  function sayLine(shell) {
    const hero = $(".hero");
    const here = (shell.apps || []).find((a) => a.id === document.body.dataset.app);
    const ask = document.body.dataset.say || (here && here.ask);
    if (!hero || !ask || $(".say-line", hero)) return;
    hero.append(el("button", { type: "button", class: "say-line", title: "Try it in Talk",
      onclick: () => toggleTalk(true, ask) }, el("span", { class: "say-label" }, "Say"), "“" + ask + "”"));
  }

  /** The frame alone (sidebar + MIA) for a page that runs its own render and sign-in. */
  // ---------------------------------------------------------------- Search (Ctrl+K, "/")
  // Apps are matched here (the frame has the person's apps); records come from core/web_search.py (/api/search),
  // each opening its own page. The last rows always offer the library (knowledge.html?q=) and asking MIA.
  let shellData = null;
  let searchBox = null;
  function appMatches(q) {
    const words = q.toLowerCase().split(/\s+/).filter(Boolean);
    return ((shellData && shellData.apps) || []).filter((a) => {
      const hay = (a.name + " " + (a.tagline || "")).toLowerCase();
      return words.every((w) => hay.includes(w));
    }).sort((a, b) => Number(!a.name.toLowerCase().startsWith(words[0])) - Number(!b.name.toLowerCase().startsWith(words[0]))).slice(0, 5);
  }
  function openSearch() {
    if (searchBox) { searchBox.showModal(); searchBox.querySelector("input").select(); return; }
    const input = el("input", { type: "search", class: "search-input", placeholder: "Search apps, things and notes…",
      "aria-label": "Search", autocomplete: "off", role: "combobox", "aria-controls": "mia-search-list", "aria-expanded": "true" });
    const list = el("ul", { id: "mia-search-list", class: "search-list", role: "listbox", "aria-label": "Results" });
    let seq = 0, active = 0;
    const row = (title, detail, href, glyph) => el("li", { role: "option" },
      el("a", { href }, el("span", { class: "sr-ico", "aria-hidden": "true" }, glyph), el("span", { class: "sr-title" }, title),
        detail ? el("span", { class: "sr-detail" }, detail) : null));
    const mark = () => [...list.children].forEach((li, i) => li.setAttribute("aria-selected", String(i === active)));
    async function run() {
      const q = input.value.trim(), mine = ++seq;
      if (!q) { list.replaceChildren(el("li", { class: "sr-hint" }, "Type to search. Enter opens the first result.")); return; }
      const apps = appMatches(q).map((a) => row(a.name, "App", a.page, "▦"));
      const tail = [row("Search the library for \u201c" + q + "\u201d", "Knowledge, offline", "knowledge.html?q=" + encodeURIComponent(q), "📚"),
        row("Ask MIA: \u201c" + q + "\u201d", "Talk", "assistant.html?ask=" + encodeURIComponent(q), "💬")];
      list.replaceChildren(...apps, ...tail); active = 0; mark();
      let found = [];
      try { found = (await MIA.search(q)).results || []; } catch (e) { found = []; }
      if (mine !== seq) return;  // a newer search has started
      list.replaceChildren(...apps, ...found.map((r) => row(r.title, r.detail, r.href, "•")), ...tail); active = 0; mark();
    }
    input.addEventListener("input", run);
    input.addEventListener("keydown", (e) => {
      const n = list.children.length;
      if (e.key === "ArrowDown" || e.key === "ArrowUp") {
        e.preventDefault(); active = (active + (e.key === "ArrowDown" ? 1 : n - 1)) % Math.max(n, 1); mark();
        const li = list.children[active]; if (li) li.scrollIntoView({ block: "nearest" });
      } else if (e.key === "Enter") {
        e.preventDefault(); const a = list.children[active] && list.children[active].querySelector("a"); if (a) location.href = a.href;
      }
    });
    searchBox = el("dialog", { class: "confirm search-dialog", "aria-label": "Search", onclick: (e) => { if (e.target === searchBox) searchBox.close(); } },
      el("div", { class: "search-panel" }, input, list));
    document.body.append(searchBox);
    searchBox.showModal(); run();
  }
  document.addEventListener("keydown", (e) => {
    const typing = /^(INPUT|TEXTAREA|SELECT)$/.test(e.target.tagName) || e.target.isContentEditable;
    if ((e.key === "k" || e.key === "K") && (e.ctrlKey || e.metaKey)) { e.preventDefault(); openSearch(); }
    else if (e.key === "/" && !typing && !e.ctrlKey && !e.metaKey && !e.altKey) { e.preventDefault(); openSearch(); }
  });

  async function frame() {
    try { renderNav(await MIA.shell()); } catch (e) { return; }
    if (talkHere) mountTalk();
  }

  // Gear condition (DEC-0028): an asset's upkeep as a health bar, from the
  // engine's `condition` (core/web_equipment.condition). Nothing when it
  // has no recurring upkeep yet.
  function conditionBar(c, big) {
    if (!c) return null;
    return el("div", { class: "gear-condition tone-" + c.tone + (big ? " big" : ""), role: "meter", "aria-valuenow": String(c.percent),
      "aria-valuemin": "0", "aria-valuemax": "100", "aria-label": "Condition " + c.percent + "%, " + c.label },
      el("span", { class: "gc-label" }, "Condition"),
      el("span", { class: "gc-bar" }, el("span", { class: "gc-fill", style: "width:" + c.percent + "%" })),
      el("span", { class: "gc-value" }, c.percent + "% · " + c.label));
  }

  // An email draft (core/email_drafts.py): MIA never sends by herself. Send
  // goes only when pressed (from your own address, once it's set up on the
  // computer); Copy and Mail App always work.
  async function showDraft(d, canSend) {
    const dialog = el("dialog", { class: "confirm form-dialog draft-view", "aria-label": d.subject || "Email draft" });
    const close = () => { dialog.close(); dialog.remove(); };
    const run = async (fn, okText) => { try { await fn(); say(okText); close(); } catch (e) { say(e.message); } };
    dialog.append(el("h3", {}, d.subject || "Email"),
      el("p", { class: "dim" }, d.to && d.to.length ? "To: " + d.to.join(", ") : "No address yet: add one in your mail app."),
      el("pre", { class: "draft-body" }, d.body),
      el("div", { class: "confirm-actions" },
        canSend && d.to && d.to.length ? el("button", { type: "button", class: "btn btn-green", onclick: () => run(() => MIA.sendDraft(d.draft_id), "Sent.") }, "Send") : null,
        el("button", { type: "button", class: "btn btn-ghost", onclick: async () => {
          try { await navigator.clipboard.writeText(d.text || d.body); say("Copied."); } catch (e) { say("Couldn't copy here."); }
        } }, "Copy"),
        el("a", { class: "btn btn-ghost", href: d.mailto }, "Mail App"),
        el("button", { type: "button", class: "btn btn-ghost", onclick: () => run(() => MIA.discardDraft(d.draft_id), "Discarded.") }, "Discard"),
        el("button", { type: "button", class: "btn btn-ghost", onclick: close }, "Close")));
    dialog.oncancel = (ev) => { ev.preventDefault(); close(); };
    document.body.append(dialog);
    dialog.showModal();
  }

  // Buffs (DEC-0028): the good effects you've earned (core/buffs.py), never
  // debuffs. Tapping one says what earned it and how long it lasts.
  function buffChips(list, compact) {
    if (!list || !list.length) return null;
    return el("div", { class: "buff-row" + (compact ? " compact" : ""), role: "list", "aria-label": "Active buffs" }, list.map((b) =>
      el("button", { type: "button", class: "buff", role: "listitem", title: b.why,
        onclick: () => say(b.icon + " " + b.name + ": " + b.why + " +" + b.bonus + " " + b.stat.charAt(0).toUpperCase() + b.stat.slice(1) + ", " + b.lasts + ".") },
        el("span", { class: "buff-ico", "aria-hidden": "true" }, b.icon), el("span", { class: "buff-name" }, b.name),
        el("small", { class: "buff-left" }, b.lasts))));
  }

  window.MIAShell = { look, theme, start, act, say, el, refresh, frame, form, search: openSearch, levelCard, conditionBar, buffChips, showDraft, confirm: confirmBox, talk: toggleTalk,
    notRight, voiceRecorder, playReply };

  // <script src="shell.js" data-frame="garage">: frame an existing page as soon
  // as someone is signed in (now, or when its own sign-in form succeeds).
  const me = document.currentScript;
  // data-talk="own": the page has its own Talk (Home), so no floating one.
  const talkHere = !(me && me.dataset.talk === "own");
  if (me && me.dataset.frame) {
    document.body.dataset.app = me.dataset.frame;
    const signIn = MIA.signIn;
    MIA.signIn = async (...args) => { const r = await signIn(...args); frame(); return r; };
    if (MIA.signedIn) {
      if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", frame);
      else frame();
    }
  }
})();
