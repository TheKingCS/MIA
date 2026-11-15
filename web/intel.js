/*
 * intel.js — World (claude, 2026-11-15, DEC-0170, World Intelligence phase W1).
 *
 * Renders MIA.worldIntel() (core/web_world_intel.py) in three tabs:
 * - Needs: what each project still needs (Procurement P1, DEC-0172), with
 *   Add A Need, Got It and Not Needed.
 * - Finds: what the watches turned up, new first, each with its source named
 *   (always, Zac's rule), its link, when, which watches and why; Save or
 *   Not For Me.
 * - Watches: each watch's words, areas, how often, last look and what it
 *   found; pause, resume, stop; and Watch For to add one.
 * - Sources: the areas and the sources each reads.
 * Plus the switch: World Intelligence is off until it's turned on.
 *
 * Every change is an action (core/world_intel_actions.py). This file only
 * formats.
 */
(function () {
  "use strict";
  const { el, act, form } = MIAShell;
  const $ = (id) => document.getElementById(id);
  const TABS = [["finds", "Finds"], ["needs", "Needs"], ["watches", "Watches"], ["sources", "Sources"]];
  let page = null;
  let tab = TABS.some(([t]) => t === location.hash.slice(1)) ? location.hash.slice(1) : "finds";

  const btn = (label, cls, onclick) => el("button", { type: "button", class: "btn " + cls, onclick }, label);
  const buttons = (...list) => el("div", { class: "row-buttons" }, list.filter(Boolean));
  const section = (title, actions, ...body) =>
    el("section", { class: "glass money-section" }, el("div", { class: "sect" }, el("h2", {}, title), actions), ...body);
  const chip = (text, cls) => el("span", { class: "chip " + (cls || "") }, text);
  const go = (id) => { tab = id; history.replaceState(null, "", "#" + id); draw(); };
  const field = (name, label, type, def, required, options) => ({ name, label, type, required: !!required, options: options || [], default: def ?? null });

  async function watchFor() {
    const v = await form("Watch For", [
      field("words", "What to look for (separate phrases with commas)", "text", "", true),
      field("areas", "Areas (optional): " + page.areas.map((a) => a.id).join(", "), "text"),
      field("search", "Also search the web for it", "choice", "no", false, ["no", "yes"]),
      field("every_hours", "Look every this many hours", "int", 6),
      field("max_price", "Most it should cost (optional, for listings)", "text")], {});
    if (v) act({ kind: "world_watch.add", params: v });
  }
  const switchIt = (on) => act({ kind: "world_intel.switch", params: { on: on ? "yes" : "no" } });

  function finds() {
    const off = !page.on ? section("World Intelligence Is Off", buttons(btn("Turn On", "btn-green", () => switchIt(true))),
      el("p", {}, "Turned on, MIA reads public feeds (and your own search engine, when a watch asks) for your watches' words, a few times a day. Only those words go out.")) : null;
    if (!page.finds.length) return [off, section("Finds", buttons(btn("Watch For", "btn-green", watchFor)),
      el("p", { class: "empty" }, page.watches.length ? "Nothing found yet. Finds show up here, each with where it came from." : "Tell MIA what to watch for, and what she finds shows up here."))];
    return [off, ...page.finds.map((f) => el("article", { class: "glass closet-pick" },
      el("div", { class: "row-title" }, f.link ? el("a", { href: f.link, target: "_blank", rel: "noopener noreferrer" }, f.title) : f.title,
        f.status === "saved" ? chip("saved", "ok") : chip("new"), f.fits ? chip(f.fits, f.fits === "fits your plans" ? "ok" : "") : null),
      el("p", { class: "pw-label" }, "From " + f.source + (f.published ? " · " + f.published : "") + " · found " + f.found),
      f.summary ? el("p", { class: "dim" }, f.summary) : null,
      f.why.length ? el("p", { class: "dim" }, f.why.join(" · ")) : null,
      buttons(f.status !== "saved" ? btn("Save", "btn-green", () => act({ kind: "world_find.save", params: { discovery_id: f.id } }, { quick: true })) : null,
        btn("Not For Me", "btn-ghost", () => act({ kind: "world_find.not_for_me", params: { discovery_id: f.id } }, { quick: true })))))];
  }

  function watches() {
    const head = section("Watches", buttons(btn("Watch For", "btn-green", watchFor),
      page.on ? btn("Turn Off", "btn-ghost", () => switchIt(false)) : btn("Turn On", "btn-green", () => switchIt(true))),
      el("p", { class: "dim" }, page.on ? "Each watch reads its sources every few hours." : "World Intelligence is off: no watch is running."));
    if (!page.watches.length) return [head, el("p", { class: "empty" }, "No watches yet.")];
    return [head, ...page.watches.map((w) => el("article", { class: "glass closet-pick" },
      el("div", { class: "row-title" }, w.name, w.paused ? chip("paused") : null, w.made_by === "mia" ? chip("made by MIA") : null),
      el("p", {}, "Looking for: " + w.words),
      el("p", { class: "dim" }, [w.areas.join(", "), w.search ? "and your search engine" : "", "every " + w.every_hours + " hours",
        "last looked " + w.last_run, w.found + " found"].filter(Boolean).join(" · ")),
      w.reason ? el("p", { class: "dim" }, w.reason) : null,
      w.refused.length ? el("p", { class: "attention" }, "Turned the reader away (waiting for you): " + w.refused.join(", ")) : null,
      buttons(btn(w.paused ? "Resume" : "Pause", "btn-ghost", () => act({ kind: "world_watch.pause", params: { watch_id: w.id, paused: w.paused ? "no" : "yes" } }, { quick: true })),
        btn("Stop Watching", "btn-ghost", () => act({ kind: "world_watch.remove", params: { watch_id: w.id } })))))];
  }

  function sources() {
    const mute = (s, yes) => act({ kind: "world_source.mute", params: { source_id: s.id, mute: yes ? "yes" : "no" } }, { quick: true });
    const rows = (page.sources || []).filter((s) => s.finds || s.muted || s.suggest_mute);
    const judged = rows.length ? section("How Each Source Is Doing", null,
      el("p", { class: "dim" }, "The last 30 days. A source that keeps giving finds you set aside, and none you save, is suggested for muting."),
      el("div", { class: "rows" }, rows.map((s) => el("div", { class: "row money-row" },
        el("div", {}, el("div", { class: "row-title" }, s.name, s.muted ? chip("muted") : null, s.suggest_mute ? chip("mute?", "attention") : null),
          el("div", { class: "row-sub" }, s.finds + " found · " + s.saved + " saved · " + s.not_for_me + " set aside")),
        btn(s.muted ? "Unmute" : "Mute", "btn-ghost btn-small", () => mute(s, !s.muted)))))) : null;
    return [judged, ...page.areas.map((a) => section(a.name, null,
      a.sources.length ? el("p", { class: "dim" }, a.sources.join(" · ")) : el("p", { class: "dim" }, "Your search engine, and the listings sources in the next phase.")))];
  }

  // Needs (core/requirements.py, DEC-0172): what each project still needs; a find that fits one ranks first.
  async function addNeed(project) {
    const v = await form("What Does " + project.name + " Need?", [
      field("item", "Item", "text", "", true), field("quantity", "How many", "text", "1"),
      field("unit", "Unit (optional)", "text"), field("specs", "What it has to be (optional)", "text"),
      field("max_price", "Most it should cost (optional)", "text"),
      field("condition", "Condition", "choice", "any", false, ["any", "new", "used"]),
      field("priority", "Priority", "choice", "first", false, ["first", "later", "nice to have"])], {});
    if (v) act({ kind: "requirement.add", params: Object.assign({ project_id: project.id }, v) });
  }
  function needs() {
    const head = section("What Your Projects Need", buttons(btn("Check What's On Hand", "btn-ghost", () => act({ kind: "requirement.check", params: {} }, { quick: true }))),
      el("p", { class: "dim" }, "Starting a project from a plan lists its materials here. What's on hand in the workshop and inventory is marked off; a find that fits a need ranks first."));
    if (!(page.needs || []).length) return [head, el("p", { class: "empty" }, "No projects yet. Start one from a plan in the Library, or on the Projects page.")];
    const status = { needed: "needed", partial: "some on hand", owned: "on hand", found: "found", ordered: "ordered", acquired: "got it" };
    return [head, ...page.needs.map((p) => section(p.name, buttons(btn("Add A Need", "btn-green", () => addNeed(p))),
      el("p", { class: "dim" }, p.progress.lines ? p.progress.open + " still to get · " + p.progress.done + " on hand or got" : "Nothing listed yet."),
      p.lines.length ? el("div", { class: "rows" }, p.lines.map((l) => el("div", { class: "row money-row" },
        el("div", {}, el("div", { class: "row-title" }, l.quantity + " " + (l.unit ? l.unit + " " : "") + l.item,
            chip(status[l.status] || l.status, ["owned", "acquired"].includes(l.status) ? "ok" : "")),
          el("div", { class: "row-sub" }, [l.specs, l.max_price ? "up to " + l.max_price : "", l.condition !== "any" ? l.condition : "",
            l.priority !== "first" ? l.priority : "", l.have && l.status === "partial" ? l.have + " on hand" : "", "from " + l.from].filter(Boolean).join(" · "))),
        ["owned", "acquired"].includes(l.status) ? null : buttons(
          btn("Got It", "btn-ghost btn-small", () => act({ kind: "requirement.got", params: { requirement_id: l.id } }, { quick: true })),
          btn("Not Needed", "btn-ghost btn-small", () => act({ kind: "requirement.remove", params: { requirement_id: l.id } }))))))
        : null))];
  }

  const VIEWS = { finds, needs, watches, sources };

  function draw() {
    $("strip").replaceChildren(
      el("div", { class: "cell " + (page.on ? "ok" : "soon") }, el("span", { class: "n" }, page.on ? "On" : "Off"), el("span", { class: "t" }, "World Intelligence")),
      el("div", { class: "cell ok" }, el("span", { class: "n" }, String(page.counts.new)), el("span", { class: "t" }, "New")),
      el("div", { class: "cell ok" }, el("span", { class: "n" }, String(page.counts.saved)), el("span", { class: "t" }, "Saved")),
      el("div", { class: "cell ok" }, el("span", { class: "n" }, String(page.watches.length)), el("span", { class: "t" }, "Watches")));
    $("tabs").hidden = false;
    $("tabs").replaceChildren(...TABS.map(([id, l]) => el("button", { type: "button", role: "tab", "aria-selected": String(id === tab),
      onclick: () => go(id) }, l)));
    $("panel").replaceChildren(...[].concat(VIEWS[tab]()).filter(Boolean),
      el("p", { class: "dim nt-say" }, "Or say “what have you found?”, “watch for greenhouse panels”, “save that find”, “not for me”."));
  }

  MIAShell.start(async () => {
    page = await MIA.worldIntel();
    if (!page.available) { $("panel").replaceChildren(el("p", { class: "empty" }, "World Intelligence isn't on this MIA.")); return; }
    draw();
  });
})();
