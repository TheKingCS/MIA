/*
 * inbox.js — the Inbox screen (claude, 2026-10-16; Zac: "build the inbox
 * for sending stuff to MIA"). Send To MIA: a photo, a file or a note (and
 * from any app, the phone's Share menu). Waiting: what MIA read in each
 * one and where she proposes it goes; File It opens the proposal to
 * check (what it's for, the amount, which maintenance steps, which
 * details), Dismiss sets it aside. Renders MIA.inbox() (core/web_inbox.py);
 * changes are inbox.* actions. Formatting only.
 */
(function () {
  "use strict";
  const { el, act, form, say } = MIAShell;
  const $ = (id) => document.getElementById(id);
  let page = null, showDone = false;
  const ICON = { receipt: "🧾", invoice: "📑", manual: "📘", warranty: "🛡", other: "📄" };

  const btn = (label, cls, onclick) => el("button", { type: "button", class: "btn " + cls, onclick }, label);
  const buttons = (...list) => el("div", { class: "row-buttons" }, list.filter(Boolean));
  const section = (title, actions, ...body) =>
    el("section", { class: "glass money-section" }, el("div", { class: "sect" }, el("h2", {}, title), actions), ...body);
  const day = (iso) => iso ? new Date(iso.slice(0, 10) + "T00:00:00").toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" }) : "";

  // ------------------------------------------------------------ send
  function pick(accept, capture) {
    const input = el("input", { type: "file", multiple: true, hidden: true, accept: accept || null, capture: capture || null });
    input.addEventListener("change", async () => {
      for (const file of input.files) {
        if (file.size > page.max_mb * 1024 * 1024) { say(file.name + " is over " + page.max_mb + " MB."); continue; }
        try {
          say((await MIA.upload("/api/inbox/upload", file)).message);
        } catch (e) {
          say("Couldn't send " + file.name + ": " + e.message);
        }
      }
      input.remove();
      page = await MIA.inbox();
      draw();
    });
    document.body.append(input);
    input.click();
  }
  async function note() {
    const v = await form("Write A Note To MIA", [
      { name: "title", label: "Title", type: "text", required: false, options: [], default: null },
      { name: "text", label: "What to send (a link, a reminder, anything to keep)", type: "textarea", required: true, options: [], default: null },
    ], {});
    if (v) act({ kind: "inbox.note", params: v });
  }

  // ------------------------------------------------------------ open a file
  async function view(item, f) {
    let blob;
    try {
      blob = await MIA.download("/api/inbox/item/" + encodeURIComponent(item.id) + "/file?name=" + encodeURIComponent(f.name));
    } catch (e) {
      say("Couldn't open " + f.name + ".");
      return;
    }
    const url = URL.createObjectURL(blob);
    const dialog = el("dialog", { class: "confirm form-dialog file-view", "aria-label": f.name });
    const close = () => { dialog.close(); dialog.remove(); URL.revokeObjectURL(url); };
    let body;
    if (f.kind === "image") body = el("img", { src: url, alt: f.name });
    else if (f.kind === "pdf") body = el("iframe", { src: url, title: f.name });
    else if (f.kind === "text") { body = el("pre", { class: "file-text" }); body.textContent = (await blob.text()).slice(0, 200000); }
    else body = el("p", { class: "dim" }, item.excerpt || "Download it to open it.");
    dialog.append(el("h3", {}, f.name), body, el("div", { class: "confirm-actions" },
      el("a", { class: "btn btn-ghost", href: url, download: f.name }, "Download"), btn("Close", "btn-ghost", close)));
    dialog.oncancel = (ev) => { ev.preventDefault(); close(); };
    document.body.append(dialog);
    dialog.showModal();
  }

  // ------------------------------------------------------------ file it
  function fileIt(item) {
    const dialog = el("dialog", { class: "confirm form-dialog", "aria-label": "File " + item.label });
    const close = () => { dialog.close(); dialog.remove(); };
    const select = (id, list, value, blank) => el("select", { id },
      blank ? el("option", { value: "" }, blank) : null,
      list.map((o) => el("option", { value: o.id || o, selected: (o.id || o) === value ? true : null }, o.name || o)));
    const row = (label, input) => el("label", { class: "form-row" }, el("span", {}, label), input);
    const money = item.type === "receipt" || item.type === "invoice";
    const asset = select("f-asset", page.picks.assets, item.asset ? item.asset.id : "", "Nothing in particular");
    const amount = el("input", { id: "f-amount", type: "number", step: "any", min: "0", inputmode: "decimal" });
    amount.value = item.amount_value != null ? item.amount_value : "";
    const category = select("f-category", page.picks.categories, item.category || "", "MIA's choice");
    const project = page.picks.projects.length ? select("f-project", page.picks.projects, item.project ? item.project.id : "", "No build") : null;
    const ticks = (list, key, checked) => list.map((x) => {
      const box = el("input", { type: "checkbox", value: String(x[key]) });
      box.checked = checked(x);
      return el("label", { class: "tick-row" }, box, el("span", {}, x.text));
    });
    const steps = ticks(item.schedule, "index", () => true);
    const details = ticks(item.details, "field", (d) => d.on);
    dialog.append(el("form", { method: "dialog", onsubmit: (ev) => {
      ev.preventDefault();
      const params = { item_id: item.id, asset_id: asset.value };
      if (project) params.project_id = project.value;
      if (money) { params.amount = amount.value; if (category.value) params.category = category.value; }
      params.schedule = steps.map((l) => l.querySelector("input")).filter((b) => b.checked).map((b) => Number(b.value));
      if (details.length) params.details = details.map((l) => l.querySelector("input")).filter((b) => b.checked).map((b) => b.value);
      close();
      act({ kind: "inbox.file", params });
    } },
      el("h3", {}, "File " + item.label),
      row("What it's for", asset),
      project ? row("Build", project) : null,
      money ? row("Total", amount) : null,
      money ? row("Category", category) : null,
      steps.length ? el("h4", {}, "Maintenance steps to add") : null, ...steps,
      details.length ? el("h4", {}, "Fill in on its page") : null, ...details,
      el("div", { class: "confirm-actions" }, el("button", { type: "submit", class: "btn btn-green" }, "File It"), btn("Cancel", "btn-ghost", close))));
    dialog.oncancel = (ev) => { ev.preventDefault(); close(); };
    document.body.append(dialog);
    dialog.showModal();
  }

  // ------------------------------------------------------------ cards
  function card(item) {
    const facts = [
      item.vendor ? ["From", item.vendor] : null,
      item.amount ? ["Total", item.amount] : null,
      item.date ? ["Date", day(item.date)] : null,
      item.asset ? ["For", item.asset.name] : null,
      item.project ? ["Build", item.project.name] : null,
      item.subject && item.subject !== item.vendor ? ["Subject", item.subject] : null,
    ].filter(Boolean);
    return el("article", { class: "glass inbox-card" + (item.reading ? " reading" : "") },
      el("div", { class: "inbox-head" },
        el("span", { class: "inbox-ico", "aria-hidden": "true" }, ICON[item.type] || ICON.other),
        el("div", {}, el("h3", {}, item.label), el("p", { class: "dim" }, item.source + " · " + day(item.received))),
        el("span", { class: "chip" }, item.type_label)),
      item.reading ? el("p", { class: "dim" }, "MIA is still reading this photo or scan…") : null,
      item.note ? el("p", { class: "dim" }, item.note) : null,
      facts.length ? el("dl", { class: "inbox-facts" }, facts.map(([k, v]) => [el("dt", {}, k), el("dd", {}, v)]).flat()) : null,
      item.schedule.length ? el("p", { class: "dim" }, "Maintenance in it: " + item.schedule.map((s) => s.text).join("; ")) : null,
      item.details.length ? el("p", { class: "dim" }, "Details for its page: " + item.details.map((d) => d.text).join("; ")) : null,
      !facts.length && item.excerpt ? el("p", { class: "inbox-excerpt" }, item.excerpt) : null,
      el("div", { class: "chip-row" }, item.files.map((f) => el("button", { type: "button", class: "chip chip-button", onclick: () => view(item, f) }, "📎 " + f.name))),
      buttons(btn("File It", "btn-green", () => fileIt(item)),
        btn("Dismiss", "btn-ghost", () => act({ kind: "inbox.dismiss", params: { item_id: item.id } }))));
  }

  function draw() {
    const c = page.counts;
    $("strip").replaceChildren(
      el("div", { class: "cell " + (c.waiting ? "soon" : "ok") }, el("span", { class: "n" }, c.waiting), el("span", { class: "t" }, "Waiting")),
      el("div", { class: "cell ok" }, el("span", { class: "n" }, c.reading), el("span", { class: "t" }, "Being Read")),
      el("div", { class: "cell ok" }, el("span", { class: "n" }, c.filed), el("span", { class: "t" }, "Filed")));
    $("panel").replaceChildren(...[
      section("Send To MIA", null,
        el("div", { class: "inbox-send" },
          btn("📷 Take A Photo", "btn-amber", () => pick("image/*", "environment")),
          btn("📎 Upload A File", "btn-ghost", () => pick()),
          btn("✏ Write A Note", "btn-ghost", note)),
        el("p", { class: "dim" }, "Receipts, manuals, warranties, invoices, anything. From any app on your phone, tap Share and pick MIA. MIA reads it and suggests where it goes; nothing is filed until you say so.")),
      section("Waiting", null, page.pending.length ? el("div", { class: "inbox-list" }, page.pending.map(card))
        : el("p", { class: "empty" }, "Nothing waiting. Send MIA a receipt or a manual.")),
      page.done.length ? section("Filed And Dismissed", btn(showDone ? "Hide" : "Show", "btn-ghost btn-small", () => { showDone = !showDone; draw(); }),
        showDone ? el("div", { class: "rows" }, page.done.map((d) => el("div", { class: "row money-row" },
          el("div", {}, el("div", { class: "row-title" }, d.label), el("div", { class: "row-sub" }, (d.filed_note || d.status) + " · " + day(d.received))))))
          : null) : null,
    ].filter(Boolean));
  }

  MIAShell.start(async () => {
    page = await MIA.inbox();
    if (!page.available) {
      $("panel").replaceChildren(el("p", { class: "empty" }, "The inbox isn't set up on this MIA."));
      return;
    }
    draw();
    // A photo or scan is read in the background: look again until it's done.
    if (page.counts.reading) setTimeout(async () => { page = await MIA.inbox(); draw(); }, 8000);
  });
})();
