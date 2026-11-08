/*
 * wallet.js — the ID wallet (claude, 2026-11-08).
 * Lists MIA.wallet() (core/id_wallet.listing: numbers masked, soonest to expire first), adds and edits cards through
 * MIA.walletSave (their own endpoint: a number never goes through an action), keeps photos of each side (sealed on the
 * PC), removes a card with the undoable wallet.delete, and shows one card full screen (?show=<id>, what "show my
 * license" opens). A copy is a backup, not the legal ID: the page says so.
 */
(function () {
  "use strict";
  const { el, act, form, say } = MIAShell;
  const $ = (id) => document.getElementById(id);
  const btn = (label, cls, onclick) => el("button", { type: "button", class: "btn " + cls + " btn-small", onclick }, label);
  const day = (iso) => iso ? new Date(iso + "T00:00:00").toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" }) : "";
  let page = null;

  const fields = () => [
    { name: "kind", label: "Kind", type: "choice", options: page.kinds },
    { name: "name", label: "Name (like “Texas driver's license”)", type: "text", required: true },
    { name: "number", label: "Number", type: "password" },
    { name: "issued_by", label: "Issued by", type: "text" },
    { name: "issued", label: "Issued", type: "date" },
    { name: "expires", label: "Expires", type: "date" },
    { name: "notes", label: "Notes", type: "textarea" }];

  async function save(card) {
    const full = card ? await MIA.walletCard(card.id) : {};
    const v = await form(card ? "Edit " + card.name : "Add a card", fields(), card ? full : { kind: page.kinds[0] });
    if (!v) return;
    try { say((await MIA.walletSave(card ? card.id : null, v)).message); MIAShell.refresh(); } catch (e) { say(e.message); }
  }

  function photo(card, side) {
    const input = el("input", { type: "file", accept: "image/jpeg,image/png,image/webp", capture: "environment", hidden: true, onchange: async () => {
      const file = input.files[0];
      input.remove();
      if (!file) return;
      try { say((await MIA.upload("/api/wallet/" + encodeURIComponent(card.id) + "/photo/" + side, file)).message); MIAShell.refresh(); }
      catch (e) { say(e.message); }
    } });
    document.body.append(input);
    input.click();
  }

  function expiry(c) {
    const e = c.expiry;
    if (e.state === "none") return c.kind;
    const text = e.state === "expired" ? "Expired " + day(c.expires) : "Expires " + day(c.expires) + (e.state === "soon" ? " · in " + e.days + " days" : "");
    return el("span", {}, c.kind + " · ", el("span", { class: e.state === "ok" ? "" : "wallet-renew" }, text));
  }

  function card(c) {
    return el("article", { class: "glass wallet-card" },
      el("div", { class: "wallet-top" },
        el("div", {}, el("h3", {}, c.name), el("p", { class: "dim" }, expiry(c)),
          c.number ? el("p", { class: "wallet-num" }, c.number) : null, c.issued_by ? el("p", { class: "dim" }, c.issued_by) : null),
        btn("Show", "btn-amber", () => show(c.id))),
      el("div", { class: "row-buttons" },
        btn((c.photos || {}).front ? "Retake Front" : "Photo of Front", "btn-ghost", () => photo(c, "front")),
        btn((c.photos || {}).back ? "Retake Back" : "Photo of Back", "btn-ghost", () => photo(c, "back")),
        btn("Edit", "btn-ghost", () => save(c)),
        btn("Remove", "btn-ghost danger", () => act({ kind: "wallet.delete", params: { card_id: c.id } }))));
  }

  // Show: the card full screen, its photos and its number in large type, the screen kept bright while it's open.
  async function show(id) {
    let c;
    try { c = await MIA.walletCard(id); } catch (e) { say(e.message); return; }
    const pics = el("div", { class: "wallet-pics" });
    for (const side of ["front", "back"]) {
      if (!(c.photos || {})[side]) continue;
      const img = el("img", { alt: c.name + ", " + side });
      pics.append(img);
      MIA.image("/api/wallet/" + encodeURIComponent(id) + "/photo/" + side).then((u) => { if (u) img.src = u; else img.remove(); });
    }
    let lock = null;
    try { lock = await navigator.wakeLock.request("screen"); } catch (e) { /* not everywhere */ }
    const dialog = el("dialog", { class: "wallet-show", "aria-label": c.name });
    const close = () => { dialog.close(); dialog.remove(); if (lock) lock.release().catch(() => {}); history.replaceState(null, "", "wallet.html" + (location.search.includes("demo") ? "?demo" : "")); };
    dialog.append(el("div", { class: "wallet-show-in" },
      el("p", { class: "pw-label" }, c.kind), el("h2", {}, c.name), pics,
      c.number ? el("p", { class: "wallet-show-num" }, c.number) : null,
      el("p", { class: "dim" }, [c.issued_by, c.expires ? "Expires " + day(c.expires) : null].filter(Boolean).join(" · ")),
      el("p", { class: "dim wallet-note" }, page.note),
      el("button", { type: "button", class: "btn btn-green", onclick: close }, "Done")));
    dialog.oncancel = (e) => { e.preventDefault(); close(); };
    document.body.append(dialog);
    dialog.showModal();
  }

  MIAShell.start(async () => {
    page = await MIA.wallet();
    $("panel").replaceChildren(
      el("div", { class: "row-buttons" }, btn("Add a card", "btn-green", () => save(null))),
      page.cards.length ? el("div", { class: "wallet-grid" }, page.cards.map(card))
        : el("p", { class: "empty" }, "Your license, passport, insurance cards and registrations: photos of each side, the number, and a reminder before it expires. Kept encrypted on your PC."),
      el("p", { class: "dim wallet-note" }, page.note));
    const want = new URLSearchParams(location.search).get("show");
    if (want) show(want);
  });
})();
