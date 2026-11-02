/*
 * sync.js — User Sync on the phone (claude, 2026-11-02).
 * Renders MIA.userSync() (core/user_sync.py): the question, a box to type
 * the answer, the chips to approve, and the phone's permissions, asked
 * through window.MIAPhonePermissions (Permissions.kt) and reported back.
 * The steps and words are all the engine's. Formatting only.
 */
(function () {
  "use strict";
  const { el } = MIAShell;
  const $ = (id) => document.getElementById(id);
  const phone = window.MIAPhonePermissions;
  const POLL_MS = 3000;
  let shown = "", shownQuestion = "", lead = "", draft = null;

  async function step(body) {
    try { paint(await MIA.userSyncStep(body)); }
    catch (err) { MIAShell.say(err.message); }
  }

  function report() {
    if (phone) return step({ permissions: JSON.parse(phone.status()) });
  }
  window.MIAPermissions = { changed: report };  // Permissions.kt, once Android has answered

  const button = (label, onclick, cls) => el("button", { type: "button", class: "btn " + (cls || "btn-ghost"), onclick }, label);

  function askRows(s) {
    return el("div", { class: "sync-rows" }, s.rows.map((r) => el("div", { class: "sync-row" },
      el("span", {}, r.label),
      r.status === "allowed" ? el("span", { class: "dim" }, "Allowed")
        : phone ? button("Allow", () => phone.ask(r.id), "btn-amber btn-small")
          : el("span", { class: "dim" }, "In the MIA app"))));
  }

  function answerBox() {
    const box = el("textarea", { class: "sync-box", rows: "3", "aria-label": "Your answer", placeholder: "Type your answer" });
    box.value = draft || "";
    box.oninput = () => { draft = box.value; };
    const send = () => { const text = box.value.trim(); if (text) { draft = null; step({ text }); } };
    return [box, el("div", { class: "row-buttons" }, button("Send", send, "btn-amber"), button("Skip That One", () => step({ choice: "skip" })))];
  }

  function chips(s) {
    return el("div", { class: "sync-chips" }, s.chips.map((c, i) => el("div", { class: "sync-chip" },
      el("span", {}, el("span", { class: "dim" }, c.app + " · "), c.text),
      el("button", { type: "button", class: "sync-x", "aria-label": "Drop " + c.text, onclick: () => step({ choice: "drop", index: i }) }, "×"))));
  }

  function body(s) {
    if (s.step === "phone") return [askRows(s), el("div", { class: "row-buttons" }, button("Skip This For Now", () => step({ choice: "skip" })))];
    if (s.step === "next") return [el("div", { class: "row-buttons" }, button("Keep Going", () => step({ choice: "continue" }), "btn-amber"), button("Skip This Topic", () => step({ choice: "skip" })))];
    if (s.step === "review") return [chips(s), el("div", { class: "row-buttons" }, button("Looks Right", () => step({ choice: "approve" }), "btn-amber"))];
    return answerBox();
  }

  function paint(s) {
    if (s.say) lead = s.say.replace(s.question, "").trim();  // what came before the question
    else if (s.question !== shownQuestion) lead = "";
    shownQuestion = s.question;
    const seen = JSON.stringify({ ...s, say: "" });
    if (seen === shown && !s.say) return;
    if (seen !== shown && shown) draft = s.step === "ask" && JSON.parse(shown).question === s.question ? draft : null;
    shown = seen;
    $("sync-where").textContent = s.done ? "All caught up." : s.step === "phone" ? "Your phone first." : "Topic " + s.number + " of " + s.topics + " · " + s.title;
    if (s.done || s.paused || s.offer) {
      const start = s.done ? null : button(s.paused ? "Pick It Back Up" : "Start", () => step({ choice: "start" }), "btn-amber");
      $("panel").replaceChildren(el("section", { class: "glass money-section" },
        el("p", {}, s.done ? (lead || "That's everything for now. You can tell me more any time.") : (s.paused ? lead || "We'll pick this up whenever you like." : "A few questions, so MIA can set things up for you.")),
        el("div", { class: "row-buttons" }, start, el("a", { class: "btn btn-ghost", href: "index.html" }, "Home"))));
      return;
    }
    $("panel").replaceChildren(el("section", { class: "glass money-section" },
      lead ? el("p", { class: "dim" }, lead) : null,
      el("h2", { class: "sync-q" }, s.question),
      s.heard ? el("p", { class: "dim" }, "You said: “" + s.heard + "”") : null,
      ...body(s),
      el("div", { class: "row-buttons" }, button("Finish Later", () => step({ choice: "later" }))),
      el("div", { class: "bar", role: "progressbar", "aria-valuenow": String(s.percent), "aria-valuemin": "0", "aria-valuemax": "100" },
        el("div", { class: "bar-fill", style: "width:" + s.percent + "%" }))));
    if (s.step === "phone" && !sentStatus) { sentStatus = true; report(); }
  }

  let sentStatus = false;
  MIAShell.start(async () => { paint(await MIA.userSync()); });
  // The glasses may be answering: keep up, without touching a half-typed answer.
  setInterval(() => {
    if (document.activeElement && document.activeElement.className === "sync-box") return;
    MIA.userSync().then(paint).catch(() => {});
  }, POLL_MS);
})();
