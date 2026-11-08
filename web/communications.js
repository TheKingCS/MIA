/*
 * communications.js — Communications (DEC-0129, claude, 2026-11-08).
 * Renders MIA.communications() (core/web_comms.comms_page): email drafts (opened in the frame's draft view: Send only
 * when you press it), the mailbox, what MIA said on her own today and held back, her daily limit (comms.limit), the
 * kinds of message on a break (comms.resume), the latest notifications, and people to write to (Talk drafts it).
 * By voice: "draft an email to…", "did you hold anything back?", "only tell me things three times a day".
 */
(function () {
  "use strict";
  const { el } = MIAShell;
  const $ = (id) => document.getElementById(id);
  const btn = (label, cls, onclick) => el("button", { type: "button", class: "btn " + cls + " btn-small", onclick }, label);
  const card = (title, ...kids) => el("section", { class: "glass money-section" }, el("h2", { class: "pw-label" }, title), ...kids);

  let canSend = false;

  function drafts(d) {
    if (!d.available) return null;
    return card("Email Drafts" + (d.items.length ? " · " + d.items.length : ""),
      d.items.length ? el("div", { class: "rows" }, d.items.map((x) => el("a", { href: "#", class: "row money-row comms-row",
        onclick: (ev) => { ev.preventDefault(); MIAShell.showDraft(x, canSend); } },
        el("div", {}, el("div", { class: "row-title" }, x.subject || "(no subject)"),
          el("div", { class: "row-sub" }, (x.to && x.to.length ? "To " + x.to.join(", ") : "No address yet") + " · " + (x.body || "").slice(0, 80))),
        el("span", { class: "row-meta" }, "Open ›"))))
        : el("p", { class: "dim" }, "No drafts. Ask MIA to write one: “draft an email to the plumber about Tuesday.” MIA only drafts; it goes when you press Send."),
      el("div", { class: "row-buttons" }, btn("Ask MIA for a draft", "btn-amber", () => MIAShell.talk(true, "Draft an email to "))));
  }

  function mailbox(m) {
    if (!m || m.available === false) return null;
    const state = !m.configured ? "Not set up. MIA can read it for receipts and bills."
      : m.unlocked ? "Connected" + (m.address ? " · " + m.address : "") : "Locked until you unlock it this session.";
    return card("Your Mailbox", el("p", {}, state), el("div", { class: "row-buttons" }, el("a", { class: "btn btn-ghost btn-small", href: "inbox.html" }, m.configured ? "Inbox ›" : "Set Up in Inbox ›")));
  }

  function messages(m) {
    if (!m.available) return null;
    const limit = async () => {
      const v = await MIAShell.form("How often MIA speaks up", [{ name: "count", label: "At most this many times a day (urgent things and answers don't count)", type: "int", required: true }], { count: m.limit });
      if (v) MIAShell.act({ kind: "comms.limit", params: { count: v.count } });
    };
    return card("MIA's Messages Today",
      el("p", {}, "She spoke up " + m.said_today + " of " + m.limit + " time" + (m.limit === 1 ? "" : "s") + " allowed today."),
      m.held.length ? el("div", { class: "rows" }, m.held.map((h) => el("div", { class: "row money-row" },
        el("div", {}, el("div", { class: "row-title" }, h.title), el("div", { class: "row-sub" }, h.message)),
        el("span", { class: "row-meta comms-note" }, h.waiting ? "Waiting" : "Let go: " + h.reason)))) : el("p", { class: "dim" }, "Nothing held back today."),
      m.paused.length ? el("div", { class: "rows" }, el("p", { class: "pw-label" }, "On a Break"), m.paused.map((p) => el("div", { class: "row money-row" },
        el("div", {}, el("div", { class: "row-title" }, p.label), el("div", { class: "row-sub" }, "Until " + p.until + " (you dismissed it a few times)")),
        btn("Bring Back", "btn-ghost", () => MIAShell.act({ kind: "comms.resume", params: { topic: p.topic } }))))) : null,
      el("div", { class: "row-buttons" }, btn("Change the limit", "btn-ghost", limit)));
  }

  function notifications(n) {
    if (!n.available) return null;
    return card("Notifications" + (n.unread ? " · " + n.unread + " new" : ""),
      n.items.length ? el("div", { class: "rows" }, n.items.map((x) => el("div", { class: "row money-row" + (x.read ? "" : " unread") },
        el("div", {}, el("div", { class: "row-title" }, x.title), el("div", { class: "row-sub" }, x.message + " · " + x.when))))) : el("p", { class: "dim" }, "Nothing yet."),
      el("div", { class: "row-buttons" }, el("a", { class: "btn btn-ghost btn-small", href: "notifications.html" }, "All notifications ›")));
  }

  function people(list) {
    return card("Catch Up",
      list.length ? el("div", { class: "rows" }, list.map((p) => el("div", { class: "row money-row" },
        el("div", {}, el("div", { class: "row-title" }, p.name),
          el("div", { class: "row-sub" }, p.since == null ? "No catch-up logged yet" : p.since === 0 ? "Caught up today" : "Last caught up " + p.since + " day" + (p.since === 1 ? "" : "s") + " ago")),
        btn("Write", "btn-ghost", () => MIAShell.talk(true, "Draft an email to " + p.name + " ")))))
        : el("p", { class: "dim" }, "Add an email to someone in People and they'll show here to write to."),
      el("div", { class: "row-buttons" }, el("a", { class: "btn btn-ghost btn-small", href: "people.html" }, "People ›")));
  }

  async function load() {
    const page = await MIA.communications();
    try { canSend = (await MIA.emailDrafts()).can_send; } catch (e) { canSend = false; }
    $("panel").replaceChildren(...[drafts(page.drafts), messages(page.messages), notifications(page.notifications),
      people(page.people), mailbox(page.mailbox)].filter(Boolean));
  }

  MIAShell.start(load);
})();
