/*
 * vault.js — Memory Vault (claude, 2026-10-18, DEC-0030 phase E). Renders
 * MIA.vault() (core/memory_vault.py) in tabs: Photos (one month at a time,
 * by day, with what happened that day and the trip it was on; each tile
 * says whether it's safe on the home computer), Free Up Space (photos the
 * PC holds, exact copies, bursts with the best shot), and Set Up.
 *
 * Freeing space is only ever an offer: MIA asks the home computer to
 * check each file again first (MIA.vaultFreePlan), then Android's own
 * dialog asks the person and moves them to its Trash (window.MIAAndroid,
 * the phone app's bridge: android-phone/.../Gallery.kt). Formatting only.
 */
(function () {
  "use strict";
  const { el, act, say } = MIAShell;
  const $ = (id) => document.getElementById(id);
  const TABS = [["photos", "Photos"], ["space", "Free Up Space"], ["setup", "Set Up"]];
  const android = window.MIAAndroid || null;
  let page = null, month = "", wantOn = false, trashDone = null;
  let tab = TABS.some(([t]) => t === location.hash.slice(1)) ? location.hash.slice(1) : "photos";

  const btn = (label, cls, onclick) => el("button", { type: "button", class: "btn " + cls, onclick }, label);
  const section = (title, actions, ...body) =>
    el("section", { class: "glass money-section" }, el("div", { class: "sect" }, el("h2", {}, title), actions), ...body);
  const plural = (n, one, many) => n + " " + (n === 1 ? one : (many || one + "s"));

  // ------------------------------------------------------------ the phone app's bridge
  function access() {
    try { return android ? String(android.galleryAccess()) : "none"; } catch (e) { return "none"; }
  }
  function canTrash() {
    try { return !!(android && android.canTrash()); } catch (e) { return false; }
  }
  window.MIAGallery = {
    // Android answered the permission question.
    onAccess: (state) => { if (wantOn && (state === "granted" || state === "partial")) switchOn(); else if (wantOn) say("MIA can't see your photos without that. You can allow it any time."); wantOn = false; },
    // Android's own Trash dialog closed.
    onTrashed: (ok) => { if (trashDone) { trashDone(!!ok); trashDone = null; } },
  };
  const trash = (paths) => new Promise((resolve) => { trashDone = resolve; android.trash(JSON.stringify(paths)); });

  async function switchOn() {
    if (android && access() === "needed") { wantOn = true; android.askGallery(); return; }
    await act({ kind: "setting.set", params: { key: "vault.on", value: true } });
  }
  const setting = (key, value) => act({ kind: "setting.set", params: { key, value } });

  async function free(what) {
    if (MIA.demo) { say("Freeing space works in the MIA phone app."); return; }
    if (!canTrash()) { say("Freeing space works in the MIA phone app, on Android 11 or newer."); return; }
    say(what === "copies" ? "Finding the extra copies…" : "Asking the home computer to check each one again…");
    let plan;
    try { plan = await MIA.vaultFreePlan(what); } catch (e) { say(e.message); return; }
    if (!plan.count) {
      say(plan.not_confirmed ? "The home computer couldn't confirm those yet, so nothing will be removed." : "Nothing to free right now.");
      return;
    }
    const sure = await MIAShell.confirm((what === "copies" ? "Remove " + plural(plan.paths.length, "extra copy", "extra copies") :
      "Free " + plural(plan.count, "photo or video", "photos and videos") + " from this phone") +
      "? " + (what === "copies" ? "One copy of each stays on the phone." : "The home computer just checked each one: they're safe there.") +
      " Android asks you next, and keeps them in its Trash for 30 days.");
    if (!sure) return;
    const ok = await trash(plan.paths);
    if (!ok) { say("Nothing was removed."); return; }
    try { say((await MIA.vaultFreeDone(plan.paths, what)).message); } catch (e) { say(e.message); }
    MIAShell.refresh();
  }

  // ------------------------------------------------------------ tiles and the viewer
  const seen = new IntersectionObserver((entries) => entries.forEach((e) => {
    if (!e.isIntersecting) return;
    seen.unobserve(e.target);
    MIA.image(e.target.dataset.src).then((src) => { if (src) e.target.src = src; });
  }), { rootMargin: "400px" });

  function tile(item) {
    const img = el("img", { alt: item.name + (item.time ? ", " + item.time : ""), "data-src": "/api/vault/photo/" + item.sha });
    const marks = [
      !item.on_phone ? el("span", { class: "vault-mark ok", title: "Only on the home computer now" }, "PC only") :
        item.on_pc ? el("span", { class: "vault-mark ok", title: "Safe on the home computer" }, "✓ PC") :
        el("span", { class: "vault-mark wait", title: "Not on the home computer yet" }, "⏳"),
      item.best ? el("span", { class: "vault-mark best", title: "Best of the burst" }, "★") : null,
      item.copies > 1 ? el("span", { class: "vault-mark", title: "On the phone " + item.copies + " times" }, "×" + item.copies) : null,
    ].filter(Boolean);
    // The marks' meaning for a screen reader too (Muse, H-0063 §4).
    const status = [!item.on_phone ? "only on the home computer now" : item.on_pc ? "safe on the home computer" : "not on the home computer yet",
      item.best ? "best of the burst" : "", item.copies > 1 ? "on the phone " + item.copies + " times" : ""].filter(Boolean).join(", ");
    const t = el("button", { type: "button", class: "media-tile vault-tile kind-" + (item.kind === "video" ? "video" : "image"),
      "aria-label": (item.kind === "video" ? "Video " : "Photo ") + item.name + ", " + status, onclick: () => view(item) },
      item.kind === "video" ? el("span", { class: "media-ico", "aria-hidden": "true" }, "▶") : img,
      el("span", { class: "vault-marks" }, ...marks));
    if (item.kind !== "video") seen.observe(img);
    return t;
  }

  async function view(item) {
    const box = el("dialog", { class: "confirm vault-view", "aria-label": item.name });
    const close = () => { box.close(); box.remove(); };
    const body = el("div", { class: "vault-full" }, el("p", { class: "dim" }, "Opening…"));
    box.append(body, el("div", { class: "confirm-actions" },
      el("span", { class: "dim" }, item.name + (item.on_pc ? " · safe on the home computer" : " · not on the home computer yet")),
      btn("Close", "btn-ghost", close)));
    box.oncancel = (e) => { e.preventDefault(); close(); };
    document.body.append(box);
    box.showModal();
    try {
      const url = URL.createObjectURL(await MIA.download("/api/vault/photo/" + item.sha + "?full=1"));
      body.replaceChildren(item.kind === "video" ? el("video", { src: url, controls: true, playsinline: true, class: "vault-media" })
        : el("img", { src: url, alt: item.name, class: "vault-media" }));
    } catch (e) { body.replaceChildren(el("p", { class: "empty" }, e.message)); }
  }

  // ------------------------------------------------------------ views
  function offNote() {
    if (page.on) return null;
    return section("Keep Your Photos Safe", null,
      el("p", {}, "Switch the vault on and MIA copies this phone's photos and videos to your home computer, on Wi-Fi, by itself. " +
        "Then the phone can let old ones go, only when you say so."),
      el("p", { class: "dim" }, "MIA never deletes anything. Before it offers to free space, the home computer checks each photo again; then Android asks you itself."),
      el("div", { class: "row-buttons" }, btn("Turn On The Vault", "btn-amber", switchOn)));
  }

  function photos() {
    const parts = [offNote()];
    if (!page.months.length) {
      parts.push(section("Photos", null, el("p", { class: "empty" }, page.on ? "No photos found yet. MIA looks through the camera roll every minute." :
        "Nothing here yet.")));
      return parts.filter(Boolean);
    }
    const pick = el("select", { "aria-label": "Month", onchange: async (e) => { month = e.target.value; MIAShell.refresh(); } },
      page.months.map((m) => el("option", { value: m.month, selected: m.month === page.month ? true : null }, m.label + " · " + m.count)));
    parts.push(el("div", { class: "vault-month" }, pick));
    // What the marks mean, once: there's no hover on a phone (Muse, H-0063 §1).
    parts.push(el("p", { class: "dim vault-legend" },
      "✓ PC safe on the home computer · ⏳ not yet copied · ★ best of the burst · ×2 on the phone twice · PC only freed from the phone"));
    // Days are plain, a hairline between them; cards stay for the sections with actions (H-0063 §2).
    page.days.forEach((d) => parts.push(el("section", { class: "vault-day", "aria-label": d.label },
      el("div", { class: "vault-day-head" }, el("h2", {}, d.label), d.trip ? el("span", { class: "craft-tag" }, "🏕 " + d.trip) : null),
      d.happened.length ? el("p", { class: "dim vault-happened" }, "That day: " + d.happened.join(" · ")) : null,
      el("div", { class: "media-grid" }, d.items.map(tile)))));
    return parts.filter(Boolean);
  }

  function space() {
    const f = page.free, c = page.copies;
    const why = { off: "Turn the vault on first.", not_linked: "Link your home computer first (Settings → Home Computer).",
      waiting_wifi: "They're waiting for Wi-Fi to reach the home computer.", waiting_pc: "They're waiting for the home computer.",
      sending: "MIA is still copying them.", safe: "" }[page.state] || "";
    return [
      section("Free Up Space", null, f.count
        ? [el("p", {}, plural(f.count, "photo or video", "photos and videos") + " older than " + plural(f.older_than_days, "day") +
            " (" + f.size + ") are safe on your home computer."),
           el("div", { class: "row-buttons" }, btn("Free " + f.size, "btn-amber", () => free("old")))]
        : el("p", { class: "empty" }, "Nothing to free yet. " + (why || "Photos older than " + plural(f.older_than_days, "day") +
            " that are safe on the home computer show here."))),
      section("Exact Copies", null, c.count
        ? [el("p", {}, plural(c.count, "photo is", "photos are") + " on this phone more than once (" + c.size + "). One copy of each stays."),
           el("div", { class: "row-buttons" }, btn("Remove The Extra Copies", "btn-ghost", () => free("copies")))]
        : el("p", { class: "empty" }, "No photo is on this phone twice.")),
      section("Bursts", null, page.bursts.length
        ? el("div", { class: "rows" }, page.bursts.map((b) => el("div", { class: "row money-row vault-burst" },
            el("div", {}, el("div", { class: "row-title" }, plural(b.count, "shot") + " · " + b.day),
              el("div", { class: "row-sub" }, (b.scored ? "★ The sharpest, best-lit one is marked." : "★ The most detailed one is marked; the home computer looks closer once it has them.") +
                " Just a suggestion.")),
            el("div", { class: "vault-burst-tiles" }, (() => {
              const img = el("img", { alt: "The best shot", class: "vault-best", "data-src": "/api/vault/photo/" + b.best });
              seen.observe(img);
              return img;
            })()),
            el("div", { class: "row-buttons" }, b.others_safe
              ? btn("Keep The Best, Free " + b.others_on_phone + " (" + b.size + ")", "btn-ghost btn-small", () => free("burst:" + b.id))
              : el("span", { class: "dim" }, "Copying first.")))))
        : el("p", { class: "empty" }, "No bursts on the phone.")),
      page.freed.length ? section("Freed", null, el("div", { class: "rows" }, page.freed.map((x) =>
        el("div", { class: "row" }, el("div", { class: "row-title" }, plural(x.count, "file") + " · " + x.size),
          el("div", { class: "row-sub" }, new Date(x.at).toLocaleString()))))) : null,
    ].filter(Boolean);
  }

  function setup() {
    const s = page.summary;
    const toggle = (label, key, on) => el("label", { class: "tick-row" },
      el("input", { type: "checkbox", checked: on ? true : null,
        onchange: (e) => (key === "vault.on" && e.target.checked ? switchOn() : setting(key, e.target.checked)) }), el("span", {}, label));
    return [
      section("The Vault", page.on ? btn("Copy Now", "btn-ghost btn-small", async () => {
        try { say((await MIA.vaultNow()).message); } catch (e) { say(e.message); } }) : null,
        el("p", {}, page.state_words),
        toggle("Keep my photos safe on the home computer", "vault.on", page.on),
        toggle("Copy only on Wi-Fi", "vault.wifi_only", page.wifi_only),
        el("label", { class: "form-row" }, el("span", {}, "Keep recent photos on the phone (days)"),
          el("input", { type: "number", min: "0", max: "365", value: String(page.keep_days),
            onchange: (e) => setting("vault.keep_days", Number(e.target.value)) })),
        s.last_sent ? el("p", { class: "dim" }, "Last copied " + new Date(s.last_sent).toLocaleString() + ".") : null,
        android && access() === "partial" ? el("p", { class: "dim" }, "MIA can see only the photos you picked. To keep them all safe, allow all photos for MIA in Android's settings.") : null),
      section("How It Works", null,
        el("p", { class: "dim" }, "Each photo is known by its fingerprint, so a copy that was cut off picks up where it stopped and nothing is copied twice. " +
          "The home computer checks the whole file before it keeps it, and again before MIA offers to free it. " +
          "On the computer they're in your MIA folder, vault, by year and month.")),
    ];
  }

  const VIEWS = { photos, space, setup };

  function draw() {
    const s = page.summary;
    $("strip").replaceChildren(
      el("div", { class: "cell ok" }, el("span", { class: "n" }, s.photos), el("span", { class: "t" }, "Photos")),
      el("div", { class: "cell ok" }, el("span", { class: "n" }, s.videos), el("span", { class: "t" }, "Videos")),
      el("div", { class: "cell ok" }, el("span", { class: "n" }, s.on_pc), el("span", { class: "t" }, "Safe On PC")),
      el("div", { class: "cell " + (s.waiting ? "soon" : "ok") }, el("span", { class: "n" }, s.waiting), el("span", { class: "t" }, "Waiting")));
    $("tabs").hidden = false;
    $("tabs").replaceChildren(...TABS.map(([id, l]) => el("button", { type: "button", role: "tab", "aria-selected": String(id === tab),
      onclick: () => { tab = id; history.replaceState(null, "", "#" + id); draw(); } }, l)));
    $("panel").replaceChildren(el("p", { class: "dim vault-state" }, page.state_words), ...[].concat(VIEWS[tab]()));
  }

  MIAShell.start(async () => {
    page = await MIA.vault(month);
    if (!page.available) { $("panel").replaceChildren(el("p", { class: "empty" }, "The vault isn't set up on this MIA.")); return; }
    month = page.month;
    draw();
  });
})();
