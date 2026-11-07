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
    const effects = ticks(item.effects || [], "index", (e) => e.on);
    dialog.append(el("form", { method: "dialog", onsubmit: (ev) => {
      ev.preventDefault();
      const params = { item_id: item.id, asset_id: asset.value };
      if (project) params.project_id = project.value;
      if (money) { params.amount = amount.value; if (category.value) params.category = category.value; }
      params.schedule = steps.map((l) => l.querySelector("input")).filter((b) => b.checked).map((b) => Number(b.value));
      if (details.length) params.details = details.map((l) => l.querySelector("input")).filter((b) => b.checked).map((b) => b.value);
      if (effects.length) params.effects = effects.map((l) => l.querySelector("input")).filter((b) => b.checked).map((b) => Number(b.value));
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
      effects.length ? el("h4", {}, "What this receipt means (" + item.receipt_kind + ")") : null, ...effects,
      ...(item.effect_notes || []).map((n) => el("p", { class: "dim" }, n)),
      el("div", { class: "confirm-actions" }, el("button", { type: "submit", class: "btn btn-green" }, "File It"), btn("Cancel", "btn-ghost", close))));
    dialog.oncancel = (ev) => { ev.preventDefault(); close(); };
    document.body.append(dialog);
    dialog.showModal();
  }

  // ------------------------------------------------------------ email (core/inbox_mail.py, 2026-11-07)
  let changingEmail = false;
  async function emailDo(call, done) {
    try { await call(); say(done); } catch (e) { say(e.message); return; }
    changingEmail = false;
    page = await MIA.inbox();
    draw();
  }

  function emailSection(mail) {
    if (!mail || !mail.available) return null;
    if (!mail.configured || changingEmail) {
      const field = (label, attrs) => el("label", { class: "form-row" }, el("span", {}, label), el("input", Object.assign({ class: "input" }, attrs)));
      const host = field("Mail server", { value: mail.host || "imap.gmail.com", autocomplete: "off" });
      const address = field("Email address", { type: "email", value: mail.address || "", autocomplete: "username" });
      const password = field("App password", { type: "password", autocomplete: "off" });
      const passphrase = field("Passphrase (8+ characters; your journal one unlocks both)", { type: "password", autocomplete: "off" });
      const everyday = el("input", { type: "checkbox" });
      everyday.checked = mail.configured ? mail.everyday : true;
      const value = (row) => row.querySelector("input").value;
      return section("Email", null,
        el("p", { class: "dim" }, "Your everyday mailbox: MIA reads only receipts, orders and service confirmations, "
          + "and leaves your mail as it is (nothing marked read). For Gmail, make an app password first: Google Account, "
          + "Security, 2-Step Verification, App passwords."),
        el("form", { class: "stack-form", onsubmit: (e) => {
          e.preventDefault();
          emailDo(() => MIA.inboxEmailSetup({ host: value(host), address: value(address), password: value(password),
            passphrase: value(passphrase), everyday: everyday.checked }), "Email is set up. Checking it now.");
        } }, host, address, password, passphrase,
          el("label", { class: "tick-row" }, everyday, el("span", {}, "This is my everyday mailbox (receipts and orders only)")),
          buttons(el("button", { type: "submit", class: "btn btn-green" }, "Save"),
            mail.configured ? btn("Cancel", "btn-ghost", () => { changingEmail = false; draw(); }) : null)));
    }
    if (!mail.unlocked) {
      const passphrase = el("input", { type: "password", class: "input", placeholder: "Passphrase", autocomplete: "off" });
      return section("Email", null,
        el("p", {}, "Set up for " + mail.address + ", but locked since MIA started. Unlock it to check for receipts."),
        el("form", { class: "form-row", onsubmit: (e) => { e.preventDefault(); emailDo(() => MIA.inboxEmailUnlock(passphrase.value), "Unlocked. Checking now."); } },
          passphrase, el("button", { type: "submit", class: "btn btn-green" }, "Unlock")),
        buttons(btn("Change settings", "btn-ghost btn-small", () => { changingEmail = true; draw(); })));
    }
    return section("Email", null,
      el("p", {}, "Checking " + mail.address + " every 10 minutes" + (mail.everyday ? " for receipts and orders (nothing marked read)." : ".")),
      mail.last ? el("p", { class: "dim" }, mail.last) : null,
      buttons(btn("Check now", "btn-ghost btn-small", () => emailDo(() => MIA.inboxEmailCheck(), "Checking.")),
        btn("Change settings", "btn-ghost btn-small", () => { changingEmail = true; draw(); })));
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
      (item.effects || []).length ? el("p", { class: "dim" }, item.receipt_kind[0].toUpperCase() + item.receipt_kind.slice(1) + ": "
        + item.effects.slice(0, 4).map((e) => e.text).join("; ") + (item.effects.length > 4 ? "; and " + (item.effects.length - 4) + " more" : "")) : null,
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
      (page.auto || []).length ? section("Filed By MIA From Your Email", null,
        el("p", { class: "dim" }, "She files emailed receipts on her own. If one is wrong, Undo takes back exactly what it did and puts it in Waiting."),
        el("div", { class: "rows" }, page.auto.map((a) => el("div", { class: "row money-row" },
          el("div", {}, el("div", { class: "row-title" }, a.label), el("div", { class: "row-sub" }, a.did + " · " + day(a.received))),
          btn("Undo", "btn-ghost btn-small", () => act({ kind: "inbox.unfile", params: { item_id: a.id } })))))) : null,
      emailSection(page.email),
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
