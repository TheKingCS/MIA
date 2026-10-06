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

  // ---------------------------------------------------------------- sidebar
  function renderSidebar(shell) {
    let side = $("nav.side");
    if (!side) {
      side = el("nav", { class: "side", "aria-label": "Apps" });
      $(".layout").prepend(side);
    }
    const here = document.body.dataset.app || "dashboard";
    const p = shell.person;
    const pct = p.xp_for_level ? Math.round((100 * p.xp_into_level) / p.xp_for_level) : 0;
    side.replaceChildren(
      el("a", { class: "brand", href: "index.html" }, el("span", { class: "brand-mark", "aria-hidden": "true" }, "🌿"),
        el("span", {}, "MIA", el("small", {}, "Your Life. In Sync."))),
      ...shell.apps.map((a) => el("a", { class: "nav", href: a.page, "aria-current": a.id === here ? "page" : null },
        el("span", { class: "ico", "aria-hidden": "true" }, a.icon), a.name)),
      el("div", { class: "side-foot" },
        el("div", { class: "side-level" },
          el("span", { class: "side-level-n" }, "lvl " + p.level),
          el("span", { class: "side-level-xp" }, p.total_xp + " XP")),
        el("div", { class: "xpbar" }, el("div", { class: "xpbar-track" },
          el("div", { class: "xpbar-fill", style: "width:" + pct + "%" }))),
        shell.on_pc_only.length
          ? el("small", { class: "side-more", title: shell.on_pc_only.join(", ") },
            shell.on_pc_only.length + " more apps in the PC app for now")
          : null));
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
      try { renderSidebar(await MIA.shell()); } catch (e) { say(e.message); }
      mountTalk();
      await refresh();
      if (!options || options.refreshOnChange !== false) {
        MIA.onChange(async () => {
          try { renderSidebar(await MIA.shell()); } catch (e) { /* keep the old one */ }
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
    try { renderSidebar(await MIA.shell()); } catch (e) { return; }
    mountTalk();
  }

  window.MIAShell = { start, act, say, el, refresh, frame, talk: toggleTalk };

  // <script src="shell.js" data-frame="garage">: frame an existing page as soon
  // as someone is signed in (now, or when its own sign-in form succeeds).
  const me = document.currentScript;
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
