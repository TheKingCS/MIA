/*
 * studio.js — the Theme Studio (DEC-0136, claude, 2026-11-08).
 * Draws MIA.themes() (core/themes.studio): pick a theme to start from, tweak its colours, corners, font, material and
 * the 3D room's light, and see it at once on this whole page (MIAShell.previewTheme, not kept) and in a little room
 * (web/nexus3d.js). Save proposes `theme.save` (core/theme_actions.py): core builds the tokens from the same choices
 * (core/themes.build_theme, the arithmetic mirrored in tokensFrom below for the live preview) and makes the checks
 * that count: an accent that reads as a warning colour, or text too faint to read. The checks here only say so early.
 * Describe One asks MIA to design a theme (MIA.designTheme, core/theme_design.py) and loads it here to tweak; Export
 * downloads what's on screen as a mia-theme/1 file; Import proposes `theme.import`, which core reads and checks.
 */
(function () {
  "use strict";
  const { el } = MIAShell;
  const $ = (id) => document.getElementById(id);
  let data = null, base = null, picks = null, own = null, room = null, roomTimer = 0, savedName = "";
  let described = "", designNote = "", designedName = "";  // MIA's last design, kept while you tweak it

  // ------------------------------------------------------------ colour arithmetic (mirrors core/themes.py)
  const rgbOf = (h) => { const n = parseInt(h.slice(1, 7), 16); return [n >> 16 & 255, n >> 8 & 255, n & 255]; };
  const hexOf = (c) => "#" + c.map((v) => Math.max(0, Math.min(255, Math.round(v))).toString(16).padStart(2, "0")).join("");
  const mix = (a, b, t) => { const x = rgbOf(a), y = rgbOf(b); return hexOf(x.map((v, i) => v + (y[i] - v) * t)); };
  const triplet = (h) => rgbOf(h).join(", ");
  function contrast(a, b) {
    const lum = (h) => rgbOf(h).map((v) => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); })
      .reduce((s, v, i) => s + v * [0.2126, 0.7152, 0.0722][i], 0);
    const [hi, lo] = [lum(a), lum(b)].sort((p, q) => q - p);
    return (hi + 0.05) / (lo + 0.05);
  }
  function accentProblem(h) {
    const [r, g, b] = rgbOf(h).map((v) => v / 255);
    const max = Math.max(r, g, b), min = Math.min(r, g, b), l = (max + min) / 2, d = max - min;
    const s = d === 0 ? 0 : d / (1 - Math.abs(2 * l - 1));
    if (s < 0.35 || l > 0.85 || l < 0.12) return "";
    let hue = d === 0 ? 0 : max === r ? ((g - b) / d) % 6 : max === g ? (b - r) / d + 2 : (r - g) / d + 4;
    hue = (hue * 60 + 360) % 360;
    const hit = data.meaning_hues.find((m) => Math.min(Math.abs(hue - m.hue), 360 - Math.abs(hue - m.hue)) < 20);
    return hit ? "That accent would look like " + hit.meaning + ". Try a blue, violet, pink, cyan or white." : "";
  }
  function tokensFrom(c, b) {
    const r = Math.max(0, Math.min(28, Math.round(Number(c.radius) || 0)));
    const font = (data.fonts.find((f) => f.id === c.font) || data.fonts[0]).stack;
    return Object.assign({}, (b && b.tokens) || {}, {
      "--accent": c.accent, "--rgb-accent": triplet(c.accent),
      "--accent-soft": mix(c.accent, "#ffffff", 0.6), "--accent-deep": mix(c.accent, "#000000", 0.45),
      "--bg": c.background, "--rgb-bg": triplet(c.background), "--bg-soft": mix(c.background, "#ffffff", 0.025),
      "--rgb-panel": triplet(c.panel), "--rgb-panel-2": triplet(mix(c.panel, "#ffffff", 0.04)),
      "--rgb-panel-3": triplet(mix(c.panel, "#ffffff", 0.09)), "--surface-solid": c.panel,
      "--text": c.text, "--text-dim": mix(c.text, c.background, 0.3), "--text-faint": mix(c.text, c.background, 0.45),
      "--rgb-line": triplet(c.line), "--radius": r + "px", "--radius-sm": Math.round(r * 0.66) + "px", "--font": font,
    });
  }
  function roomFrom(c, b) {
    const out = Object.assign({}, (b && b.room) || {}, { accent: c.accent });
    Object.keys(data.levels).forEach((k) => { if (typeof c[k] === "number") out[k] = c[k]; });
    if (c.palette && c.palette.length) out.palette = c.palette.slice(0, 6); else delete out.palette;
    return out;
  }

  // ------------------------------------------------------------ the preview
  function problems() {
    const out = [];
    const a = accentProblem(picks.accent);
    if (a) out.push(a);
    if (contrast(picks.text, picks.background) < data.min_contrast || contrast(picks.text, picks.panel) < data.min_contrast) {
      out.push("The text would be hard to read on that background. Make one lighter or darker.");
    }
    return out;
  }
  function preview() {
    const theme = { id: base.id, name: "Preview", tokens: tokensFrom(picks, base), material: picks.material, room: roomFrom(picks, base) };
    MIAShell.previewTheme(theme);
    const issues = problems();
    $("st-issues").replaceChildren(...issues.map((p) => el("p", { class: "st-issue" }, p)));
    $("st-save").disabled = $("st-use").disabled = issues.length > 0;
    clearTimeout(roomTimer);
    roomTimer = setTimeout(() => mountRoom(theme.room), 250);
  }
  function mountRoom(light) {
    const canvas = $("st-room");
    if (!canvas || !(window.MIARoom && MIARoom.supported())) { if (canvas) canvas.hidden = true; return; }
    if (room) room.stop();
    const fresh = canvas.cloneNode(false);  // a stopped room hands its GL context back, so draw on a fresh canvas
    canvas.replaceWith(fresh);
    room = MIARoom.mount(fresh, data.sample, { start: 1, theme: light });
  }

  // ------------------------------------------------------------ controls
  const LEVEL_NAMES = { fire: "Fire", bloom: "Glow", mist: "Mist", scan: "Scanlines", grain: "Film grain" };
  const MATERIAL_NAMES = { solid: "Solid", glass: "Glass", chrome: "Chrome", wire: "Wire" };
  function colour(key, label) {
    const input = el("input", { type: "color", value: picks[key], "aria-label": label,
      oninput: (e) => { picks[key] = e.target.value; preview(); } });
    return el("label", { class: "st-colour" }, input, el("span", {}, label));
  }
  function slider(key, label, low, high, step) {
    const out = el("output", {}, String(picks[key]));
    const input = el("input", { type: "range", min: String(low), max: String(high), step: String(step), value: String(picks[key]),
      "aria-label": label, oninput: (e) => { picks[key] = Number(e.target.value); out.textContent = e.target.value; preview(); } });
    return el("label", { class: "st-slider" }, el("span", {}, label), input, out);
  }
  function select(key, label, options) {
    const input = el("select", { "aria-label": label, onchange: (e) => { picks[key] = e.target.value; preview(); } },
      options.map(([v, text]) => el("option", { value: v, selected: v === picks[key] ? "" : null }, text)));
    return el("label", { class: "st-select" }, el("span", {}, label), input);
  }
  function palette() {
    const on = el("input", { type: "checkbox", checked: picks.palette.length ? "" : null, onchange: (e) => {
      picks.palette = e.target.checked ? [picks.accent, mix(picks.accent, "#8a5cff", 0.6), mix(picks.accent, "#35d4ff", 0.6)] : [];
      paint(); } });
    const row = el("div", { class: "st-palette" }, picks.palette.map((c, i) => el("input", { type: "color", value: c,
      "aria-label": "Mist colour " + (i + 1), oninput: (e) => { picks.palette[i] = e.target.value; preview(); } })));
    return el("div", {}, el("label", { class: "st-check" }, on, el("span", {}, "Colour the room's mist and vapor")), picks.palette.length ? row : null);
  }

  function start(theme) {
    base = theme;
    picks = Object.assign({}, theme.choices, { palette: (theme.choices.palette || []).slice() });
    own = theme.own ? theme.id : null;
    designNote = ""; designedName = "";
    paint();
  }

  // MIA designs one (core/theme_design.design): it loads here to look at and tweak; nothing is kept until you save.
  async function designIt() {
    described = $("st-describe").value.trim();
    if (!described) return;
    try {
      const made = await MIA.designTheme(described);
      base = data.themes.find((t) => t.id === made.base) || data.themes[0];
      picks = Object.assign({}, made.choices, { palette: (made.choices.palette || []).slice() });
      own = null;
      designNote = made.summary; designedName = made.name;
      paint();
    } catch (e) { MIAShell.say(e.message); }
  }

  // A theme as a file (core/theme_actions.export's shape): what's on screen now, so a tweak can be shared unsaved.
  function exportIt() {
    const name = $("st-name").value.trim() || base.name;
    const file = { format: data.file_format, name, line: base.line || "", choices: picks, tokens: tokensFrom(picks, base),
      material: picks.material, room: roomFrom(picks, base) };
    const url = URL.createObjectURL(new Blob([JSON.stringify(file, null, 2)], { type: "application/json" }));
    const a = el("a", { href: url, download: name.replace(/[^\w -]+/g, "").trim().replace(/\s+/g, "-").toLowerCase() + ".mia-theme.json" });
    document.body.append(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 2000);
  }
  function importIt(input) {
    const f = input.files && input.files[0];
    if (!f) return;
    if (f.size > 20000) { MIAShell.say("That file is too big to be a theme."); return; }
    f.text().then((text) => {
      try { savedName = (JSON.parse(text).name || "").trim(); } catch (e) { savedName = ""; }
      return MIAShell.act({ kind: "theme.import", params: { file: text } });  // core reads and checks it
    }).finally(() => { input.value = ""; });
  }

  async function save(use) {
    const name = $("st-name").value.trim();
    savedName = name;
    const params = { name, choices: picks, base: base.id, use };
    if (own) params.id = own;
    await MIAShell.act({ kind: "theme.save", params });
  }

  function paint() {
    const chips = data.themes.map((t) => el("button", { type: "button", class: "chip-button st-theme" + (t.id === base.id ? " on" : ""),
      "aria-pressed": String(t.id === base.id), onclick: () => start(t) },
      el("i", { class: "st-swatch", style: "background:" + t.choices.accent + ";box-shadow:0 0 10px " + t.choices.accent }),
      t.name, t.own ? el("small", {}, "yours") : null, t.id === data.current ? el("small", {}, "in use") : null));
    const name = designedName || (own ? base.name : "My " + base.name);
    const describe = el("section", { class: "glass st-describe", "aria-label": "Describe a theme" },
      el("h2", { class: "pw-label" }, "Describe One"),
      el("div", { class: "st-describe-row" },
        el("input", { id: "st-describe", type: "text", maxlength: "300", value: described,
          placeholder: "A rainy Tokyo night. Calm ocean glass. Loud 2000s rave.", "aria-label": "Describe a theme",
          onkeydown: (e) => { if (e.key === "Enter") designIt(); } }),
        el("button", { type: "button", class: "btn", onclick: designIt }, "Design It")),
      designNote ? el("p", { class: "st-designed", role: "status" }, designNote) : null);
    $("panel").replaceChildren(
      describe,
      el("section", { class: "st-start", "aria-label": "Start from" }, el("h2", { class: "pw-label" }, "Start From"), el("div", { class: "chip-row" }, ...chips)),
      el("div", { class: "st-grid" },
        el("section", { class: "glass st-controls", "aria-label": "Tweak" },
          el("h2", { class: "pw-label" }, "Colours"),
          el("div", { class: "st-colours" }, colour("accent", "Accent"), colour("background", "Background"), colour("panel", "Panels"),
            colour("text", "Text"), colour("line", "Lines")),
          el("h2", { class: "pw-label" }, "Shape and Type"),
          slider("radius", "Corners", 0, 28, 1),
          select("font", "Font", data.fonts.map((f) => [f.id, f.label])),
          select("material", "Panels", data.materials.map((m) => [m, MATERIAL_NAMES[m] || m])),
          el("h2", { class: "pw-label" }, "The Room"),
          ...Object.keys(data.levels).map((k) => slider(k, LEVEL_NAMES[k] || k, data.levels[k][0], data.levels[k][1], 0.05)),
          palette(),
          el("h2", { class: "pw-label" }, "Keep It"),
          el("label", { class: "st-select" }, el("span", {}, "Name"), el("input", { id: "st-name", type: "text", maxlength: "40", value: name })),
          el("div", { id: "st-issues", role: "status" }),
          el("div", { class: "st-actions" },
            el("button", { id: "st-use", type: "button", class: "btn", onclick: () => save(true) }, "Save and Use"),
            el("button", { id: "st-save", type: "button", class: "btn btn-ghost", onclick: () => save(false) }, own ? "Save" : "Save as Mine"),
            el("button", { type: "button", class: "btn btn-ghost", onclick: () => start(base) }, "Start Over"),
            own ? el("button", { type: "button", class: "btn btn-ghost st-delete", onclick: () => MIAShell.act({ kind: "theme.delete", params: { id: own } }) }, "Delete") : null),
          el("h2", { class: "pw-label" }, "Share It"),
          el("div", { class: "st-actions" },
            el("button", { type: "button", class: "btn btn-ghost", onclick: exportIt }, "Export"),
            el("label", { class: "btn btn-ghost st-import" }, "Import",
              el("input", { type: "file", accept: ".json,application/json", onchange: (e) => importIt(e.target) })))),
        el("section", { class: "st-preview", "aria-label": "Preview" },
          el("h2", { class: "pw-label" }, "Preview"),
          el("canvas", { id: "st-room", class: "st-room", "aria-hidden": "true" }),
          el("div", { class: "strip" },
            el("div", { class: "stat attention" }, el("span", {}, el("span", { class: "stat-label" }, "Needs You"), el("span", { class: "stat-value" }, "3"))),
            el("div", { class: "stat" }, el("span", {}, el("span", { class: "stat-label" }, "Coming Up"), el("span", { class: "stat-value" }, "5"))),
            el("div", { class: "stat ok" }, el("span", {}, el("span", { class: "stat-label" }, "Done Today"), el("span", { class: "stat-value" }, "2")))),
          el("div", { class: "glass st-sample" },
            el("h3", {}, "A card in this theme"),
            el("p", { class: "dim" }, "Text, lines and panels the way every screen will show them."),
            el("div", { class: "row" }, el("div", {}, el("div", { class: "row-title" }, "Change the oil"), el("div", { class: "row-sub" }, "Pickup truck")),
              el("span", { class: "chip chip-bad" }, "Overdue")),
            el("div", { class: "row" }, el("div", {}, el("div", { class: "row-title" }, "Water the beds"), el("div", { class: "row-sub" }, "Greenhouse")),
              el("span", { class: "chip chip-soon" }, "Soon")),
            el("div", { class: "row" }, el("div", {}, el("div", { class: "row-title" }, "Morning workout"), el("div", { class: "row-sub" }, "Workout")),
              el("span", { class: "chip chip-ok" }, "Done")),
            el("div", { class: "st-actions" }, el("span", { class: "btn" }, "A Button"), el("span", { class: "btn btn-ghost" }, "Another")),
            el("p", { class: "st-note" }, "Amber, red, green and gold keep their meanings in every theme.")))));
    preview();
  }

  MIAShell.start(async () => {
    data = await MIA.themes();
    const wanted = (savedName && data.themes.find((t) => t.name === savedName)) || data.themes.find((t) => t.id === data.current) || data.themes[0];
    savedName = "";
    start(wanted);
  }, { refreshOnChange: false });  // a change elsewhere in MIA mustn't throw away what you're tweaking
})();
