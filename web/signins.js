/*
 * signins.js — Sign-ins and Security (claude, 2026-11-08). Renders MIA.securityLog() (core/security_log.py): this
 * account's events newest first (what happened, from which device, when; a new device and wrong passwords marked),
 * how many other devices are signed in, Sign Out Everywhere (MIA.signOutEverywhere: every other session ends,
 * this one stays, and every linked phone is unlinked), the phones linked to MIA on this computer with Unlink for each
 * (MIA.unlinkDevice, core/linked_devices.py), and two-step sign-in turned on (password, then the key for the authenticator app and a code from
 * it) or off (password and a code; core/two_step.py), and whether MIA's most private files are sealed on disk with
 * the recovery key shown behind the password, on the PC only (core/at_rest.py, DEC-0126), and Lockdown (WP-01,
 * MIA.lockdown, core/lockdown.py), and whether the log is intact (WP-05: its chain, and the newest hash this device
 * kept, checked again next time). Formatting only.
 */
(function () {
  "use strict";
  const { el, say } = MIAShell;
  const $ = (id) => document.getElementById(id);

  const when = (iso) => new Date(iso).toLocaleString(undefined, { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" });
  const WARN = new Set(["sign_in_failed", "waiting", "password_changed", "phone_linked", "phone_unlinked", "two_step_off", "lockdown"]);
  const day = (iso) => new Date(iso.length === 10 ? iso + "T12:00:00" : iso).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });

  // The log's head kept on this device (WP-05, REQ-SEC-034): the newest hash it saw, sent next time so the computer
  // says whether its log still holds it. Kept only while the log checks out, so a rewrite stays shown until he says.
  const HEAD = "mia.securityLogHead";
  const seenHead = () => { try { return localStorage.getItem(HEAD) || ""; } catch (e) { return ""; } };
  const keepHead = (h) => { try { if (h) localStorage.setItem(HEAD, h); } catch (e) { /* private window: not kept */ } };

  async function load() {
    const page = await MIA.securityLog(seenHead());
    const c = page.chain || {};
    if (c.ok && c.seen !== "missing" && c.head) keepHead(c.head.h);
    return page;
  }

  // Whether the log is as written: each entry chained to the one before, and still holding what this device saw.
  function chain(page) {
    const c = page.chain || {};
    const box = el("section", { class: "glass money-section", "aria-label": "Whether your security log is intact" },
      el("h2", {}, "Is the Log Intact?"));
    if (c.seen === "missing") {
      box.append(el("p", { class: "si-warn" }, "Changed. This log no longer holds the newest entry this device saw last time: "
        + "something other than MIA rewrote it or cut it back. Check the sign-ins below, change your password if anything "
        + "looks wrong, and consider Lockdown."),
        el("div", { class: "acct-actions" }, el("button", { type: "button", class: "btn btn-ghost", onclick: async () => {
          keepHead(c.head && c.head.h); say("This device checks from the log as it is now."); draw(await load());
        } }, "Check From Now On")));
    } else if (!c.ok) {
      const b = c.broken || {};
      box.append(el("p", { class: "si-warn" }, "Changed: " + (b.why || "the chain is broken") + (b.at ? " (the entry of " + when(b.at) + ")" : "") + "."));
    } else {
      box.append(el("p", {}, c.chained ? "Intact. Each of its " + c.chained + " entries is linked to the one before, so one changed or removed shows."
        + (c.seen === "held" ? " It still holds what this device saw last time." : "") : "Nothing to check yet."),
        el("p", { class: "dim" }, "This device keeps the newest link and checks it next time, so a log rewritten on the computer shows here."));
    }
    return box;
  }

  async function everywhere() {
    if (!(await MIAShell.confirm("Sign out every other device? This one stays signed in. Linked phones are unlinked too, and link again with your password."))) return;
    try {
      const done = await MIA.signOutEverywhere();
      const n = (done.ended || 0) + (done.unlinked || 0);
      say(n ? "Signed out " + n + " other device" + (n === 1 ? "" : "s") + "." : "No other devices were signed in.");
    }
    catch (e) { say(e.message); }
    draw(await load());
  }

  // Lockdown (WP-01, core/lockdown.py): every sign-in ends, this one too; phones unlinked; vaults locked; all of hers
  // stopped, until he signs in with his password.
  async function lockdown() {
    if (!(await MIAShell.confirm("Lock MIA down? Every device is signed out, this one too, linked phones are unlinked, "
      + "your vaults lock and everything of MIA's own stops. Signing in with your password lifts it."))) return;
    try { await MIA.lockdown(); } catch (e) { /* this session has ended: the sign-in page follows */ }
    location.href = "index.html";
  }

  // Linked devices (core/linked_devices.py, WP-10): each in words (what it is, when it linked, when it last reached
  // this computer, stale after 90 days unseen), with Unlink, and Lost: its key refused at once and the device told to
  // erase MIA's data when it next reaches the computer. Those reported lost stay listed until they've been told.
  function phones(page) {
    const list = (page.linked_devices || []).filter((d) => !d.lost);
    const gone = (page.linked_devices || []).filter((d) => d.lost);
    const unlink = async (d) => {
      if (!(await MIAShell.confirm("Unlink this device? It stops reaching MIA on this computer until it links again with your password."))) return;
      try { await MIA.unlinkDevice(d.id); say("Unlinked."); } catch (e) { say(e.message); }
      draw(await load());
    };
    const lost = async (d) => {
      if (!(await MIAShell.confirm("Report this device lost? Its key stops working now, and the next time it reaches this "
        + "computer it erases MIA's data on it. Your data here is untouched."))) return;
      try { await MIA.lostDevice(d.id); say("Reported lost. It erases MIA's data when it next connects."); } catch (e) { say(e.message); }
      draw(await load());
    };
    const what = (d) => (d.name || (d.kind === "phone" ? "Phone" : d.kind)) + (d.scope === "household" ? " (the household's)" : "");
    return el("section", { class: "glass money-section", "aria-label": "Linked devices" },
      el("h2", {}, "Linked Devices"),
      list.length ? el("div", { class: "rows" }, list.map((d) => el("div", { class: "row" + (d.stale ? " si-warn" : "") },
        el("div", {}, el("div", { class: "row-title" }, what(d) + ", linked " + day(d.linked)),
          el("div", { class: "row-sub" }, (d.last_seen ? "Last reached this computer " + day(d.last_seen) : "Not seen since it linked")
            + (d.stale ? " · not seen for 90 days: unlink it if you don't use it" : ""))),
        el("div", { class: "acct-actions" },
          el("button", { type: "button", class: "btn btn-ghost", onclick: () => unlink(d) }, "Unlink"),
          el("button", { type: "button", class: "btn btn-ghost", onclick: () => lost(d) }, "Lost")))))
        : el("p", { class: "empty" }, "No devices are linked to MIA on this computer."),
      gone.length ? el("div", { class: "rows" }, gone.map((d) => el("div", { class: "row si-warn" },
        el("div", {}, el("div", { class: "row-title" }, what(d) + ", reported lost " + day(d.lost)),
          el("div", { class: "row-sub" }, d.told ? "It reconnected on " + day(d.told) + " and was told to erase MIA's data."
            : "Its key is refused. It erases MIA's data when it next reaches this computer."))))) : null);
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
          try { await MIA.twoStepConfirm(code.value.trim()); say("Two-step sign-in is on."); draw(await load()); }
          catch (e) { say(e.message); }
        } }, "Turn On")));
      code.focus();
    };
    const turnOff = async () => {
      const v = await MIAShell.form("Turn Off Two-Step Sign-In", [
        { name: "password", label: "Your password", type: "password", required: true, options: [], default: null },
        { name: "code", label: "Code from your authenticator app", type: "text", required: true, options: [], default: null }], {});
      if (!v) return;
      try { await MIA.twoStepOff(v.password, v.code); say("Two-step sign-in is off."); draw(await load()); }
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

  // Sealed files (core/at_rest.py): the key opens only for this account on this computer (the Windows sign-in, or
  // on Linux the machine's unlock secret); the recovery key opens them anywhere.
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
        el("p", {}, "Put this in your password manager now, not in a file on this computer. With it, your files open on a new computer or after the system is reinstalled; without it, they can't."),
        el("div", { class: "acct-actions" }, el("button", { type: "button", class: "btn btn-ghost", onclick: async () => draw(await load()) }, "Done")));
    };
    box.append(el("h2", {}, "Your Files on This Computer"),
      el("p", {}, s.sealing ? "Encrypted. Your conversations, memories, notes, people, finances and other private records are sealed on disk; only your " + (s.protection === "dpapi" ? "Windows account" : "account") + " on this computer opens them."
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
        el("button", { type: "button", class: "btn btn-ghost", onclick: everywhere }, "Sign Out Everywhere"),
        el("p", { class: "dim" }, "Lockdown signs out everything, this device too, locks your vaults and stops MIA "
          + "until you sign in with your password. You can also just say \u201clockdown\u201d."),
        el("button", { type: "button", class: "btn btn-ghost", onclick: lockdown }, "Lockdown")),
      phones(page),
      twoStep(page),
      sealed(page),
      chain(page),
      el("section", { class: "glass money-section", "aria-label": "Your security log" },
        el("h2", {}, "Your Security Log"),
        page.events.length ? el("div", { class: "rows" }, page.events.map((e) => el("div", { class: "row" + (WARN.has(e.kind) ? " si-warn" : "") },
          el("div", {}, el("div", { class: "row-title" }, e.what + (e.detail ? " · " + e.detail : "")),
            el("div", { class: "row-sub" }, (e.device || "This computer") + " · " + when(e.at))))))
          : el("p", { class: "empty" }, "Nothing yet. Sign-ins from your phone and other devices show here.")));
  }

  MIAShell.start(async () => draw(await load()));
})();
