/*
 * profile.js — the Profile screen (claude, 2026-10-07; Zac: the gear's
 * Profile). Renders MIA.profile() (core/web_account.py): your level, name,
 * email, country, what MIA helps with, household, password and recovery
 * code. Name, email, country and interests are one action (profile.edit),
 * so they're confirmed and undoable; the password and a new recovery code
 * have their own calls, so a password never sits in a proposal.
 */
(function () {
  "use strict";
  const { el, act, say } = MIAShell;
  const $ = (id) => document.getElementById(id);
  let page = null;
  let freshCode = "";  // shown until you leave: saving it redraws the page

  const section = (title, ...body) => el("section", { class: "glass money-section" }, el("div", { class: "sect" }, el("h2", {}, title)), ...body);
  const row = (label, input) => el("label", { class: "form-row" }, el("span", {}, label), input);
  const fact = (label, value) => el("div", { class: "acct-fact" }, el("span", { class: "dim" }, label), el("strong", {}, value));

  function about() {
    const name = el("input", { type: "text", autocomplete: "name", maxlength: "60" });
    name.value = page.name;
    const email = el("input", { type: "email", autocomplete: "email", disabled: page.child ? true : null });
    email.value = page.email || "";
    const country = el("select", {}, page.countries.map((c) => el("option", { value: c.code, selected: c.code === page.country ? true : null }, c.name)));
    const save = () => {
      const params = {};
      if (name.value.trim() !== page.name) params.name = name.value.trim();
      if (!page.child && email.value.trim().toLowerCase() !== (page.email || "").toLowerCase()) params.email = email.value.trim();
      if (country.value !== page.country) params.country = country.value;
      if (!Object.keys(params).length) return say("Nothing to change.");
      act({ kind: "profile.edit", params });
    };
    return section("About you", el("div", { class: "acct-form" },
      row("Name", name), row("Email (you sign in with it)", email), row("Country (money and help numbers)", country),
      el("div", { class: "acct-actions" }, el("button", { type: "button", class: "btn btn-green", onclick: save }, "Save"))));
  }

  function interests() {
    const chosen = new Set(page.interests);
    const picks = page.interest_options.map((name) => el("label", { class: "setup-chip" },
      el("input", { type: "checkbox", value: name, checked: chosen.has(name) ? true : null }), name));
    const save = () => {
      const now = picks.map((p) => p.querySelector("input")).filter((i) => i.checked).map((i) => i.value);
      if (now.join() === page.interests.join()) return say("Nothing to change.");
      act({ kind: "profile.edit", params: { interests: now } });
    };
    return section("What MIA helps with",
      el("p", { class: "dim" }, "MIA puts these first in Skills and suggests missions for them."),
      el("div", { class: "setup-interests" }, picks),
      el("div", { class: "acct-actions" }, el("button", { type: "button", class: "btn btn-green", onclick: save }, "Save")));
  }

  function household() {
    if (!page.household) return "";
    const others = page.household.others;
    return section("Household",
      fact("Name", page.household.name),
      fact("Shared with", others.length ? others.join(", ") : "Just you"),
      el("p", { class: "dim" }, "People join a household on the PC with a member's approval."));
  }

  function password() {
    const current = el("input", { type: "password", autocomplete: "current-password" });
    const next = el("input", { type: "password", autocomplete: "new-password" });
    const again = el("input", { type: "password", autocomplete: "new-password" });
    const change = async () => {
      if (next.value !== again.value) return say("The two new passwords don't match.");
      try {
        await MIA.changePassword(current.value, next.value);
        current.value = next.value = again.value = "";
        say("Password changed.");
      } catch (e) { say(e.message); }
    };
    return section("Password", el("div", { class: "acct-form" },
      row("Current password", current), row("New password (at least " + page.min_password + " characters)", next), row("New password again", again),
      el("div", { class: "acct-actions" }, el("button", { type: "button", class: "btn btn-green", onclick: change }, "Change password"))));
  }

  function recovery() {
    const box = el("div", {});
    const pw = el("input", { type: "password", autocomplete: "current-password" });
    const make = async () => {
      try {
        freshCode = (await MIA.newRecoveryCode(pw.value)).recovery_code;
        pw.value = "";
        box.replaceChildren(...shown());
      } catch (e) { say(e.message); }
    };
    const shown = () => [el("p", { class: "setup-code" }, freshCode),
      el("p", {}, "Write it down somewhere safe. Your old code no longer works, and MIA shows this one only now.")];
    if (freshCode) {
      box.append(...shown());
      return section("Recovery code", box);
    }
    box.append(el("p", { class: "dim" }, page.has_recovery_code
      ? "You have a recovery code. If you lost it, make a new one; the old one stops working."
      : "You don't have a recovery code yet. It's the way back in if you forget your password."),
    el("div", { class: "acct-form" }, row("Your password", pw),
      el("div", { class: "acct-actions" }, el("button", { type: "button", class: "btn btn-ghost", onclick: make }, "Make a new code"))));
    return section("Recovery code", box);
  }

  function draw() {
    $("hero-name").textContent = page.name;
    $("hero-tagline").textContent = (page.email || "No email yet") + (page.since ? " · since " + page.since : "");
    const level = el("div", {});
    MIAShell.levelCard(level, page.me);
    $("panel").replaceChildren(level, about(), interests(), household(), password(), recovery(),
      section("This phone", el("div", { class: "acct-actions" },
        el("a", { class: "btn btn-ghost", href: "settings.html" }, "Settings"),
        el("button", { type: "button", class: "btn btn-ghost", onclick: async () => { await MIA.signOut(); location.href = "index.html"; } }, "Log out"))));
  }

  MIAShell.start(async () => {
    page = await MIA.profile();
    if (!page.signed_in) {
      $("panel").replaceChildren(el("p", { class: "empty" }, el("strong", {}, "Sign in to see your profile."), ""));
      return;
    }
    draw();
  });
})();
