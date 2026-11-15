/*
 * selection.js — Do With This (claude, 2026-11-15, the Universal Action Layer's U2, DEC-0165).
 *
 * The card over another app on the phone: the selection (from the MIASelection bridge, SelectionActivity.kt; in the
 * public demo, a sample), what MIA can do with it, and the pick:
 * - a read action shows its result here, with Copy and links that open MIA;
 * - an act action shows the sentence of what it would change and waits for Yes; then Undo is offered.
 * Everything is decided by the engine (core/ual.py through /api/ual/*); this file only formats. Without the bridge
 * (a browser), Close goes back.
 */
(function () {
  "use strict";
  const $ = (id) => document.getElementById(id);
  const bridge = window.MIASelection || null;
  const demo = new URLSearchParams(location.search).has("demo");
  const SAMPLE = { text: "Stake tomatoes before they flower: a single stake for determinate kinds, a cage or string for vining ones.",
    title: "Gardening blog", source_app: "android:com.android.chrome", device: "phone" };

  function el(tag, attrs, ...kids) {
    const node = document.createElement(tag);
    Object.entries(attrs || {}).forEach(([k, v]) => {
      if (v == null || v === false) return;
      if (k.startsWith("on")) node.addEventListener(k.slice(2), v); else node.setAttribute(k, v === true ? "" : v);
    });
    kids.flat().filter((k) => k != null && k !== false).forEach((k) => node.append(k.nodeType ? k : String(k)));
    return node;
  }
  const btn = (label, cls, onclick) => el("button", { type: "button", class: "btn " + cls, onclick }, label);
  const close = () => { if (bridge) bridge.done(); else history.back(); };
  const show = (...kids) => $("body").replaceChildren(...kids.flat().filter(Boolean));
  const problem = (e) => show(el("p", { class: "sel-note" }, e.message || String(e)), btn("Close", "btn-ghost", close));

  function capture() {
    if (bridge) { try { return JSON.parse(bridge.capture()); } catch (e) { return {}; } }
    return demo ? SAMPLE : {};
  }
  // A result's link opens that page in MIA (on the phone, MIA comes forward and the card closes).
  function open(href) {
    return (event) => {
      if (!bridge) return;
      event.preventDefault();
      bridge.openInMia(href);
    };
  }

  function result(r) {
    const text = r.text || "Done.";
    return [el("p", { class: "sel-result" }, text),
      (r.results || []).length ? el("ul", { class: "sel-list" }, r.results.map((x) =>
        el("li", {}, el("a", { href: x.href, onclick: open(x.href) }, x.title), x.detail ? el("span", { class: "sel-dim" }, " · " + x.detail) : null))) : null,
      el("div", { class: "row-buttons" }, bridge ? btn("Copy", "btn-ghost", () => bridge.copy(text)) : null, btn("Done", "btn-green", close))];
  }

  async function approve(proposal) {
    try {
      const done = await MIA.approve(proposal.proposal_id);
      show(el("p", { class: "sel-result" }, done.result || "Done."),
        el("div", { class: "row-buttons" },
          done.undoable ? btn("Undo", "btn-ghost", async () => {
            try { await MIA.undo(done.proposal_id); show(el("p", { class: "sel-result" }, "Undone."), btn("Done", "btn-green", close)); }
            catch (e) { problem(e); }
          }) : null,
          btn("Done", "btn-green", close)));
    } catch (e) { problem(e); }
  }

  function ask(proposal) {
    show(el("p", { class: "sel-dim" }, "This changes something, so it waits for you:"),
      el("p", { class: "sel-result" }, proposal.summary),
      el("div", { class: "row-buttons" },
        btn("Yes, Do It", "btn-green", () => approve(proposal)),
        btn("No", "btn-ghost", () => { MIA.reject(proposal.proposal_id).catch(() => {}); close(); })));
  }

  async function pick(action, c) {
    show(el("p", { class: "sel-dim" }, action.label + "…"));
    try {
      const got = await MIA.ualRun(action.id, c);
      if (got.tier === "act") ask(got.proposal); else show(result(got.result || {}));
    } catch (e) { problem(e); }
  }

  async function start() {
    const c = capture();
    const text = String(c.text || "").trim();
    if (!text) { show(el("p", { class: "sel-note" }, "There's no text to act on."), btn("Close", "btn-ghost", close)); return; }
    $("text").textContent = text.length > 320 ? text.slice(0, 320) + "…" : text;
    $("from").textContent = c.title ? "From " + c.title : "";
    let found;
    try { found = await MIA.ualOffer(c); } catch (e) { problem(e); return; }
    if (found.capture && found.capture.missing && found.capture.missing.length) {
      $("from").textContent += ($("from").textContent ? " · " : "") + "Not kept: " + found.capture.missing.join(", ");
    }
    const rows = (found.actions || []).map((a) => el("li", {},
      el("button", { type: "button", class: "sel-action", onclick: () => pick(a, c) },
        el("span", { class: "sel-label" }, a.label),
        el("span", { class: "sel-dim" }, a.needs_approval ? "Asks first" : "Right away"))));
    show(rows.length ? el("ul", { class: "sel-actions" }, rows) : el("p", { class: "sel-note" }, "There's nothing I can do with that yet."),
      (found.later || []).length ? el("p", { class: "sel-dim" }, "Coming: " + found.later.slice(0, 5).join(", ") + ".") : null);
  }

  $("close").addEventListener("click", close);
  start();
})();
