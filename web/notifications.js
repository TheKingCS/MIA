/*
 * notifications.js — Notifications (claude, 2026-11-07, DEC-0125). Renders
 * MIA.notifications() (core/web_notifications.py): each notification newest
 * first, unread ones lit, amber for a warning and red only for a real error;
 * "Why?" opens why MIA sent one she sent on her own. Mark All Read and
 * Dismiss are actions (notification.read_all, notification.dismiss); a
 * dismissal teaches MIA what you'd rather not hear. Formatting only.
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

  function draw(page) {
    if (window.MIAIcons) MIAIcons.badge($("hero-icon"), "inbox");
    $("nt-sub").textContent = page.unread ? page.unread + " new" : "All caught up.";
    $("panel").replaceChildren(...[
      page.unread ? el("div", { class: "row-buttons" }, el("button", { type: "button", class: "btn btn-ghost",
        onclick: () => act({ kind: "notification.read_all", params: {} }, { quick: true }) }, "Mark All Read")) : null,
      ...(page.items.length ? page.items.map(card) : [el("p", { class: "empty" }, "No notifications.")]),
      el("p", { class: "dim nt-say" }, "Or say “what are my notifications?”, “why did you tell me that?”, “stop telling me about budgets”."),
    ].filter(Boolean));
  }

  MIAShell.start(async () => draw(await MIA.notifications()));
})();
