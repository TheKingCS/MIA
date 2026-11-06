/*
 * knowledge.js — the offline reference library (claude, 2026-11-06).
 * Renders MIA.knowledge(q) (core/reference_library_manager.py): the installed
 * packs, a search across all of them, and an article read as plain text
 * (MIA.knowledgeArticle). Works with no internet. Formatting only; the look
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

  async function draw() {
    const data = await MIA.knowledge(query);
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
      data.packs.length ? el("section", { class: "glass money-section" }, el("h2", {}, "Packs"),
        el("ul", {}, data.packs.map((p) => el("li", {}, p.title + " · " + p.articles.toLocaleString() + " articles")))) : null);
  }

  MIAShell.start(draw);
})();
