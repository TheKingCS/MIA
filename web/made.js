/*
 * made.js: every screen MIA makes (claude, 2026-11-04, DEC-0088 to DEC-0091).
 * Draws a creation's blocks as core assembled them (core/creation_spec.py):
 * stats, chart, table, list, cards, meter, timeline, form, note. Only MIA's
 * own classes and tokens, no styling of its own, so whatever she makes
 * looks like the rest of her. All the working out happens in core;
 * changes go through actions (records.add, creation.publish...).
 */
(function () {
  "use strict";
  const { el } = MIAShell;
  const $ = (id) => document.getElementById(id);
  const id = new URLSearchParams(location.search).get("id");
  const SVG = "http://www.w3.org/2000/svg";
  const svg = (tag, attrs) => {
    const node = document.createElementNS(SVG, tag);
    for (const [k, v] of Object.entries(attrs || {})) node.setAttribute(k, v);
    return node;
  };
  const section = (title, ...body) => el("section", { class: "glass made-block" },
    title ? el("div", { class: "sect" }, el("h2", {}, title)) : "", ...body);

  // Bars as plain boxes (they size with the screen, labels stay readable), a line as a stretched
  // SVG stroke; the words are always beside it, for anyone not looking at the drawing.
  function chart(b) {
    const pts = b.points;
    if (!pts.length) return el("p", { class: "empty" }, "No records yet.");
    const top = Math.max(...pts.map((p) => p.value), 1);
    let drawing;
    if (b.type === "bar") {
      drawing = el("div", { class: "made-bars", role: "img", "aria-label": b.text }, pts.map((p) =>
        el("div", { class: "made-bar-col" },
          el("span", { class: "made-bar-n" }, p.text),
          el("div", { class: "made-bar-track" },
            el("div", { class: "made-bar", style: "height:" + Math.max(2, Math.round((p.value / top) * 100)) + "%" })),
          el("span", { class: "made-bar-lbl", title: p.label }, p.label))));
    } else {
      // A line spans its own range (readings of 119 to 131 shouldn't look flat against zero).
      const n = Math.max(pts.length - 1, 1);
      const lo = Math.min(...pts.map((p) => p.value)), span = Math.max(...pts.map((p) => p.value)) - lo || 1;
      const line = svg("svg", { viewBox: "0 0 100 100", preserveAspectRatio: "none", class: "made-line" });
      line.append(svg("polyline", { "vector-effect": "non-scaling-stroke",
        points: pts.map((p, i) => `${(i / n) * 100},${92 - ((p.value - lo) / span) * 84}`).join(" ") }));
      drawing = el("div", { role: "img", "aria-label": b.text }, line, el("div", { class: "made-line-ends dim" },
        el("span", {}, pts[0].label), el("span", {}, pts[pts.length - 1].label)));
    }
    return el("div", {}, drawing, el("p", { class: "dim made-chart-text" }, b.text));
  }

  function block(b, page) {
    const live = page.status === "published" && !page.pending;
    switch (b.block) {
      case "stats":
        return el("section", { class: "strip made-strip", "aria-label": b.title || "Numbers" },
          b.items.map((s) => el("div", { class: "cell ok" }, el("span", { class: "n" }, s.value), el("span", { class: "t" }, s.label))));
      case "chart":
        return section(b.title, chart(b));
      case "table":
        return section(b.title, b.rows.length ? el("div", { class: "made-table-wrap" }, el("table", { class: "made-table" },
          el("thead", {}, el("tr", {}, b.columns.map((c) => el("th", { scope: "col" }, c)), live ? el("th", {}) : "")),
          el("tbody", {}, b.rows.map((r) => el("tr", {}, r.cells.map((c) => el("td", {}, c)),
            live ? el("td", {}, remove(page, r.id)) : ""))))) : el("p", { class: "empty" }, "No records yet."));
      case "list":
      case "cards":
        return section(b.title, b.items.length ? el("ul", { class: b.block === "cards" ? "made-cards" : "dg-runs" },
          b.items.map((r) => el("li", { class: b.block === "cards" ? "glass" : "dg-run" },
            el("div", { class: "row-title" }, r.title),
            el("div", { class: "row-sub dim" }, r.details.map((d) => d.label + ": " + d.text).join(" · ")),
            live ? remove(page, r.id) : ""))) : el("p", { class: "empty" }, "No records yet."));
      case "timeline":
        return section(b.title, b.items.length ? el("ul", { class: "made-time" },
          b.items.map((r) => el("li", {}, el("span", { class: "dim" }, r.date), el("span", {}, r.title)))) :
          el("p", { class: "empty" }, "No records yet."));
      case "meter":
        return section(b.title, el("div", { class: "made-meter", role: "meter", "aria-valuenow": String(b.share * 100),
          "aria-valuemin": "0", "aria-valuemax": "100", "aria-label": b.text },
          el("div", { class: "fill", style: "width:" + Math.round(b.share * 100) + "%" })), el("p", { class: "dim" }, b.text));
      case "form":
        return section(b.title || "Add one", live
          ? el("button", { class: "btn btn-green", type: "button", onclick: () => add(page, b.fields) }, "Add")
          : el("p", { class: "dim" }, page.status === "draft" ? "Publish it first, then add records here." :
            "Adding goes to the published version."));
      case "note":
        return el("p", { class: "made-note" }, b.text);
      default:
        return "";
    }
  }

  function remove(page, recordId) {
    return el("button", { class: "btn btn-ghost made-x", type: "button", "aria-label": "Remove this record",
      onclick: () => MIAShell.act({ kind: "records.remove", params: { creation_id: page.id, record_id: recordId } }) }, "×");
  }

  async function add(page, fields) {
    const values = await MIAShell.form("Add to " + page.screen.title, fields.map((f) => ({ ...f, options: f.options })));
    if (!values) return;
    if (Object.prototype.hasOwnProperty.call(values, "")) delete values[""];
    await MIAShell.act({ kind: "records.add", params: { creation_id: page.id, values } }, { quick: true });
  }

  function banner(page) {
    const act = (kind, label, cls) => el("button", { class: "btn " + cls, type: "button",
      onclick: () => MIAShell.act({ kind, params: { creation_id: page.id } }) }, label);
    const bits = [];
    if (page.status === "draft") bits.push(el("p", {}, el("strong", {}, "A draft MIA made. "),
      "Only you can see it, and nothing's been changed yet. Publishing adds it to your apps and starts its records " +
      (page.owner === "household" ? "with the household." : "in your own folder.")), act("creation.publish", "Publish", "btn-green"));
    else if (page.pending) bits.push(el("p", {}, el("strong", {}, "Version " + page.latest + " is waiting. "),
      "You're seeing it; your apps still show version " + page.version + "."), act("creation.publish", "Publish it", "btn-green"));
    if (page.rollback && !page.pending) bits.push(act("creation.rollback", "Go back a version", "btn-ghost"));
    if (page.status === "published") bits.push(act("creation.retire", "Remove from my apps", "btn-ghost"));
    bits.push(el("p", { class: "dim made-why" }, "Made from what you said: “" + page.why + "” · " + page.blueprint +
      (page.status === "published" ? " · version " + page.version : "")));
    return el("section", { class: "glass made-banner" + (page.status === "draft" || page.pending ? " glow" : "") }, bits);
  }

  async function drawOne() {
    const page = await MIA.made(id);
    $("hero-name").textContent = page.screen.title;
    $("hero-tagline").textContent = page.screen.about || page.screen.records + " record" + (page.screen.records === 1 ? "" : "s");
    if (window.MIAIcons) MIAIcons.badge(document.querySelector(".hero h1 > span"), page.screen.icon);
    document.title = page.screen.title + " — MIA";
    $("panel").replaceChildren(banner(page), ...page.screen.blocks.map((b) => block(b, page)));
  }

  async function drawList() {
    const { creations } = await MIA.madeList();
    const ask = el("textarea", { class: "made-ask", rows: "3", placeholder: "What do you want to keep track of? Say what matters about each one.",
      "aria-label": "What do you want to keep track of?" });
    const note = el("p", { class: "dim" });
    const go = el("button", { class: "btn btn-green", type: "button", onclick: async () => {
      if (!ask.value.trim()) return;
      go.disabled = true; note.textContent = "MIA is designing it…";
      try { const made = await MIA.make(ask.value.trim()); location.href = "made.html?id=" + made.id; }
      catch (e) { note.textContent = e.message; go.disabled = false; }
    } }, "Make it");
    $("panel").replaceChildren(
      section("Ask for a new one", el("p", {}, "Describe something you keep track of, and MIA designs a screen for it from her own parts. " +
        "You'll see a draft first; nothing changes until you publish it."), ask, el("div", { class: "made-row" }, go), note),
      section("What she's made", creations.length ? el("ul", { class: "dg-runs" }, creations.map((c) =>
        el("li", { class: "dg-run" }, el("a", { href: "made.html?id=" + c.id },
          el("div", { class: "row-title" }, c.title),
          el("div", { class: "row-sub dim" }, [c.status, c.owner === "household" ? "the household's" : "yours",
            "version " + (c.version || c.versions)].join(" · ")))))) : el("p", { class: "empty" }, "Nothing yet.")));
  }

  MIAShell.start(() => (id ? drawOne() : drawList()).catch((e) => $("panel").replaceChildren(el("p", { class: "empty" }, e.message))));
})();
