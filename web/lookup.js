/*
 * lookup.js — Look It Up Online (claude, 2026-11-08, DEC-0053 / T-0017).
 * Renders MIA.lookup() (core/web_lookup.screen): whether a lookup is allowed now and the rules; Search runs
 * MIA.lookupSearch(words) (core/web_lookup.look): what was actually sent (the scrubbed words), then each result with
 * its site, date and a link, marked as from the web. Nothing is kept. Formatting only.
 */
(function () {
  "use strict";
  const { el } = MIAShell;
  const $ = (id) => document.getElementById(id);
  let page = null, found = null, busy = false, words = "";

  async function go() {
    const box = $("lk-words");
    words = box ? box.value.trim() : "";
    if (!words || busy) return;
    busy = true; found = null; paint();
    try { found = await MIA.lookupSearch(words); } catch (e) { found = { problem: e.message }; }
    busy = false; paint();
  }

  function results() {
    if (busy) return el("p", { class: "dim", role: "status" }, "Searching…");
    if (!found) return null;
    if (found.problem) return el("p", { class: "lk-problem", role: "status" }, found.problem);
    const day = String(found.at || "").slice(0, 10);
    return el("section", { class: "lk-results", "aria-live": "polite" },
      el("p", { class: "dim lk-sent" }, "Sent: “" + found.query + "”" + (found.query !== words ? " (the private parts taken out)" : "") + " · " + day),
      found.results.length ? el("ol", { class: "lk-list" }, ...found.results.map((r) => el("li", { class: "glass lk-item" },
        el("a", { class: "lk-title", href: r.url, target: "_blank", rel: "noopener noreferrer" }, r.title || r.url),
        el("p", { class: "dim lk-src" }, r.source + (r.published ? " · published " + r.published : "")),
        r.snippet ? el("p", { class: "lk-snip" }, r.snippet) : null)))
        : el("p", { class: "dim" }, "Nothing useful came back."),
      el("p", { class: "dim lk-note" }, "From the web, not from your records; check anything that matters at its source. Never a legal or tax ruling."));
  }

  function paint() {
    if (!page) return;
    $("lk-sub").textContent = "Search the web through your own search engine, when her records and offline packs don't have it.";
    const off = !page.allowed;
    $("panel").replaceChildren(...[
      el("section", { class: "glass lk-box" },
        el("div", { class: "lk-row" },
          el("input", { id: "lk-words", type: "search", maxlength: "300", value: words, placeholder: "When to plant garlic in zone 6",
            "aria-label": "What to look up", disabled: off || busy ? "" : null, onkeydown: (e) => { if (e.key === "Enter") go(); } }),
          el("button", { type: "button", class: "btn btn-primary", onclick: go, disabled: off || busy ? "" : null }, "Search")),
        off ? el("p", { class: "lk-problem" }, page.why) : null,
        el("p", { class: "dim lk-rules" }, page.rules)),
      results(),
    ].filter(Boolean));
  }

  MIAShell.start(async () => { page = await MIA.lookup(); paint(); });
})();
