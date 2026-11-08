/*
 * settings.js — the Settings screen (claude, 2026-10-07; Zac: the gear's
 * Settings). Renders MIA.settings() (core/web_account.py): the person's
 * own settings, grouped as on the PC, the kinds of message MIA is taking a
 * break from, and a way to choose which apps show. Each change is an
 * action (setting.set, communication.resume): confirmed, then undoable.
 */
(function () {
  "use strict";
  const { el, act } = MIAShell;
  const $ = (id) => document.getElementById(id);
  let page = null;

  const section = (title, ...body) => el("section", { class: "glass money-section" }, el("div", { class: "sect" }, el("h2", {}, title)), ...body);

  async function change(key, value) {
    if (!(await act({ kind: "setting.set", params: { key, value } }))) draw();  // not now: put the control back
  }

  function control(s) {
    const id = "s-" + s.key.replace(/\./g, "-");
    if (s.kind === "toggle") {
      const box = el("input", { id, type: "checkbox", role: "switch", checked: s.value ? true : null,
        onchange: () => change(s.key, box.checked) });
      return el("span", { class: "switch" }, box, el("span", { "aria-hidden": "true" }));
    }
    if (s.kind === "choice") {
      const pick = el("select", { id, onchange: () => change(s.key, pick.value) },
        s.options.map((o) => el("option", { value: o.value, selected: String(o.value) === String(s.value) ? true : null }, o.label)));
      if (s.key === "sound.startup") return el("span", { class: "row-buttons" }, pick, startupPlay(pick));
      return pick;
    }
    if (s.kind === "number") {
      const n = el("input", { id, type: "number", inputmode: "numeric", min: s.low, max: s.high, step: "1",
        onchange: () => change(s.key, n.value) });
      n.value = s.value;
      return n;
    }
    const t = el("input", { id, type: "text", maxlength: "200", onchange: () => change(s.key, t.value) });
    t.value = s.value || "";
    return t;
  }

  // The design canvas (DEC-0113): each setting a row, its name and a short note on the left and its control (a
  // switch for on/off) on the right; a group is a small label over one card of rows.
  const setting = (s) => el("div", { class: "st-row" + (s.kind === "text" ? " wide" : "") },
    el("div", { class: "st-text" }, el("label", { for: "s-" + s.key.replace(/\./g, "-") }, s.label),
      s.help ? el("span", { class: "st-note" }, s.help) : null),
    el("div", { class: "st-control" }, control(s)));
  const group = (title, ...rows) => el("section", { class: "st-group", "aria-label": title },
    el("h2", { class: "st-label" }, title), el("div", { class: "glass st-card" }, ...rows.filter(Boolean)));

  // Hear a startup sound before choosing it (core/boot_sound.py, 2026-11-07): plays the one picked in the list.
  let startupAudio = null;
  function startupPlay(pick) {
    return el("button", { type: "button", class: "btn btn-ghost btn-small", onclick: async () => {
      if (pick.value === "off") { MIAShell.say("Off: MIA starts quietly."); return; }
      try {
        if (startupAudio) startupAudio.pause();
        const blob = await MIA.download("/api/sounds/startup/" + encodeURIComponent(pick.value));
        startupAudio = new Audio(URL.createObjectURL(blob));
        await startupAudio.play();
      } catch (e) { MIAShell.say("Couldn't play it here: " + e.message); }
    } }, "▶ Play");
  }

  // Hear each tune without earning a win first (Muse, H-0057).
  function soundCheck() {
    if (!window.MIASound) return "";
    const tunes = [["chime", "Objective"], ["quest", "Mission"], ["fanfare", "Level Up"], ["tick", "XP"]];
    return el("div", { class: "acct-actions" }, tunes.map(([name, label]) =>
      el("button", { type: "button", class: "btn btn-ghost btn-small", onclick: () => MIASound.preview(name) }, "▶ " + label)));
  }

  function breaks() {
    if (!page.breaks.length) return "";
    return group("MIA Is Taking a Break From",
      el("p", { class: "st-note st-intro" }, "You kept dismissing these, so MIA stopped sending them for a while."),
      ...page.breaks.map((b) => el("div", { class: "st-row" },
        el("div", { class: "st-text" }, el("span", {}, b.label), el("span", { class: "st-note" }, "until " + b.until)),
        el("div", { class: "st-control" }, el("button", { type: "button", class: "btn btn-ghost btn-small",
          onclick: () => act({ kind: "communication.resume", params: { topic: b.topic } }) }, "Resume")))));
  }

  // The home computer's bigger model (DEC-0022, core/home_link.py).
  function homeLink(h) {
    const status = h.linked
      ? el("p", {}, (h.reachable ? "🟢 Linked and reachable" : "⚪ Linked, not reachable right now") + " · " + h.url +
        (h.model ? " · " + h.model : "") + (h.who ? " · as " + h.who : ""))
      : el("p", { class: "dim" }, "Link this phone to MIA on your computer and Talk uses the computer's bigger model whenever it can reach it (same Wi-Fi, or Tailscale), and this phone's model when it can't. Your data stays on your devices.");
    const connect = async () => {
      const v = await MIAShell.form("Link The Home Computer", [
        { name: "url", label: "The computer's address (e.g. 192.168.1.20:8765 or its Tailscale name)", type: "text", required: true, options: [], default: h.url || null },
        { name: "who", label: "Your name or email on MIA there", type: "text", required: true, options: [], default: h.who || null },
        { name: "password", label: "Your password there", type: "password", required: true, options: [], default: null }], {});
      if (!v) return;
      try { MIAShell.say((await MIA.homeConnect(v.url, v.who, v.password)).message); page = await MIA.settings(); draw(); }
      catch (e) { MIAShell.say(e.message); }
    };
    const disconnect = async () => {
      try { MIAShell.say((await MIA.homeDisconnect()).message); page = await MIA.settings(); draw(); } catch (e) { MIAShell.say(e.message); }
    };
    // Two-way sync (core/sync.py) and the heavy jobs the computer takes (core/heavy_jobs.py).
    const s = h.sync || {};
    const ago = (iso) => {
      if (!iso) return "not yet";
      const min = Math.round((Date.now() - new Date(iso).getTime()) / 60000);
      return min < 1 ? "just now" : min < 60 ? min + " min ago" : new Date(iso).toLocaleString(undefined, { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" });
    };
    const syncNow = async () => {
      MIAShell.say("Syncing with the home computer…");
      try { MIAShell.say((await MIA.syncNow()).message); page = await MIA.settings(); draw(); }
      catch (e) { MIAShell.say(e.message); }
    };
    const syncInfo = h.linked ? [
      el("p", {}, "🔄 Sync: " + (s.problem ? "⚠ " + s.problem : "last synced " + ago(s.last)) +
        ". Changes on this phone and the computer show up on both, by themselves, photos and files too."),
      s.note ? el("p", { class: "dim" }, "⚠ " + s.note) : "",
      el("p", { class: "dim" }, "When this phone can't, the computer reads your photos and receipts, hears you, and speaks for MIA."),
    ] : [];
    return section("Home Computer", status, ...syncInfo, el("div", { class: "acct-actions" },
      el("button", { type: "button", class: "btn btn-amber", onclick: connect }, h.linked ? "Link Again" : "Link"),
      h.linked ? el("button", { type: "button", class: "btn btn-ghost", onclick: syncNow }, "Sync Now") : "",
      h.linked ? el("button", { type: "button", class: "btn btn-ghost", onclick: disconnect }, "Unlink") : ""));
  }

  // Pairing with the glasses' sealed relay (DEC-0062) lives in the phone app, so this shows only there.
  function glassesSection() {
    const relay = window.MIARelay;
    if (!relay) return "";
    const body = el("div", {});
    const box = section("Glasses", body);
    let drawn = "";
    const draw = () => {
      const state = JSON.parse(relay.state());
      const key = state.stage + state.check + state.connected;
      if (key === drawn) return;
      drawn = key;
      if (state.stage === "unpaired") {
        const code = el("input", { type: "text", inputmode: "numeric", maxlength: "6", placeholder: "6 digits", "aria-label": "Code on your glasses" });
        body.replaceChildren(el("p", { class: "dim" }, "Open MIA on your glasses and enter the code she shows."), code,
          el("div", { class: "acct-actions" }, el("button", { type: "button", class: "btn btn-amber", onclick: () => relay.pair(code.value.trim()) }, "Pair")));
      } else if (state.stage === "pairing" || state.stage === "confirming") {
        body.replaceChildren(el("p", { class: "dim" }, "Looking for your glasses..."),
          el("div", { class: "acct-actions" }, el("button", { type: "button", class: "btn btn-ghost", onclick: () => relay.cancel() }, "Cancel")));
      } else if (state.stage === "check") {
        body.replaceChildren(el("p", {}, "Check this matches your glasses: " + state.check.slice(0, 4) + " " + state.check.slice(4)),
          el("div", { class: "acct-actions" },
            el("button", { type: "button", class: "btn btn-amber", onclick: () => relay.confirm() }, "They Match"),
            el("button", { type: "button", class: "btn btn-ghost", onclick: () => relay.cancel() }, "They Don't")));
      } else {
        body.replaceChildren(el("p", { class: "dim" }, state.connected ? "Paired. Your glasses can reach MIA." : "Paired. Connecting..."),
          el("div", { class: "acct-actions" }, el("button", { type: "button", class: "btn btn-ghost", onclick: () => relay.unpair() }, "Unpair Glasses")));
      }
    };
    draw();
    const watch = setInterval(() => { if (box.isConnected) draw(); else clearInterval(watch); }, 700);
    return box;
  }

  // Starter sets (core/starter_actions.py): the usual chores, upkeep and routines for a kind of life, each part ticked
  // or left out; starter.add adds them as one change that Undo takes back. By voice: "add the homestead starter set".
  function starterSets() {
    if (!page.starters || !page.starters.length) return "";
    return section("Starter Sets", el("p", { class: "dim" }, "Fill MIA in with the usual for a kind of life. Leave out any part you don't need; nothing already here is added twice."),
      ...page.starters.map((s) => {
        const boxes = s.parts.map((p) => el("label", { class: "st-part" }, el("input", { type: "checkbox", value: p.id, checked: true }), el("span", {}, p.label)));
        return el("details", { class: "st-set" }, el("summary", {}, el("strong", {}, s.name), el("span", { class: "dim" }, " · " + s.description)),
          el("div", { class: "st-parts" }, boxes),
          el("button", { type: "button", class: "btn btn-ghost btn-small", onclick: () => {
            const parts = boxes.map((b) => b.firstChild).filter((b) => b.checked).map((b) => b.value);
            if (!parts.length) { MIAShell.say("Tick at least one part."); return; }
            act({ kind: "starter.add", params: { starter_id: s.id, parts: parts.join(",") } });
          } }, "Add " + s.name));
      }));
  }

  // MIA's voice (core/web_voice.py), for the PC's owner: the voices installed, the AI voice effect (Piper voices) and
  // the volume. Changed at once (device-wide; pick the old one again to go back). By voice: "switch to the British voice".
  let voices = null;
  async function chooseVoice(change) {
    try { MIAShell.say((await MIA.chooseVoice(change)).said); voices = await MIA.voiceChoice(); draw(); }
    catch (e) { MIAShell.say(e.message); }
  }
  function voiceSection() {
    if (!voices || !voices.available) return "";
    if (!voices.voices.length) return section("MIA's Voice", el("p", { class: "dim" }, "No voices are installed on this computer yet."));
    const pick = el("select", { "aria-label": "MIA's voice", onchange: () => chooseVoice({ voice_id: pick.value }) },
      voices.voices.map((v) => el("option", { value: v.id, selected: v.id === voices.current ? true : null }, v.name)));
    const effect = el("input", { type: "checkbox", role: "switch", checked: voices.effect ? true : null, "aria-label": "AI voice effect" });
    effect.addEventListener("change", () => chooseVoice({ effect: effect.checked }));
    const vol = el("input", { type: "range", min: "0", max: "150", step: "5", value: String(voices.volume), "aria-label": "MIA's volume" });
    const shown = el("span", { class: "dim" }, voices.volume + "%");
    vol.addEventListener("input", () => { shown.textContent = vol.value + "%"; });
    vol.addEventListener("change", () => chooseVoice({ volume: Number(vol.value) }));
    return section("MIA's Voice",
      el("label", { class: "vc-row" }, el("span", {}, "Voice"), pick),
      el("label", { class: "vc-row" }, el("span", {}, "AI voice effect (Piper voices)"), el("span", { class: "switch" }, effect, el("span", { "aria-hidden": "true" }))),
      el("label", { class: "vc-row" }, el("span", {}, "Volume"), vol, shown));
  }

  // Backups (core/web_backups.py), for the PC's owner: how long since the last one, the newest few, and Back Up Now
  // with an optional passphrase (sent once, never kept). Restoring is on the PC. By voice: "when did I last back up?"
  let backups = null;
  function backupSection() {
    if (!backups) return "";
    const pass = el("input", { type: "password", autocomplete: "new-password", placeholder: "Passphrase (optional, 8+)", "aria-label": "Backup passphrase" });
    return section("Backups",
      el("p", { class: "dim" }, backups.count ? "Last backup " + backups.last + ". Saved in " + backups.folder + "." : "No backups yet. They're saved in " + backups.folder + "."),
      backups.backups.length ? el("ul", { class: "bk-list" }, backups.backups.map((b) => el("li", {},
        el("span", {}, b.when), el("span", { class: "dim" }, b.size + (b.locked ? " · passphrase" : ""))))) : null,
      el("div", { class: "acct-actions bk-make" }, pass, el("button", { type: "button", class: "btn btn-amber", onclick: async (ev) => {
        ev.target.disabled = true;
        try { const done = await MIA.backupNow(pass.value); pass.value = ""; MIAShell.say("Backed up: " + done.made); backups = await MIA.backups(); draw(); }
        catch (e) { MIAShell.say(e.message); ev.target.disabled = false; }
      } }, "Back Up Now")),
      el("p", { class: "dim" }, "With a passphrase the backup is encrypted; keep it somewhere safe, it can't be recovered. Restoring is on the PC."));
  }

  function draw() {
    $("panel").replaceChildren(
      ...page.groups.map((g) => group(g.title, ...g.settings.map(setting), g.title === "Sound" ? soundCheck() : null)),
      breaks(),
      page.home_link ? homeLink(page.home_link) : "",
      page.model_test ? section("MIA's model on this phone",
        el("p", { class: "dim" }, "Download a small AI model, run it on this phone, and see how fast and how right it is. Talk uses it once it's running."),
        el("div", { class: "acct-actions" }, el("a", { class: "btn btn-ghost", href: "model-test.html" }, "Model test"))) : "",
      glassesSection(),
      voiceSection(),
      starterSets(),
      backupSection(),
      section("My Places", el("p", { class: "dim" }, "Places where arriving opens something: your workout at the gym, your grocery list at the store."),
        el("div", { class: "acct-actions" }, el("a", { class: "btn btn-ghost", href: "places.html" }, "My Places"))),
      section("Notifications", el("p", { class: "dim" }, "Everything MIA has told you, and why she sent the ones she sent on her own."),
        el("div", { class: "acct-actions" }, el("a", { class: "btn btn-ghost", href: "notifications.html" }, "Notifications"))),
      section("Recent Changes", el("p", { class: "dim" }, "What MIA changed lately, with Undo, and the last two weeks' history."),
        el("div", { class: "acct-actions" }, el("a", { class: "btn btn-ghost", href: "changes.html" }, "Recent Changes"))),
      section("Connect Apps", el("p", { class: "dim" }, "Bring in data from your other apps: a calendar, contacts, a bank statement, a rental's calendar link. You see it before anything changes."),
        el("div", { class: "acct-actions" }, el("a", { class: "btn btn-ghost", href: "connect.html" }, "Connect Apps"))),
      section("Apps", el("p", { class: "dim" }, "Choose which apps you see, and your favorites."),
        el("div", { class: "acct-actions" }, el("a", { class: "btn btn-ghost", href: "apps.html#manage" }, "Choose apps"))),
      section("Account", el("div", { class: "acct-actions" },
        el("a", { class: "btn btn-ghost", href: "profile.html" }, "Profile"),
        el("button", { type: "button", class: "btn btn-ghost", onclick: async () => { await MIA.signOut(); location.href = "index.html"; } }, "Log out"))));
  }

  MIAShell.start(async () => {
    page = await MIA.settings();
    try { backups = await MIA.backups(); } catch (e) { backups = null; }  // the PC owner's only
    try { voices = await MIA.voiceChoice(); } catch (e) { voices = null; }  // the PC owner's only
    draw();
  });
})();
