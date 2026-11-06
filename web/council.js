/*
 * council.js — the council from the phone (claude, 2026-11-06, build plan step 16).
 * Renders MIA.council() (core/council.py through server/app.py): the latest
 * messages, who's here and ready, and a box to write to them. Only the PC's
 * owner gets an answer; anyone else sees why. Formatting only.
 */
(function () {
  "use strict";
  const { el } = MIAShell;
  const $ = (id) => document.getElementById(id);
  const POLL_MS = 4000;
  let draft = "", shown = "", replyTo = "";

  const button = (label, onclick, cls) => el("button", { type: "button", class: "btn " + (cls || "btn-ghost"), onclick }, label);
  const when = (iso) => { const d = new Date(iso); return isNaN(d) ? "" : d.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" }); };

  async function send() {
    const text = draft.trim();
    if (!text) return;
    try {
      await MIA.councilSay({ text, reply_to: replyTo });
      draft = ""; replyTo = "";
      refresh(true);
    } catch (err) { MIAShell.say(err.message); }
  }

  function message(m) {
    const mine = m.who === "zac";
    return el("div", { class: "sync-row council-msg" + (mine ? " mine" : "") },
      el("div", {},
        el("span", { class: "dim" }, (mine ? "You" : m.who) + " · " + when(m.at) + (m.kind && m.kind !== "message" ? " · " + m.kind : "")),
        el("p", { class: "council-text" }, m.text)),
      mine ? null : button("Reply", () => { replyTo = m.id; paintBox(); }, "btn-small"));
  }

  function paintBox() {
    const box = el("textarea", { class: "sync-box", rows: "3", "aria-label": "Your message to the council",
      placeholder: replyTo ? "Your reply (@name to ask one member)" : "To the council (@name to ask one member)" });
    box.value = draft;
    box.oninput = () => { draft = box.value; };
    $("council-box").replaceChildren(box, el("div", { class: "row-buttons" },
      button("Send", send, "btn-amber"),
      replyTo ? button("Not a reply", () => { replyTo = ""; paintBox(); }) : null));
  }

  function paint(data) {
    const seen = JSON.stringify(data);
    if (seen === shown) return;
    shown = seen;
    const ready = data.members.filter((m) => m.ready).map((m) => m.name);
    $("council-who").textContent = ready.length ? "Here and ready: " + ready.join(", ") : "Nobody's ready right now.";
    if (!$("council-box")) {
      $("panel").replaceChildren(
        el("section", { class: "glass money-section" }, el("div", { id: "council-box" })),
        el("section", { class: "glass money-section" }, el("div", { id: "council-list", class: "sync-rows" })));
      paintBox();
    }
    $("council-list").replaceChildren(...data.messages.slice().reverse().map(message));
  }

  async function refresh(force) {
    if (force) shown = "";
    try { paint(await MIA.council()); }
    catch (err) {
      $("panel").replaceChildren(el("section", { class: "glass money-section" }, el("p", {}, err.message)));
    }
  }

  MIAShell.start(() => refresh(true));
  setInterval(() => {
    if (document.activeElement && document.activeElement.className === "sync-box") return;  // never under a half-typed message
    refresh(false);
  }, POLL_MS);
})();
