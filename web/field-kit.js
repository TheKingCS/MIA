/*
 * field-kit.js — the Field Kit (claude, 2026-11-07, DEC-0125; the design
 * canvas's Field Kit, DEC-0113). Renders MIA.fieldKit()
 * (core/web_field_kit.py) in three tabs: Devices (what's plugged into the
 * computer), Network (a hash's kind and a subnet, worked out in core by
 * MIA.fieldKitCheck as you type) and Scripts (the library, each to read and
 * copy). Ejecting, running scripts and the port scan stay on the PC; this
 * page says so and links there. Formatting only.
 */
(function () {
  "use strict";
  const { el } = MIAShell;
  const $ = (id) => document.getElementById(id);
  const TABS = [["devices", "Devices"], ["network", "Network"], ["scripts", "Scripts"]];
  let page = null;
  let tab = TABS.some(([t]) => t === location.hash.slice(1)) ? location.hash.slice(1) : "devices";
  const typed = {};
  let timer = 0;
  let asked = 0;

  const pcLink = (ask) => el("a", { class: "btn btn-ghost btn-small", href: MIA.desktop ? "/desktop-open/field_kit" : "assistant.html?ask=" + encodeURIComponent(ask) }, MIA.desktop ? "Open on the PC" : "Ask MIA");

  function row(name, detail, right) {
    return el("div", { class: "fk-row" }, el("div", { class: "fk-row-main" }, el("span", { class: "tb-row-name" }, name),
      detail ? el("span", { class: "dim" }, detail) : null), right || null);
  }

  function devices() {
    const d = page.devices;
    if (!d.available) return [el("p", { class: "empty" }, "This MIA can't look for devices.")];
    const storage = d.storage.map((s) => row(s.name, [s.via, s.fstype, s.mounted ? "mounted at " + s.mounted : "not mounted"].filter(Boolean).join(" · "),
      el("span", { class: "fk-tag ok" }, "Connected")));
    const serial = d.serial.map((s) => row(s.name, s.board ? s.description : "A USB serial port", el("span", { class: "fk-tag" }, s.port)));
    return [
      el("section", { class: "glass tb-list" }, el("p", { class: "pw-label" }, "Storage"),
        ...(storage.length ? storage : [el("p", { class: "dim" }, "No USB drives or SD cards plugged in.")])),
      el("section", { class: "glass tb-list" }, el("p", { class: "pw-label" }, "Boards and serial"),
        ...(serial.length ? serial : [el("p", { class: "dim" }, "No boards plugged in.")])),
      el("div", { class: "fk-pc" }, el("p", { class: "dim" }, "Ejecting or flashing a drive is done on the PC, beside it."), pcLink("What's plugged into the computer?")),
    ];
  }

  function answer(box, r) {
    if (r.error) { box.replaceChildren(el("p", { class: "dim" }, r.error)); return; }
    box.replaceChildren(...[el("div", { class: "tb-answer-main" }, r.answer),
      el("dl", { class: "tb-lines" }, ...r.lines.flatMap(([k, v]) => [el("dt", {}, k), el("dd", {}, v)])),
      r.demo ? el("p", { class: "dim" }, "The demo shows the example's answer.") : null].filter(Boolean));
  }

  function checkCard(c) {
    const out = el("div", { class: "tb-answer", "aria-live": "polite" }, el("p", { class: "dim" }, c.about));
    const box = el("input", { class: "tb-input", type: "text", autocomplete: "off", spellcheck: "false", placeholder: c.placeholder,
      value: typed[c.id] || "", "aria-label": c.name });
    box.addEventListener("input", () => {
      typed[c.id] = box.value;
      clearTimeout(timer);
      timer = setTimeout(async () => {
        const mine = ++asked;
        let r;
        try { r = await MIA.fieldKitCheck(c.id, box.value); } catch (e) { r = { error: e.message }; }
        if (mine === asked) answer(out, r);
      }, 250);
    });
    return el("section", { class: "glass tb-calc" }, el("div", { class: "tb-calc-head" }, el("h2", {}, c.name)), box, out);
  }

  function network() {
    return [el("div", { class: "fk-checks" }, ...page.checks.map(checkCard)),
      el("div", { class: "fk-pc" }, el("p", { class: "dim" }, "The port scan runs on the PC: it opens a connection to each port."), pcLink("Scan the common ports on my router"))];
  }

  async function copy(s, button) {
    try { await navigator.clipboard.writeText(s.content); button.textContent = "Copied"; } catch (e) { button.textContent = "Select and copy"; }
    setTimeout(() => { button.textContent = "Copy"; }, 1600);
  }

  function scriptCard(s) {
    const copyBtn = el("button", { type: "button", class: "btn btn-ghost btn-small" }, "Copy");
    copyBtn.addEventListener("click", () => copy(s, copyBtn));
    return el("details", { class: "glass fk-script" },
      el("summary", {}, el("span", { class: "tb-row-name" }, s.name),
        el("span", { class: "dim" }, s.interpreter + " · " + s.lines + (s.lines === 1 ? " line" : " lines"))),
      el("pre", { class: "fk-code" }, el("code", {}, s.content || "(empty)")),
      s.cut ? el("p", { class: "dim" }, "Long script: the start is shown here; all of it is on the PC.") : null,
      el("div", { class: "row-buttons" }, copyBtn));
  }

  function scripts() {
    if (!page.scripts.length) return [el("p", { class: "empty" }, "No scripts saved yet. Add them on the PC, in the Field Kit's Scripts tab.")];
    return [...page.categories.map((cat) => el("section", { class: "fk-cat" }, el("p", { class: "pw-label" }, cat),
      ...page.scripts.filter((s) => s.category === cat).map(scriptCard))),
    el("div", { class: "fk-pc" }, el("p", { class: "dim" }, "Running a script is done on the PC, where its output can be watched and stopped."), pcLink("List my scripts"))];
  }

  function draw() {
    if (window.MIAIcons) MIAIcons.badge($("hero-icon"), "field_kit");
    const n = page.devices.storage.length + page.devices.serial.length;
    $("fk-sub").textContent = (n ? n + (n === 1 ? " device" : " devices") + " plugged in · " : "") + page.scripts.length + (page.scripts.length === 1 ? " script." : " scripts.");
    $("tabs").hidden = false;
    $("tabs").replaceChildren(...TABS.map(([id, l]) => el("button", { type: "button", role: "tab", "aria-selected": String(id === tab),
      onclick: () => { tab = id; history.replaceState(null, "", "#" + id); draw(); } }, l)));
    $("panel").replaceChildren(...(tab === "network" ? network() : tab === "scripts" ? scripts() : devices()));
  }

  MIAShell.start(async () => {
    page = await MIA.fieldKit();
    if (!page.available) { $("panel").replaceChildren(el("p", { class: "empty" }, "The Field Kit isn't on this MIA.")); return; }
    draw();
  });
})();
