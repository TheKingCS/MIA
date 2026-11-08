/*
 * signins.js — Sign-ins and Security (claude, 2026-11-08). Renders MIA.securityLog() (core/security_log.py): this
 * account's events newest first (what happened, from which device, when; a new device and wrong passwords marked),
 * how many other devices are signed in, Sign Out Everywhere (MIA.signOutEverywhere: every other session ends,
 * this one stays), and two-step sign-in turned on (password, then the key for the authenticator app and a code from
 * it) or off (password and a code; core/two_step.py). Formatting only.
 */
(function () {
  "use strict";
  const { el, say } = MIAShell;
  const $ = (id) => document.getElementById(id);

  const when = (iso) => new Date(iso).toLocaleString(undefined, { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" });
  const WARN = new Set(["sign_in_failed", "waiting", "password_changed", "phone_linked", "two_step_off"]);

  async function everywhere() {
    if (!(await MIAShell.confirm("Sign out every other device? This one stays signed in. Linked phones are unlinked in Settings."))) return;
    try { const done = await MIA.signOutEverywhere(); say(done.ended ? "Signed out " + done.ended + " other device" + (done.ended === 1 ? "" : "s") + "." : "No other devices were signed in."); }
    catch (e) { say(e.message); }
    draw(await MIA.securityLog());
  }

  // Two-step sign-in (core/two_step.py): on only once a code from the app is entered, so a mistyped key locks no one out.
  function twoStep(page) {
    const box = el("section", { class: "glass money-section", "aria-label": "Two-step sign-in" });
    const turnOn = async () => {
      const v = await MIAShell.form("Turn On Two-Step Sign-In", [{ name: "password", label: "Your password", type: "password", required: true, options: [], default: null }], {});
      if (!v) return;
      let setup;
      try { setup = await MIA.twoStepStart(v.password); } catch (e) { say(e.message); return; }
      const code = el("input", { type: "text", inputmode: "numeric", autocomplete: "one-time-code", maxlength: "6", "aria-label": "Code from the app" });
      box.replaceChildren(el("h2", {}, "Two-Step Sign-In"),
        el("p", {}, "1. In your authenticator app (Google Authenticator, Microsoft Authenticator, Authy...), add an account with this key:"),
        el("p", { class: "ts-key" }, setup.key),
        el("p", { class: "dim" }, "On this phone? ", el("a", { href: setup.link }, "Open it in the app"), " instead of typing the key."),
        el("p", {}, "2. Enter the 6-digit code it shows:"), code,
        el("div", { class: "acct-actions" }, el("button", { type: "button", class: "btn btn-green", onclick: async () => {
          try { await MIA.twoStepConfirm(code.value.trim()); say("Two-step sign-in is on."); draw(await MIA.securityLog()); }
          catch (e) { say(e.message); }
        } }, "Turn On")));
      code.focus();
    };
    const turnOff = async () => {
      const v = await MIAShell.form("Turn Off Two-Step Sign-In", [
        { name: "password", label: "Your password", type: "password", required: true, options: [], default: null },
        { name: "code", label: "Code from your authenticator app", type: "text", required: true, options: [], default: null }], {});
      if (!v) return;
      try { await MIA.twoStepOff(v.password, v.code); say("Two-step sign-in is off."); draw(await MIA.securityLog()); }
      catch (e) { say(e.message); }
    };
    box.replaceChildren(el("h2", {}, "Two-Step Sign-In"),
      el("p", {}, page.two_step ? "On. Signing in from another device asks for the code from your authenticator app."
        : "Off. Turn it on and signing in from another device also asks for a code from an app on your phone, so a password alone isn't enough."),
      el("p", { class: "dim" }, "Lost the phone with the app? Your recovery code still gets you in (and turns this off)."),
      el("div", { class: "acct-actions" }, page.two_step
        ? el("button", { type: "button", class: "btn btn-ghost", onclick: turnOff }, "Turn Off")
        : el("button", { type: "button", class: "btn btn-green", onclick: turnOn }, "Turn On")));
    return box;
  }

  function draw(page) {
    if (!page.available) { $("panel").replaceChildren(el("p", { class: "empty" }, "The security log isn't on this MIA.")); return; }
    $("panel").replaceChildren(
      el("section", { class: "glass money-section" },
        el("p", {}, page.other_sessions ? page.other_sessions + " other device" + (page.other_sessions === 1 ? " is" : "s are") + " signed in to your account."
          : "No other devices are signed in to your account."),
        el("p", { class: "dim" }, "If you see a sign-in you don't recognize, change your password: that signs every other device out too."),
        el("button", { type: "button", class: "btn btn-ghost", onclick: everywhere }, "Sign Out Everywhere")),
      twoStep(page),
      el("section", { class: "glass money-section", "aria-label": "Your security log" },
        el("h2", {}, "Your Security Log"),
        page.events.length ? el("div", { class: "rows" }, page.events.map((e) => el("div", { class: "row" + (WARN.has(e.kind) ? " si-warn" : "") },
          el("div", {}, el("div", { class: "row-title" }, e.what + (e.detail ? " · " + e.detail : "")),
            el("div", { class: "row-sub" }, (e.device || "This computer") + " · " + when(e.at))))))
          : el("p", { class: "empty" }, "Nothing yet. Sign-ins from your phone and other devices show here.")));
  }

  MIAShell.start(async () => draw(await MIA.securityLog()));
})();
