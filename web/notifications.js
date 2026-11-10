/*
 * notifications.js — Notifications (claude, 2026-11-07, DEC-0125). Renders
 * MIA.notifications() (core/web_notifications.py): each notification newest
 * first, unread ones lit, amber for a warning and red only for a real error;
 * "Why?" opens why MIA sent one she sent on her own. Mark All Read and
 * Dismiss are actions (notification.read_all, notification.dismiss); a
 * dismissal teaches MIA what you'd rather not hear. Then Waiting for the
 * Internet: what you asked to hear once MIA is back online (online.remind,
 * online.forget). Formatting only.
 */
(function () {
  "use strict";
  const { el, act } = MIAShell;
  const $ = (id) => document.getElementById(id);

  function card(n) {
    return el("article", { class: "glass nt-card" + (n.read ? "" : " unread") + (n.tone ? " " + n.tone : "") },
      el("div", { class: "nt-top" }, el("span", { class: "nt-title" }, n.title), el("span", { class: "dim nt-when" }, n.when)),
      n.message ? el("p", { class: "nt-msg" }, n.message) : null,
      el("div", { class: "nt-foot" }, el("span", { class: "pw-label" }, n.source),
        el("div", { class: "row-buttons" },
          n.why ? el("details", { class: "nt-why" }, el("summary", {}, "Why?"), el("p", {}, n.why)) : null,
          el("button", { type: "button", class: "btn btn-quiet btn-small", onclick: () => act({ kind: "notification.dismiss", params: { notification_id: n.id } }, { quick: true }) }, "Dismiss"))));
  }

  // Waiting for the Internet (core/online_watch.OnlineReminders): delivered all at once when the connection's back.
  async function addOnline() {
    const v = await MIAShell.form("Remind Me Once We're Online", [
      { name: "what", label: "What to remind you about", type: "text", required: true }]);
    if (v) act({ kind: "online.remind", params: { what: v.what } }, { quick: true });
  }
  function onlineCard(o) {
    if (!o || !o.available) return null;
    const state = { online: "MIA's online now.", offline: "MIA's offline: these come the moment the connection's back.",
      unknown: "These come the moment MIA's back online." }[o.state] || "";
    return el("section", { class: "glass nt-online", "aria-label": "Waiting for the internet" },
      el("h2", { class: "pw-label" }, "Waiting for the Internet"),
      el("p", { class: "dim" }, state),
      o.items.length ? el("ul", { class: "nt-online-list" }, ...o.items.map((r) => el("li", {},
        el("span", {}, r.what), el("span", { class: "dim nt-when" }, r.when),
        el("button", { type: "button", class: "btn btn-quiet btn-small", "aria-label": "Don't remind me: " + r.what,
          onclick: () => act({ kind: "online.forget", params: { index: r.index } }, { quick: true }) }, "Remove"))))
        : el("p", { class: "dim" }, "Nothing waiting."),
      el("div", { class: "row-buttons" }, el("button", { type: "button", class: "btn btn-ghost btn-small", onclick: addOnline }, "Add a Reminder")));
  }

  function draw(page) {
    if (window.MIAIcons) MIAIcons.badge($("hero-icon"), "inbox");
    $("nt-sub").textContent = page.unread ? page.unread + " new" : "All caught up.";
    $("panel").replaceChildren(...[
      page.unread ? el("div", { class: "row-buttons" }, el("button", { type: "button", class: "btn btn-ghost",
        onclick: () => act({ kind: "notification.read_all", params: {} }, { quick: true }) }, "Mark All Read")) : null,
      ...(page.items.length ? page.items.map(card) : [el("p", { class: "empty" }, "No notifications.")]),
      onlineCard(page.online),
      el("p", { class: "dim nt-say" }, "Or say “what are my notifications?”, “why did you tell me that?”, “stop telling me about budgets”, “remind me when we're back online to sync the bank”."),
    ].filter(Boolean));
  }

  MIAShell.start(async () => draw(await MIA.notifications()));
})();
