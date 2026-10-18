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

  const setting = (s) => el("div", { class: "setting" + (s.kind === "text" ? " wide" : "") },
    el("label", { for: "s-" + s.key.replace(/\./g, "-") }, s.label), control(s),
    s.help ? el("p", { class: "help" }, s.help) : "");

  // Hear each tune without earning a win first (Muse, H-0057).
  function soundCheck() {
    if (!window.MIASound) return "";
    const tunes = [["chime", "Objective"], ["quest", "Mission"], ["fanfare", "Level Up"], ["tick", "XP"]];
    return el("div", { class: "acct-actions" }, tunes.map(([name, label]) =>
      el("button", { type: "button", class: "btn btn-ghost btn-small", onclick: () => MIASound.preview(name) }, "▶ " + label)));
  }

  function breaks() {
    if (!page.breaks.length) return "";
    return section("Taking a break from",
      el("p", { class: "dim" }, "You kept dismissing these, so MIA stopped sending them for a while."),
      el("div", { class: "rows" }, page.breaks.map((b) => el("div", { class: "row" },
        el("div", {}, el("div", { class: "row-title" }, b.label), el("div", { class: "row-sub" }, "until " + b.until)),
        el("button", { type: "button", class: "btn btn-ghost", onclick: () => act({ kind: "communication.resume", params: { topic: b.topic } }) },
          "Bring it back")))));
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
    return section("Home Computer", status, el("div", { class: "acct-actions" },
      el("button", { type: "button", class: "btn btn-amber", onclick: connect }, h.linked ? "Link Again" : "Link"),
      h.linked ? el("button", { type: "button", class: "btn btn-ghost", onclick: disconnect }, "Unlink") : ""));
  }

  function draw() {
    $("panel").replaceChildren(
      ...page.groups.map((g) => section(g.title, ...g.settings.map(setting), g.title === "Sound" ? soundCheck() : "")),
      breaks(),
      page.home_link ? homeLink(page.home_link) : "",
      page.model_test ? section("MIA's model on this phone",
        el("p", { class: "dim" }, "Download a small AI model, run it on this phone, and see how fast and how right it is. Talk uses it once it's running."),
        el("div", { class: "acct-actions" }, el("a", { class: "btn btn-ghost", href: "model-test.html" }, "Model test"))) : "",
      section("My Places", el("p", { class: "dim" }, "Places where arriving opens something: your workout at the gym, your grocery list at the store."),
        el("div", { class: "acct-actions" }, el("a", { class: "btn btn-ghost", href: "places.html" }, "My Places"))),
      section("Apps", el("p", { class: "dim" }, "Choose which apps you see, and your favorites."),
        el("div", { class: "acct-actions" }, el("a", { class: "btn btn-ghost", href: "apps.html#manage" }, "Choose apps"))),
      section("Account", el("div", { class: "acct-actions" },
        el("a", { class: "btn btn-ghost", href: "profile.html" }, "Profile"),
        el("button", { type: "button", class: "btn btn-ghost", onclick: async () => { await MIA.signOut(); location.href = "index.html"; } }, "Log out"))));
  }

  MIAShell.start(async () => {
    page = await MIA.settings();
    draw();
  });
})();
