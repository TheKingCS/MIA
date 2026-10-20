/*
 * passwords.js — Passwords (claude, 2026-10-20, DEC-0035). Renders
 * MIA.passwords() (core/password_vault.py): make the vault (a master
 * password, then the recovery code shown once), unlock it (or use the
 * recovery code and set a new master password), and the logins: search,
 * Show and Copy (a password comes from MIA one at a time, only then, and
 * is hidden again after a few seconds), add and change with a generator,
 * import a browser or Bitwarden export, Lock. Never through actions, so a
 * password is never in an action's record. Formatting only.
 */
(function () {
  "use strict";
  const { el, say } = MIAShell;
  const $ = (id) => document.getElementById(id);
  const SHOW_SECONDS = 15, CLEAR_CLIPBOARD_SECONDS = 30;
  let page = null, query = "", timer = null;

  const btn = (label, cls, onclick) => el("button", { type: "button", class: "btn " + cls, onclick }, label);
  const section = (title, actions, ...body) =>
    el("section", { class: "glass money-section" }, el("div", { class: "sect" }, el("h2", {}, title), actions), ...body);
  const input = (id, label, type, value, extra) => el("label", { class: "form-row", for: id }, el("span", {}, label),
    el("input", Object.assign({ id, type: type || "text", value: value || "", autocomplete: "off", spellcheck: "false" }, extra || {})));

  // A locked vault answers 423: draw the unlock screen again.
  async function guard(work) {
    try { return await work(); }
    catch (e) {
      say(e.message);
      if (e.status === 423) MIAShell.refresh();
      return null;
    }
  }

  // ------------------------------------------------------------ the generator (here, in the browser)
  function generate(length) {
    const sets = ["abcdefghijkmnpqrstuvwxyz", "ABCDEFGHJKLMNPQRSTUVWXYZ", "23456789", "!@#$%^&*-_=+?"];
    const all = sets.join("");
    const pick = (chars) => { const n = new Uint32Array(1); crypto.getRandomValues(n); return chars[n[0] % chars.length]; };
    const out = sets.map(pick);  // one of each kind
    while (out.length < (length || 20)) out.push(pick(all));
    for (let i = out.length - 1; i > 0; i--) {  // shuffle
      const n = new Uint32Array(1); crypto.getRandomValues(n);
      const j = n[0] % (i + 1); [out[i], out[j]] = [out[j], out[i]];
    }
    return out.join("");
  }

  async function copy(text, what) {
    try { await navigator.clipboard.writeText(text); }
    catch (e) {
      const t = el("textarea", { class: "pw-offscreen" }); t.value = text; document.body.append(t); t.select();
      document.execCommand("copy"); t.remove();
    }
    say(what + " copied. The clipboard is cleared in " + CLEAR_CLIPBOARD_SECONDS + " seconds.");
    setTimeout(() => { navigator.clipboard && navigator.clipboard.writeText("").catch(() => {}); }, CLEAR_CLIPBOARD_SECONDS * 1000);
  }

  // ------------------------------------------------------------ dialogs
  function dialog(title, body, actions) {
    return new Promise((resolve) => {
      const box = el("dialog", { class: "confirm form-dialog", "aria-label": title });
      const done = (v) => { box.close(); box.remove(); resolve(v); };
      box.append(el("h3", {}, title), ...body, el("div", { class: "confirm-actions" },
        ...actions.map(([label, cls, value]) => btn(label, cls, () => done(typeof value === "function" ? value() : value)))));
      box.oncancel = (e) => { e.preventDefault(); done(null); };
      document.body.append(box);
      box.showModal();
      const first = box.querySelector("input");
      if (first) first.focus();
    });
  }

  async function editLogin(l) {
    const pw = input("pw-password", l ? "Password (leave empty to keep it)" : "Password", "password", "");
    const field = pw.querySelector("input");
    const shown = btn("Show", "btn-ghost btn-small", () => { field.type = field.type === "password" ? "text" : "password"; });
    const gen = btn("Make A Strong One", "btn-ghost btn-small", () => { field.value = generate(20); field.type = "text"; });
    const v = await dialog(l ? "Change " + l.title : "Add A Login", [
      input("pw-title", "Name (the website or app)", "text", l && l.title),
      input("pw-username", "Username or email", "text", l && l.username),
      pw, el("div", { class: "row-buttons" }, gen, shown),
      input("pw-url", "Website (optional)", "text", l && l.url),
      input("pw-folder", "Folder (optional, like Banking)", "text", l && l.folder),
      el("label", { class: "form-row", for: "pw-note" }, el("span", {}, "Note (optional)"),
        el("textarea", { id: "pw-note", rows: "2" }, (l && l.note) || "")),
    ], [["Cancel", "btn-ghost", null], ["Save", "btn-amber", () => ({
      title: $("pw-title").value, username: $("pw-username").value, password: field.value, url: $("pw-url").value,
      folder: $("pw-folder").value, note: $("pw-note").value })]]);
    if (!v) return;
    const body = Object.assign(v, l ? { entry_id: l.entry_id, keep_password: !v.password } : {});
    const done = await guard(() => MIA.vaultSave(body));
    if (done) { say(done.message); MIAShell.refresh(); }
  }

  async function changeMaster() {
    const v = await dialog("Change Master Password", [
      input("pw-current", "Current master password", "password"),
      input("pw-new", "New master password", "password"),
      input("pw-new2", "The new one again", "password"),
    ], [["Cancel", "btn-ghost", null], ["Change It", "btn-amber", () => ({ current: $("pw-current").value, fresh: $("pw-new").value, again: $("pw-new2").value })]]);
    if (!v) return;
    if (v.fresh !== v.again) { say("The new passwords don't match."); return; }
    const done = await guard(() => MIA.vaultChange(v.current, v.fresh));
    if (done) say(done.message);
  }

  function importExport() {
    const pick = el("input", { type: "file", accept: ".csv,text/csv", hidden: true });
    pick.onchange = async () => {
      const file = pick.files[0];
      pick.remove();
      if (!file) return;
      const done = await guard(async () => MIA.vaultImport(await file.text()));
      if (done) { say(done.message); MIAShell.refresh(); }
    };
    document.body.append(pick);
    pick.click();
  }

  // ------------------------------------------------------------ screens
  function makeVault() {
    const go = async () => {
      const a = $("pw-master").value, b = $("pw-master2").value;
      if (a !== b) { say("The two don't match."); return; }
      const done = await guard(() => MIA.vaultSetup(a));
      if (!done) return;
      await dialog("Your Recovery Code", [
        el("p", {}, "If you ever forget your master password, this code is the only other way in. Write it down and keep it somewhere safe, away from this phone."),
        el("p", { class: "pw-code" }, done.recovery_code),
        el("p", { class: "dim" }, "It's shown this once. MIA doesn't keep it, and nobody can get it back for you."),
      ], [["I Wrote It Down", "btn-amber", true]]);
      MIAShell.refresh();
    };
    return section("Make Your Vault", null,
      el("p", {}, "Your logins are kept encrypted with a master password only you know. MIA's assistant never sees them, and they sync between your phone and computer still encrypted."),
      el("p", { class: "dim" }, "Pick something long you'll remember: a few unrelated words work well. At least " + page.min_master + " characters."),
      input("pw-master", "Master password", "password", "", { autocomplete: "new-password" }),
      input("pw-master2", "The same again", "password", "", { autocomplete: "new-password" }),
      el("div", { class: "row-buttons" }, btn("Make My Vault", "btn-amber", go)));
  }

  function unlockScreen() {
    let recovery = false;
    const box = el("div", {});
    const draw = () => box.replaceChildren(recovery
      ? el("div", {}, input("pw-code", "Recovery code", "text", "", { autocapitalize: "characters" }),
          input("pw-new", "New master password", "password", "", { autocomplete: "new-password" }),
          el("div", { class: "row-buttons" },
            btn("Unlock", "btn-amber", async () => {
              const done = await guard(() => MIA.vaultUnlock("", $("pw-code").value, $("pw-new").value));
              if (done) { say(done.message); MIAShell.refresh(); }
            }),
            btn("Use My Master Password", "btn-ghost btn-small", () => { recovery = false; draw(); })))
      : el("form", { onsubmit: async (e) => {
          e.preventDefault();
          const done = await guard(() => MIA.vaultUnlock($("pw-master").value));
          if (done) MIAShell.refresh();
        } }, input("pw-master", "Master password", "password", "", { autocomplete: "current-password" }),
        el("div", { class: "row-buttons" }, el("button", { type: "submit", class: "btn btn-amber" }, "Unlock"),
          btn("Forgot It?", "btn-ghost btn-small", () => { recovery = true; draw(); }))));
    draw();
    return section("Locked", null, el("p", { class: "dim" }, page.count + (page.count === 1 ? " login" : " logins") +
      " inside. It locks itself after " + page.lock_after_minutes + " minutes you're not using it."), box);
  }

  function row(l) {
    const secret = el("span", { class: "pw-secret" }, "••••••••");
    let hide = null;
    const show = async () => {
      const got = await guard(() => MIA.vaultReveal(l.entry_id));
      if (!got) return;
      secret.textContent = got.password; secret.classList.add("open");
      clearTimeout(hide);
      hide = setTimeout(() => { secret.textContent = "••••••••"; secret.classList.remove("open"); }, SHOW_SECONDS * 1000);
    };
    const copyPassword = async () => { const got = await guard(() => MIA.vaultReveal(l.entry_id)); if (got) copy(got.password, "Password"); };
    return el("div", { class: "row money-row pw-row" },
      el("div", { class: "pw-main" },
        el("div", { class: "row-title" }, l.title, l.reused ? el("span", { class: "pw-flag" }, "Reused") : null,
          l.weak ? el("span", { class: "pw-flag" }, "Weak") : null),
        el("div", { class: "row-sub" }, [l.username, l.site].filter(Boolean).join(" · ")),
        l.has_password ? secret : null),
      el("div", { class: "row-buttons" },
        l.has_password ? btn("Copy", "btn-amber btn-small", copyPassword) : null,
        l.has_password ? btn("Show", "btn-ghost btn-small", show) : null,
        l.username ? btn("Copy User", "btn-ghost btn-small", () => copy(l.username, "Username")) : null,
        btn("Change", "btn-ghost btn-small", () => editLogin(l)),
        btn("Delete", "btn-ghost btn-small", async () => {
          if (!(await MIAShell.confirm("Delete the login for " + l.title + "? This can't be undone."))) return;
          const done = await guard(() => MIA.vaultDelete(l.entry_id));
          if (done) { say(done.message); MIAShell.refresh(); }
        })));
  }

  function logins() {
    const q = query.trim().toLowerCase();
    const shown = page.logins.filter((l) => !q || [l.title, l.username, l.site, l.folder, l.note].join(" ").toLowerCase().includes(q));
    const search = el("input", { type: "search", class: "pw-search", placeholder: "Search", value: query, "aria-label": "Search logins",
      oninput: (e) => { query = e.target.value; const at = e.target.selectionStart; draw(); const s = document.querySelector(".pw-search"); s.focus(); s.setSelectionRange(at, at); } });
    const groups = {};
    shown.forEach((l) => (groups[l.folder || ""] = groups[l.folder || ""] || []).push(l));
    const h = page.health;
    return [
      el("div", { class: "row-buttons pw-tools" }, search, btn("Add A Login", "btn-amber", () => editLogin(null)),
        btn("Lock", "btn-ghost", async () => { await guard(() => MIA.vaultLock()); MIAShell.refresh(); })),
      h.reused || h.weak ? el("p", { class: "pw-health" }, "To fix when you can: " +
        [h.reused ? h.reused + (h.reused === 1 ? " uses" : " use") + " a password another login also uses" : "",
          h.weak ? h.weak + (h.weak === 1 ? " has" : " have") + " a weak password" : ""]
          .filter(Boolean).join("; ") + ". Change them on the site, then here.") : null,
      ...(shown.length ? Object.keys(groups).sort().map((f) => section(f || "Logins", null,
        el("div", { class: "rows" }, groups[f].map(row))))
        : [el("p", { class: "empty" }, page.logins.length ? "Nothing matches." : "No logins yet. Add one, or bring them in from your browser.")]),
      section("Bring Them In", null,
        el("p", {}, "From Chrome or Edge: Settings → Passwords → Export. From Bitwarden, Firefox, 1Password or LastPass: their CSV export. Then pick the file here."),
        el("p", { class: "dim" }, "The export file isn't encrypted: delete it once they're in."),
        el("div", { class: "row-buttons" }, btn("Import A CSV", "btn-ghost", importExport), btn("Change Master Password", "btn-ghost", changeMaster))),
    ].filter(Boolean);
  }

  function draw() {
    const cells = [el("div", { class: "cell ok" }, el("span", { class: "n" }, page.count), el("span", { class: "t" }, "Logins")),
      el("div", { class: "cell " + (page.unlocked ? "soon" : "ok") }, el("span", { class: "n" }, page.unlocked ? "Open" : "Locked"), el("span", { class: "t" }, "Vault"))];
    if (page.unlocked) cells.push(
      el("div", { class: "cell " + (page.health.reused ? "soon" : "ok") }, el("span", { class: "n" }, page.health.reused), el("span", { class: "t" }, "Reused")),
      el("div", { class: "cell " + (page.health.weak ? "soon" : "ok") }, el("span", { class: "n" }, page.health.weak), el("span", { class: "t" }, "Weak")));
    $("strip").replaceChildren(...cells);
    $("panel").replaceChildren(...[].concat(!page.set_up ? makeVault() : !page.unlocked ? unlockScreen() : logins()));
  }

  MIAShell.start(async () => {
    page = await MIA.passwords();
    if (!page.available) { $("panel").replaceChildren(el("p", { class: "empty" }, "Passwords aren't set up on this MIA.")); return; }
    draw();
    // Notice when it locks itself (nothing used for a few minutes).
    clearInterval(timer);
    timer = setInterval(async () => {
      if (!page.unlocked) return;
      try { const now = await MIA.passwords(); if (!now.unlocked) { page = now; draw(); } } catch (e) { /* next time */ }
    }, 60000);
  });
})();
