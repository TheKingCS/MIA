/*
 * knowledge.js — the offline reference library (claude, 2026-11-06).
 * Renders MIA.knowledge(q) (core/reference_library_manager.py): the installed
 * packs, a search across all of them, and an article read as plain text
 * (MIA.knowledgeArticle), and the plans shelf (MIA.knowledgePlans, core/plan_library.py):
 * plans, blueprints and material lists. Works with no internet. Formatting only; the look
 * is muse's.
 */
(function () {
  "use strict";
  const { el } = MIAShell;
  const $ = (id) => document.getElementById(id);
  let query = "";

  async function read(hit) {
    const a = await MIA.knowledgeArticle(hit.pack_id, hit.path);
    $("panel").replaceChildren(
      el("section", { class: "glass money-section" },
        el("div", { class: "row-buttons" }, el("button", { type: "button", class: "btn btn-ghost btn-small", onclick: () => draw() }, "← Back")),
        el("h2", {}, a.title), el("p", { class: "dim" }, hit.pack_title),
        ...a.text.split(/(?<=[.!?])\s+(?=[A-Z])/).reduce((paras, s, i) => {
          if (i % 4 === 0) paras.push([]);
          paras[paras.length - 1].push(s);
          return paras;
        }, []).map((p) => el("p", {}, p.join(" ")))));
  }

  // The plans shelf: plans, blueprints and material lists (core/plan_library.py).
  async function openPlan(p) {
    if (p.file) {
      const blob = await MIA.download("/api/knowledge/plan/file?id=" + encodeURIComponent(p.id));
      window.open(URL.createObjectURL(blob), "_blank");
      return;
    }
    const d = await MIA.knowledgePlan(p.id);
    const list = (title, rows) => rows.length ? [el("h3", {}, title), el("ul", {}, rows.map((r) => el("li", {}, r)))] : [];
    $("panel").replaceChildren(
      el("section", { class: "glass money-section" },
        el("div", { class: "row-buttons" }, el("button", { type: "button", class: "btn btn-ghost btn-small", onclick: () => draw() }, "← Back")),
        el("h2", {}, d.title), el("p", { class: "dim" }, d.where + (d.summary ? " · " + d.summary : "")),
        ...list(d.materials_title || "Materials", d.items.map((i) => (Number.isInteger(i.qty) ? i.qty : i.qty.toString()) + " " + (i.unit ? i.unit + " " : "") + i.name + (i.note ? " (" + i.note + ")" : ""))),
        ...list("Cuts", d.cuts.map((c) => c.qty + " × " + c.part + " at " + c.length + (c.stock ? " from " + c.stock : ""))),
        ...list("Tools", d.tools),
        ...(d.steps.length ? [el("h3", {}, "Steps"), el("ol", {}, d.steps.map((s) => el("li", {}, s)))] : []),
        ...d.notes.map((n) => el("p", { class: "dim" }, n)),
        el("p", { class: "dim" }, "Ask MIA for another size, or what to buy: \"what would a 10 by 12 one need?\"")));
  }

  function plansSection(shelf) {
    if (!shelf.available) return null;
    return el("section", { class: "glass money-section" }, el("h2", {}, "Plans"),
      el("p", { class: "dim" }, "Woodworking plans, structure blueprints and material lists. Built-in plans work out for any size; save your own PDFs and drawings into " + shelf.folder + "."),
      el("div", { class: "sync-rows" }, shelf.plans.map((p) => el("div", { class: "sync-row" },
        el("div", {}, el("p", { class: "council-text" }, p.title), el("p", { class: "dim" }, p.where + (p.summary ? " · " + p.summary : ""))),
        el("button", { type: "button", class: "btn btn-ghost btn-small", onclick: () => openPlan(p) }, "Open")))),
      shelf.sources.length ? el("details", {}, el("summary", {}, "Where to get more free plans"),
        el("ul", {}, shelf.sources.map((s) => el("li", {}, el("a", { href: s.url, target: "_blank", rel: "noopener" }, s.name), " · " + s.what)))) : null);
  }

  // The design canvas (DEC-0113): Search, Packs and the Plans Shelf as tabs; Search is a big box, "works with no
  // internet", then a card per hit (its pack, title and a snippet), and matching plans with them.
  const TABS = [["search", "Search"], ["packs", "Packs"], ["plans", "Plans Shelf"]];
  let tab = TABS.some(([t]) => t === location.hash.slice(1)) ? location.hash.slice(1) : "search";
  function hitCard(pack, title, snippet, onclick) {
    return el("button", { type: "button", class: "glass kn-hit", onclick },
      el("span", { class: "kn-pack" }, pack), el("span", { class: "kn-title" }, title), snippet ? el("span", { class: "kn-snip" }, snippet) : null);
  }
  async function draw() {
    const [data, shelf] = await Promise.all([MIA.knowledge(query), MIA.knowledgePlans(query).catch(() => ({ available: false }))]);
    $("know-sub").textContent = data.packs.length ? data.packs.length + (data.packs.length === 1 ? " pack" : " packs") + ", offline."
      : "No packs yet.";
    $("tabs").hidden = false;
    $("tabs").replaceChildren(...TABS.map(([id, l]) => el("button", { type: "button", role: "tab", "aria-selected": String(id === tab),
      onclick: () => { tab = id; history.replaceState(null, "", "#" + id); draw(); } }, l)));
    if (tab === "plans") { $("panel").replaceChildren(plansSection(shelf) || el("p", { class: "empty" }, "The plans shelf isn't on this MIA.")); return; }
    if (tab === "packs") {
      $("panel").replaceChildren(el("section", { class: "glass money-section" }, el("h2", {}, "Packs"),
        data.packs.length ? el("ul", {}, data.packs.map((p) => el("li", {}, p.title + " · " + p.articles.toLocaleString() + " articles")))
          : el("p", {}, "Copy .zim files (Wikipedia, iFixit, medical and survival guides from kiwix.org) into " + (data.root || "the library folder") + ".")));
      return;
    }
    const input = el("input", { type: "search", class: "input kn-search", placeholder: "Search the library", value: query, "aria-label": "Search the library" });
    const form = el("form", { class: "kn-form", onsubmit: (e) => { e.preventDefault(); query = input.value.trim(); draw(); } }, input);
    const plans = query && shelf.available ? shelf.plans.slice(0, 3) : [];
    $("panel").replaceChildren(...[
      form,
      el("p", { class: "kn-note" }, data.packs.length ? "Works with no internet · " + data.packs.length + (data.packs.length === 1 ? " pack" : " packs") + " installed"
        : "No packs yet: add some under Packs. Ask MIA too: she looks here first."),
      query ? el("div", { class: "kn-hits" },
        ...data.hits.map((h) => hitCard(h.pack_title, h.title, h.snippet, () => read(h))),
        ...plans.map((p) => hitCard("Plans Shelf", p.title, [p.where, p.summary].filter(Boolean).join(" · "), () => openPlan(p))),
        data.hits.length || plans.length ? null : el("p", { class: "dim" }, "Nothing in the library for that.")) : null,
    ].filter(Boolean));
  }

  MIAShell.start(draw);
})();
