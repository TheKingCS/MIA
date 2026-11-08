/*
 * journal.js — the Journal screen (claude, 2026-10-16; Zac: the app only
 * opened a chat). Renders MIA.journal() (core/web_more.py): entries newest
 * first, search, tags; an entry opens to read in full with Edit and Delete.
 * Write Entry proposes journal.add. Talk It Out opens the chat to journal
 * with MIA (those entries stay private and encrypted). Formatting only.
 */
(function () {
  "use strict";
  const { el, act, form } = MIAShell;
  const $ = (id) => document.getElementById(id);
  let page = null, query = "", tag = "";

  const btn = (label, cls, onclick) => el("button", { type: "button", class: "btn " + cls, onclick }, label);
  const day = (iso) => iso ? new Date(iso + "T00:00:00").toLocaleDateString(undefined, { weekday: "short", month: "short", day: "numeric", year: "numeric" }) : "";

  async function write() {
    const v = await form("Write Entry", page.forms.journal.fields, {});
    if (v) act({ kind: "journal.add", params: v });
  }
  async function edit(e) {
    const v = await form("Edit " + e.title, page.forms.journal.fields, e.values);
    if (v) act({ kind: "journal.edit", params: Object.assign({ entry_id: e.id }, v) });
  }

  function open(e) {
    const dialog = el("dialog", { class: "confirm form-dialog mission-sheet", "aria-label": e.title });
    const close = () => { dialog.close(); dialog.remove(); };
    dialog.append(
      el("h3", {}, e.title),
      el("p", { class: "dim" }, [day(e.date), e.conditions, e.trip ? "Trip: " + e.trip : null].filter(Boolean).join(" · ")),
      e.tags.length ? el("div", { class: "chip-row" }, e.tags.map((t) => el("span", { class: "chip" }, "#" + t))) : null,
      el("div", { class: "journal-body" }, e.body || "(No words yet.)"),
      el("div", { class: "confirm-actions" },
        btn("Edit", "btn-amber", () => { close(); edit(e); }),
        btn("Delete", "btn-ghost", () => { close(); act({ kind: "journal.delete", params: { entry_id: e.id } }); }),
        btn("Close", "btn-ghost", close)));
    dialog.oncancel = (ev) => { ev.preventDefault(); close(); };
    document.body.append(dialog);
    dialog.showModal();
  }

  // The canvas's entry (DEC-0113): the date and its first tag on a top line, then the title and the start of it.
  const shortDay = (iso) => iso ? new Date(iso + "T00:00:00").toLocaleDateString(undefined, { weekday: "short", day: "2-digit", month: "short" }) : "";
  function card(e) {
    return el("article", { class: "glass journal-card", tabindex: "0", role: "button", "aria-label": "Open " + e.title,
      onclick: () => open(e), onkeydown: (ev) => { if (ev.key === "Enter" || ev.key === " ") { ev.preventDefault(); open(e); } } },
    el("div", { class: "journal-top" }, el("span", { class: "journal-date" }, shortDay(e.date)),
      e.tags.length ? el("span", { class: "journal-tag" }, e.tags.join(" · ")) : null),
    el("h3", {}, e.title),
    e.preview ? el("p", { class: "journal-preview" }, e.preview) : null);
  }

  function matches(e) {
    if (tag && !e.tags.includes(tag)) return false;
    if (!query) return true;
    const hay = (e.title + " " + e.body + " " + e.tags.join(" ") + " " + e.conditions).toLowerCase();
    return query.toLowerCase().split(/\s+/).filter(Boolean).every((w) => hay.includes(w));
  }

  function draw() {
    const c = page.counts;
    $("strip").replaceChildren(
      el("div", { class: "cell ok" }, el("span", { class: "n" }, c.entries), el("span", { class: "t" }, "Entries")),
      el("div", { class: "cell ok" }, el("span", { class: "n" }, c.this_month), el("span", { class: "t" }, "This Month")),
      el("div", { class: "cell soon" }, el("span", { class: "n" }, page.private.count), el("span", { class: "t" }, "Private")));
    const search = el("input", { type: "search", class: "journal-search", placeholder: "Search your journal…", value: query,
      "aria-label": "Search your journal", oninput: (ev) => { query = ev.target.value; list(); } });
    const tags = page.tags.length ? el("div", { class: "chip-row tag-filter" },
      el("button", { type: "button", class: "chip chip-button" + (tag ? "" : " on"), onclick: () => { tag = ""; draw(); } }, "All"),
      page.tags.map((t) => el("button", { type: "button", class: "chip chip-button" + (tag === t.tag ? " on" : ""),
        onclick: () => { tag = tag === t.tag ? "" : t.tag; draw(); } }, "#" + t.tag + " " + t.count))) : null;
    const listBox = el("div", { id: "journal-list" });
    $("panel").replaceChildren(
      el("div", { class: "journal-actions" },
        btn("Write Entry", "btn-green", write),
        btn("Talk It Out", "btn-ghost", () => { location.href = "assistant.html?draft=" + encodeURIComponent("I want to journal."); })),
      el("p", { class: "dim journal-private" }, page.private.count
        ? "Talk It Out entries (" + page.private.count + ") stay private and encrypted on this account. Ask MIA about them with your passphrase on the PC."
        : "Talk It Out entries stay private and encrypted on this account."),
      captures(page.captures), search, tags, listBox);
    list();
  }

  // MIA Lite's recordings waiting for review (core/web_proposals.field_captures, the Toolbox's Field Captures): the
  // words as heard, Keep It puts them in the journal (capture.keep), Leave It Out doesn't. Check For New looks in the
  // capture folder (transcribed with the PC's voice).
  function captures(box) {
    if (!box || !box.available) return null;
    const check = async () => {
      const r = await MIA.checkCaptures().catch((e) => ({ error: e.message }));
      MIAShell.say(r.error || (r.found ? r.found + " new recording" + (r.found === 1 ? "" : "s") + "." : "Nothing new."));
      if (r.found) { page = await MIA.journal(); draw(); }
    };
    return el("section", { class: "glass money-section journal-captures", "aria-label": "Field recordings" },
      el("span", { class: "pw-label" }, "From the Field" + (box.captures.length ? " · " + box.captures.length + " to review" : "")),
      box.captures.length ? el("div", { class: "sync-rows" }, box.captures.map((c) => el("div", { class: "sync-row council-msg" },
        el("div", {}, el("p", { class: "council-text" }, c.title), el("p", {}, c.words || "(nothing heard)")),
        el("div", { class: "row-buttons" },
          btn("Keep It", "btn-amber", () => MIAShell.act({ kind: "capture.keep", params: { capture_id: c.id } }, { quick: true })),
          btn("Leave It Out", "btn-ghost", () => MIAShell.act({ kind: "capture.discard", params: { capture_id: c.id } }, { quick: true }))))))
        : el("p", { class: "dim" }, "Voice notes from MIA Lite show up here to keep or leave out."),
      el("div", { class: "row-buttons" }, btn("Check for new", "btn-ghost", check)));
  }

  function list() {
    const shown = page.entries.filter(matches);
    $("journal-list").replaceChildren(shown.length ? el("div", { class: "journal-grid" }, shown.map(card))
      : el("p", { class: "empty" }, page.entries.length ? "Nothing matches." : "No entries yet. Write your first one."));
  }

  MIAShell.start(async () => {
    page = await MIA.journal();
    if (!page.available) {
      $("panel").replaceChildren(el("p", { class: "empty" }, "The journal isn't set up on this MIA."));
      return;
    }
    draw();
  });
})();
