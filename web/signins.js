/*
 * signins.js — Sign-ins and Security (claude, 2026-11-08). Renders MIA.securityLog() (core/security_log.py): this
 * account's events newest first (what happened, from which device, when; a new device and wrong passwords marked),
 * how many other devices are signed in, Sign Out Everywhere (MIA.signOutEverywhere: every other session ends,
 * this one stays, and every linked phone is unlinked), the phones linked to MIA on this computer with Unlink for each
 * (MIA.unlinkDevice, core/linked_devices.py), and two-step sign-in turned on (password, then the key for the authenticator app and a code from
 * it) or off (password and a code; core/two_step.py), and whether MIA's most private files are sealed on disk with
 * the recovery key shown behind the password, on the PC only (core/at_rest.py, DEC-0126). Formatting only.
 */
(function () {
  "use strict";
  const { el, say } = MIAShell;
  const $ = (id) => document.getElementById(id);

  const when = (iso) => new Date(iso).toLocaleString(undefined, { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" });
  const WARN = new Set(["sign_in_failed", "waiting", "password_changed", "phone_linked", "phone_unlinked", "two_step_off"]);
  const day = (iso) => new Date(iso.length === 10 ? iso + "T12:00:00" : iso).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });

  async function everywhere() {
    if (!(await MIAShell.confirm("Sign out every other device? This one stays signed in. Linked phones are unlinked too, and link again with your password."))) return;
    try {
      const done = await MIA.signOutEverywhere();
      const n = (done.ended || 0) + (done.unlinked || 0);
      say(n ? "Signed out " + n + " other device" + (n === 1 ? "" : "s") + "." : "No other devices were signed in.");
    }
    catch (e) { say(e.message); }
    draw(await MIA.securityLog());
  }

  // Linked phones (core/linked_devices.py): each with when it linked and last reached this computer, and Unlink.
  function phones(page) {
    const list = page.linked_devices || [];
    const unlink = async (d) => {
      if (!(await MIAShell.confirm("Unlink this phone? It stops reaching MIA on this computer until it links again with your password."))) return;
      try { await MIA.unlinkDevice(d.id); say("Unlinked."); } catch (e) { say(e.message); }
      draw(await MIA.securityLog());
    };
    return el("section", { class: "glass money-section", "aria-label": "Linked phones" },
      el("h2", {}, "Linked Phones"),
      list.length ? el("div", { class: "rows" }, list.map((d) => el("div", { class: "row" },
        el("div", {}, el("div", { class: "row-title" }, "Phone linked " + day(d.linked)),
          el("div", { class: "row-sub" }, d.last_seen ? "Last reached this computer " + day(d.last_seen) : "Not seen since it linked")),
        el("button", { type: "button", class: "btn btn-ghost", onclick: () => unlink(d) }, "Unlink"))))
        : el("p", { class: "empty" }, "No phones are linked to MIA on this computer."));
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

  // Sealed files (core/at_rest.py): the key opens only for this Windows account; the recovery key opens them anywhere.
  function sealed(page) {
    const s = page.at_rest || {};
    const box = el("section", { class: "glass money-section", "aria-label": "Your files on this computer" });
    const show = async () => {
      const v = await MIAShell.form("Show the Recovery Key", [{ name: "password", label: "Your password", type: "password", required: true, options: [], default: null }], {});
      if (!v) return;
      let got;
      try { got = await MIA.recoveryKey(v.password); } catch (e) { say(e.message); return; }
      box.replaceChildren(el("h2", {}, "Your Recovery Key"),
        el("p", { class: "ts-key" }, got.key),
        el("p", {}, "Put this in your password manager now, not in a file on this computer. With it, your files open on a new computer or after Windows is reinstalled; without it, they can't."),
        el("div", { class: "acct-actions" }, el("button", { type: "button", class: "btn btn-ghost", onclick: async () => draw(await MIA.securityLog()) }, "Done")));
    };
    box.append(el("h2", {}, "Your Files on This Computer"),
      el("p", {}, s.sealing ? "Encrypted. Your conversations, memories, notes, people, finances and other private records are sealed on disk; only your Windows account on this computer opens them."
        : "Not encrypted" + (s.why_not ? ": " + s.why_not : "") + "."),
      page.on_this_pc && s.sealing
        ? el("div", { class: "acct-actions" }, el("button", { type: "button", class: "btn btn-ghost", onclick: show }, "Show the Recovery Key"))
        : el("p", { class: "dim" }, s.sealing ? "The recovery key is shown on the computer itself." : ""));
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
      phones(page),
      twoStep(page),
      sealed(page),
      el("section", { class: "glass money-section", "aria-label": "Your security log" },
        el("h2", {}, "Your Security Log"),
        page.events.length ? el("div", { class: "rows" }, page.events.map((e) => el("div", { class: "row" + (WARN.has(e.kind) ? " si-warn" : "") },
          el("div", {}, el("div", { class: "row-title" }, e.what + (e.detail ? " · " + e.detail : "")),
            el("div", { class: "row-sub" }, (e.device || "This computer") + " · " + when(e.at))))))
          : el("p", { class: "empty" }, "Nothing yet. Sign-ins from your phone and other devices show here.")));
  }

  MIAShell.start(async () => draw(await MIA.securityLog()));
})();
