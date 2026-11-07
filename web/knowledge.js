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

  async function draw() {
    const [data, shelf] = await Promise.all([MIA.knowledge(query), MIA.knowledgePlans(query).catch(() => ({ available: false }))]);
    $("know-sub").textContent = data.packs.length ? data.packs.length + (data.packs.length === 1 ? " pack" : " packs") + ", offline."
      : "No packs yet.";
    const input = el("input", { type: "search", class: "input", placeholder: "Search every pack", value: query });
    const form = el("form", { class: "form-row", onsubmit: (e) => { e.preventDefault(); query = input.value.trim(); draw(); } }, input);
    const results = query ? el("section", { class: "glass money-section" }, el("h2", {}, "Found"),
      data.hits.length ? el("div", { class: "sync-rows" }, data.hits.map((h) => el("button", { type: "button", class: "sync-row council-msg",
        onclick: () => read(h) }, el("p", { class: "council-text" }, h.title), el("p", { class: "dim" }, h.pack_title))))
        : el("p", { class: "dim" }, "Nothing in the packs for that.")) : null;
    $("panel").replaceChildren(
      el("section", { class: "glass money-section" },
        el("p", {}, data.packs.length ? "Encyclopedias and guides kept on this computer, readable with no internet. Ask MIA too: she looks here first."
          : "Copy .zim files (Wikipedia, iFixit, medical and survival guides from kiwix.org) into " + (data.root || "the library folder") + "."),
        data.packs.length ? form : null),
      ...(results ? [results] : []),
      plansSection(shelf),
      data.packs.length ? el("section", { class: "glass money-section" }, el("h2", {}, "Packs"),
        el("ul", {}, data.packs.map((p) => el("li", {}, p.title + " · " + p.articles.toLocaleString() + " articles")))) : null);
  }

  MIAShell.start(draw);
})();
