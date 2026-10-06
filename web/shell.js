/*
 * shell.js — the frame every MIA web screen shares (claude, 2026-10-06, DEC-0017).
 *
 * Function first; the look is Muse's (components.css). Gives each page:
 *   - sign-in when nobody is signed in on this tab;
 *   - the sidebar: the person's own apps from the engine (MIA.shell(): child-safe,
 *     tucked-away apps hidden), the current page highlighted, level and XP at the
 *     bottom, and how many apps are still only in the PC app;
 *   - MIA, everywhere: the orb button opens a Talk panel (MIA.talk);
 *   - MIAShell.act(action): the one way a screen changes anything —
 *     propose → the engine's sentence in a confirm → approve → undo toast.
 *
 * A page:  <body data-app="garage"> ... <script src="mia.js"></script>
 *          <script src="shell.js"></script>
 *          MIAShell.start(async () => { ...render...; }, { refreshOnChange: true });
 * No logic about the person's life here: everything shown comes from the engine.
 */
(function () {
  "use strict";

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

  /** Propose → confirm → approve → undo toast. Returns the executed proposal, or null. */
  async function act(action) {
    if (!action) return null;
    try {
      const proposal = await MIA.propose(action.kind, action.params);
      if (!(await confirmBox(proposal.summary))) {
        MIA.reject(proposal.proposal_id).catch(() => {});
        return null;
      }
      const done = await MIA.approve(proposal.proposal_id);
      say(done.result || "Done.", done.undoable ? async () => {
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
          const type = f.type === "date" ? "date" : numeric ? "number" : "text";
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
  // Desktop module pages: the concept's sidebar. Phones, and Home at any
  // size: one "⋯" button that opens every choice (Zac, 2026-10-06: the
  // wrapped phone rail looked clunky; Home stays centred on MIA).
  function levelBlock(p) {
    const pct = p.xp_for_level ? Math.round((100 * p.xp_into_level) / p.xp_for_level) : 0;
    return el("div", { class: "nav-level" },
      el("div", { class: "side-level" },
        el("span", { class: "side-level-n" }, "lvl " + p.level),
        el("span", { class: "side-level-xp" }, p.total_xp + " XP")),
      el("div", { class: "xpbar" }, el("div", { class: "xpbar-track" },
        el("div", { class: "xpbar-fill", style: "width:" + pct + "%" }))));
  }

  function appLinks(shell, cls) {
    const here = document.body.dataset.app || "web_home";
    return shell.apps.map((a) => el("a", { class: cls, href: a.page, "aria-current": a.id === here ? "page" : null },
      el("span", { class: "ico", "aria-hidden": "true" }, a.icon), el("span", { class: "label" }, a.name)));
  }

  function more(shell) {
    return shell.on_pc_only.length
      ? el("a", { class: "side-more", href: "apps.html", title: shell.on_pc_only.join(", ") },
        shell.on_pc_only.length + " more apps in the PC app for now")
      : null;
  }

  function renderNav(shell) {
    const layout = $(".layout");
    document.body.classList.toggle("has-side", Boolean(layout));
    if (layout) {
      let side = $("nav.side");
      if (!side) {
        side = el("nav", { class: "side", "aria-label": "Apps" });
        layout.prepend(side);
      }
      side.replaceChildren(
        el("a", { class: "brand", href: "index.html" }, el("span", { class: "brand-mark", "aria-hidden": "true" }, "🌿"),
          el("span", {}, "MIA", el("small", {}, "Your Life. In Sync."))),
        ...appLinks(shell, "nav"),
        el("div", { class: "side-foot" }, levelBlock(shell.person), more(shell)));
    }
    // Phone: the concept's bottom bar (Home, Apps, Dashboard, More); More opens the drawer.
    let bar = $("#mia-bottom-bar");
    if (!bar) {
      bar = el("nav", { id: "mia-bottom-bar", class: "bottom-bar", "aria-label": "Main" });
      document.body.append(bar);
    }
    const here = document.body.dataset.app || "web_home";
    const tab = (href, id, icon, label) => el("a", { href, "aria-current": here === id ? "page" : null },
      el("span", { class: "ico", "aria-hidden": "true" }, icon), label);
    bar.replaceChildren(
      tab("index.html", "web_home", "🏠", "Home"),
      tab("apps.html", "module_browser", "▦", "Apps"),
      tab("dashboard.html", "dashboard", "📊", "Dashboard"),
      el("button", { type: "button", id: "mia-menu-button", "aria-label": "More", "aria-expanded": "false",
        "aria-controls": "mia-menu", onclick: () => toggleMenu() },
      el("span", { class: "ico", "aria-hidden": "true" }, "⋯"), "More"));
    let menu = $("#mia-menu");
    if (!menu) {
      menu = el("div", { id: "mia-menu", class: "menu-sheet", hidden: true, role: "dialog", "aria-label": "Menu",
        onclick: (e) => { if (e.target === menu) toggleMenu(false); } });
      document.body.append(menu);
      document.addEventListener("keydown", (e) => { if (e.key === "Escape") toggleMenu(false); });
    }
    menu.replaceChildren(el("div", { class: "menu-panel" },
      el("div", { class: "menu-head" },
        el("span", { class: "menu-brand" }, "🌿 MIA", el("small", { class: "menu-tagline" }, " Your Life. In Sync.")),
        el("button", { type: "button", class: "btn btn-ghost", "aria-label": "Close", onclick: () => toggleMenu(false) }, "✕")),
      el("nav", { class: "menu-grid", "aria-label": "Apps" }, ...appLinks(shell, "menu-item")),
      levelBlock(shell.person), more(shell),
      el("p", { class: "menu-tagline" }, "Better systems. Bigger dreams.")));
  }

  function toggleMenu(open) {
    const menu = $("#mia-menu");
    if (!menu) return;
    const show = open == null ? menu.hidden : open;
    menu.hidden = !show;
    $("#mia-menu-button").setAttribute("aria-expanded", String(show));
    if (show) { const first = menu.querySelector("a"); if (first) first.focus(); }
  }

  // ---------------------------------------------------------------- MIA, everywhere
  function mountTalk() {
    if ($("#mia-orb")) return;
    const log = el("div", { class: "talk-log", id: "talk-log", "aria-live": "polite" });
    const input = el("input", { id: "talk-input", placeholder: "Talk to MIA…", autocomplete: "off", "aria-label": "Message MIA" });
    const panel = el("aside", { class: "talk-panel glass glow", id: "talk-panel", hidden: true, "aria-label": "Talk to MIA" },
      el("div", { class: "talk-head" }, el("span", { class: "mia-line" }, el("span", { class: "mia-dot" }), "MIA"),
        el("button", { type: "button", class: "btn btn-ghost", onclick: () => toggleTalk(false) }, "Close")),
      log,
      el("form", { class: "talk-form", onsubmit: async (e) => {
        e.preventDefault();
        const text = input.value.trim();
        if (!text) return;
        input.value = "";
        log.append(el("p", { class: "bubble me" }, text));
        const thinking = el("p", { class: "bubble mia thinking" }, "…");
        log.append(thinking);
        log.scrollTop = log.scrollHeight;
        try {
          const turn = await MIA.talk(text);
          thinking.textContent = turn.reply_text || "Done.";
          refresh();
        } catch (err) {
          thinking.textContent = err.message;
        }
        thinking.classList.remove("thinking");
        log.scrollTop = log.scrollHeight;
      } }, input, el("button", { class: "btn btn-amber", type: "submit" }, "Send")));
    const orb = el("button", { type: "button", id: "mia-orb", class: "mia-orb-button", "aria-label": "Talk to MIA",
      onclick: () => toggleTalk() }, el("span", { class: "mia-orb-core", "aria-hidden": "true" }));
    document.body.append(panel, orb);
  }

  function toggleTalk(open, prefill) {
    const panel = $("#talk-panel");
    if (!panel) return;
    const show = open == null ? panel.hidden : open;
    panel.hidden = !show;
    if (show) {
      const input = $("#talk-input");
      if (prefill != null) input.value = prefill;
      input.focus();
    }
  }

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
      form = el("form", { class: "sign-in", id: "sign-in", "aria-label": "Sign in to MIA" },
        el("p", {}, "Sign in to MIA"),
        el("input", { id: "who", autocomplete: "username", placeholder: "Email", required: true, "aria-label": "Email" }),
        el("input", { id: "password", type: "password", autocomplete: "current-password", placeholder: "Password",
          required: true, "aria-label": "Password" }),
        el("button", { class: "btn btn-amber", type: "submit" }, "Sign in"));
      document.body.prepend(form);
    }
    form.hidden = false;
    form.onsubmit = async (e) => {
      e.preventDefault();
      try { await MIA.signIn($("#who").value.trim(), $("#password").value); form.hidden = true; then(); }
      catch (err) { say(err.message); }
    };
  }

  async function start(renderPage, options) {
    render = renderPage;
    const go = async () => {
      const app = $("#app") || $(".layout");
      if (app) app.hidden = false;
      try { renderNav(await MIA.shell()); } catch (e) { say(e.message); }
      if (!options || options.talk !== false) mountTalk();
      await refresh();
      if (!options || options.refreshOnChange !== false) {
        MIA.onChange(async () => {
          try { renderNav(await MIA.shell()); } catch (e) { /* keep the old one */ }
          refresh();
        });
      }
      if (MIA.demo) say("Demo: placeholder data. Actions and Talk need MIA running.");
    };
    if (!MIA.signedIn) signInForm(go);
    else go();
  }

  /** The frame alone (sidebar + MIA) for a page that runs its own render and sign-in. */
  async function frame() {
    try { renderNav(await MIA.shell()); } catch (e) { return; }
    if (talkHere) mountTalk();
  }

  window.MIAShell = { start, act, say, el, refresh, frame, form, talk: toggleTalk };

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
