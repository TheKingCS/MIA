/*
 * showoff.js — show-off mode (claude, 2026-10-17, DEC-0031). Renders
 * MIA.showoff() (core/show_off.py) as a narrated tour, one card at a
 * time: Back / Next / Stop, arrow keys, and MIA reading each card aloud
 * when Voice is on (the browser's own speech; nothing leaves the device).
 * The data was filtered in core: no money, journal, memories, health or
 * people. No Talk on this page. Formatting only.
 */
(function () {
  "use strict";
  const { el } = MIAShell;
  const $ = (id) => document.getElementById(id);
  let tour = null, at = 0, voice = false;

  const bar = (percent, cls) => el("span", { class: "tour-bar " + (cls || "") }, el("span", { style: "width:" + Math.max(0, Math.min(100, percent)) + "%" }));
  const BODY = {
    hello: (s) => el("div", { class: "tour-orb", "aria-hidden": "true" }, el("span", {})),
    level: (s) => [el("div", { class: "tour-big" }, "LV " + s.level), bar(s.percent), el("p", { class: "dim" }, s.total_xp.toLocaleString() + " XP all time"),
      s.top_skills.length ? el("ul", { class: "tour-list" }, s.top_skills.map((k) => el("li", {}, el("span", {}, k.icon + " " + k.name), el("strong", {}, "Lv " + k.level)))) : null],
    stats: (s) => el("ul", { class: "tour-list" }, s.stats.map((a) => el("li", {}, el("span", {}, a.icon + " " + a.name), bar(100 * a.value / a.max), el("strong", {}, String(a.value))))),
    buffs: (s) => el("div", { class: "buff-row" }, s.buffs.map((b) => el("span", { class: "buff" }, el("span", { class: "buff-ico" }, b.icon),
      el("span", { class: "buff-name" }, b.name), el("small", { class: "buff-left" }, "+1 " + b.stat)))),
    missions: (s) => [s.boss ? el("div", { class: "tour-boss" }, el("span", {}, s.boss.icon + " " + s.boss.name), bar(s.boss.percent, "hp"),
      el("small", { class: "dim" }, s.boss.phase + " · " + s.boss.percent + "% HP")) : null,
      el("ul", { class: "tour-list" }, s.missions.map((m) => el("li", {}, el("span", {}, m.icon + " " + m.name), bar(m.percent), el("strong", {}, m.percent + "%"))))],
    gear: (s) => el("ul", { class: "tour-list" }, s.gear.map((g) => el("li", { class: "tone-" + g.tone }, el("span", {}, g.name), bar(g.percent), el("strong", {}, g.label)))),
    crafting: (s) => {
      const parts = [el("div", { class: "tour-tiles" },
        el("div", {}, el("strong", {}, String(s.recipes)), el("span", { class: "dim" }, s.recipes === 1 ? "recipe" : "recipes")),
        el("div", {}, el("strong", {}, String(s.built)), el("span", { class: "dim" }, "built")))];
      if (s.recipe) parts.push(el("p", {}, "🪚 " + s.recipe.name + ": " + s.recipe.materials + " materials, " + s.recipe.steps + " steps" + (s.recipe.ready ? ", ready to build" : "")));
      if (s.photo) {
        const img = el("img", { class: "tour-photo", alt: "A finished build" });
        MIA.image("/api/workshop/builds/" + encodeURIComponent(s.photo.job_id) + "/media?name=" + encodeURIComponent(s.photo.name)).then((src) => { if (src) img.src = src; else img.remove(); });
        parts.push(img);
      }
      return parts;
    },
    shop: (s) => [el("div", { class: "tour-big" }, s.credits.toLocaleString() + " cr"),
      el("ul", { class: "tour-list" }, s.rewards.map((r) => el("li", {}, el("span", {}, r.icon + " " + r.name), el("strong", {}, r.cost.toLocaleString() + " cr"))))],
    chronicle: (s) => [el("h3", { class: "tour-chapter" }, s.name), ...s.story.map((line) => el("p", {}, line))],
    glasses: () => el("a", { class: "btn btn-ghost", href: "glasses.html" }, "See The Glasses View"),
    finale: () => el("div", { class: "tour-orb", "aria-hidden": "true" }, el("span", {})),
  };

  function speak(text) {
    if (!voice || !window.speechSynthesis) return;
    speechSynthesis.cancel();
    speechSynthesis.speak(new SpeechSynthesisUtterance(text));
  }

  function draw() {
    const s = tour.steps[at];
    const last = at === tour.steps.length - 1;
    $("panel").replaceChildren(el("article", { class: "glass glow tour-card", "data-step": s.key },
      el("div", { class: "tour-count" }, (at + 1) + " / " + tour.steps.length),
      el("h1", {}, s.key === "hello" && s.name ? "Hi, I'm MIA" : s.title),
      el("p", { class: "tour-say" }, s.say),
      el("div", { class: "tour-body" }, [].concat((BODY[s.key] || (() => null))(s))),
      el("div", { class: "tour-nav" },
        el("button", { type: "button", class: "btn btn-ghost", disabled: at === 0 ? true : null, onclick: () => go(-1) }, "Back"),
        el("button", { type: "button", class: "btn btn-ghost", "aria-pressed": String(voice), onclick: () => { voice = !voice; if (!voice && window.speechSynthesis) speechSynthesis.cancel(); draw(); } },
          voice ? "🔊 Voice On" : "🔇 Voice Off"),
        last ? el("a", { class: "btn btn-green", href: "index.html" }, "Done")
          : el("button", { type: "button", class: "btn btn-green", onclick: () => go(1) }, "Next")),
      el("a", { class: "tour-stop", href: "index.html" }, "Stop the tour")));
    speak(s.say);
  }

  function go(by) {
    at = Math.max(0, Math.min(tour.steps.length - 1, at + by));
    draw();
  }

  document.addEventListener("keydown", (e) => {
    if (!tour) return;
    if (e.key === "ArrowRight") go(1);
    if (e.key === "ArrowLeft") go(-1);
    if (e.key === "Escape") location.href = "index.html";
  });

  MIAShell.start(async () => {
    tour = tour || await MIA.showoff();
    draw();
  }, { talk: false, refreshOnChange: false });
})();
