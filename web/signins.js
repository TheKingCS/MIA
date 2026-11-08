/*
 * signins.js — Sign-ins and Security (claude, 2026-11-08). Renders MIA.securityLog() (core/security_log.py): this
 * account's events newest first (what happened, from which device, when; a new device and wrong passwords marked),
 * how many other devices are signed in, and Sign Out Everywhere (MIA.signOutEverywhere: every other session ends,
 * this one stays). Formatting only.
 */
(function () {
  "use strict";
  const { el, say } = MIAShell;
  const $ = (id) => document.getElementById(id);

  const when = (iso) => new Date(iso).toLocaleString(undefined, { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" });
  const WARN = new Set(["sign_in_failed", "waiting", "password_changed", "phone_linked"]);

  async function everywhere() {
    if (!(await MIAShell.confirm("Sign out every other device? This one stays signed in. Linked phones are unlinked in Settings."))) return;
    try { const done = await MIA.signOutEverywhere(); say(done.ended ? "Signed out " + done.ended + " other device" + (done.ended === 1 ? "" : "s") + "." : "No other devices were signed in."); }
    catch (e) { say(e.message); }
    draw(await MIA.securityLog());
  }

  function draw(page) {
    if (!page.available) { $("panel").replaceChildren(el("p", { class: "empty" }, "The security log isn't on this MIA.")); return; }
    $("panel").replaceChildren(
      el("section", { class: "glass money-section" },
        el("p", {}, page.other_sessions ? page.other_sessions + " other device" + (page.other_sessions === 1 ? " is" : "s are") + " signed in to your account."
          : "No other devices are signed in to your account."),
        el("p", { class: "dim" }, "If you see a sign-in you don't recognize, change your password: that signs every other device out too."),
        el("button", { type: "button", class: "btn btn-ghost", onclick: everywhere }, "Sign Out Everywhere")),
      el("section", { class: "glass money-section", "aria-label": "Your security log" },
        el("h2", {}, "Your Security Log"),
        page.events.length ? el("div", { class: "rows" }, page.events.map((e) => el("div", { class: "row" + (WARN.has(e.kind) ? " si-warn" : "") },
          el("div", {}, el("div", { class: "row-title" }, e.what + (e.detail ? " · " + e.detail : "")),
            el("div", { class: "row-sub" }, (e.device || "This computer") + " · " + when(e.at))))))
          : el("p", { class: "empty" }, "Nothing yet. Sign-ins from your phone and other devices show here.")));
  }

  MIAShell.start(async () => draw(await MIA.securityLog()));
})();
