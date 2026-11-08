/*
 * connect.js — Connect Apps (claude, 2026-11-08). Renders MIA.connect() (core/connectors.py): each source MIA can
 * import from. A file (calendar, contacts, bank statement) or a rental's calendar link is previewed first
 * (MIA.connectPreview: what's new, what's already here, what couldn't be read), and only Import changes anything,
 * through the actions connect.file and connect.rental_calendar: confirmed, then undoable. Formatting only.
 */
(function () {
  "use strict";
  const { el, say } = MIAShell;
  const $ = (id) => document.getElementById(id);

  // A preview: the sentence, the first rows it would add, and the Import button that runs the action.
  function shown(box, preview, action) {
    box.replaceChildren(
      el("p", { class: "cn-sentence" }, preview.sentence),
      preview.adds.length ? el("ul", { class: "cn-rows" }, preview.adds.slice(0, 12).map((r) => el("li", {}, r)),
        preview.count > 12 ? el("li", { class: "dim" }, "…and " + (preview.count - 12) + " more") : null) : null,
      preview.unreadable.length ? el("p", { class: "dim" }, "Couldn't read: " + preview.unreadable.slice(0, 5).join(", ")) : null,
      preview.count ? el("button", { type: "button", class: "btn btn-green", onclick: async () => {
        if (await MIAShell.act(action)) box.replaceChildren(el("p", { class: "dim" }, "Imported. Undo it from the message, or say \"undo that\"."));
      } }, "Import " + preview.count) : null);
  }

  function fileSource() {
    const box = el("div", { class: "cn-preview", "aria-live": "polite" });
    const input = el("input", { type: "file", accept: ".ics,.vcf,.csv,text/calendar,text/vcard,text/csv", "aria-label": "Choose a file to import",
      onchange: async () => {
        const file = input.files && input.files[0];
        if (!file) return;
        if (file.size > 2 * 1024 * 1024) { say("That file is too large to import."); return; }
        const text = await file.text();
        box.replaceChildren(el("p", { class: "dim" }, "Reading " + file.name + "…"));
        try { shown(box, await MIA.connectPreview({ source: "file", name: file.name, text }), { kind: "connect.file", params: { name: file.name, text } }); }
        catch (e) { box.replaceChildren(el("p", {}, e.message)); }
      } });
    return [el("label", { class: "btn btn-ghost cn-pick" }, "Choose a File", input), box];
  }

  function rentalSource(properties) {
    const box = el("div", { class: "cn-preview", "aria-live": "polite" });
    const place = el("input", { type: "text", list: "cn-places", placeholder: "Which property", "aria-label": "Which property" });
    const list = el("datalist", { id: "cn-places" }, properties.map((p) => el("option", { value: p })));
    const url = el("input", { type: "url", inputmode: "url", placeholder: "https://… or webcal://… (.ics)", "aria-label": "The listing's calendar link" });
    const look = async () => {
      const params = { url: url.value.trim(), property: place.value.trim() };
      if (!params.url || !params.property) { say("Paste the calendar link and say which property it's for."); return; }
      box.replaceChildren(el("p", { class: "dim" }, "Reading the calendar…"));
      try { shown(box, await MIA.connectPreview({ source: "rental_calendar", ...params }), { kind: "connect.rental_calendar", params }); }
      catch (e) { box.replaceChildren(el("p", {}, e.message)); }
    };
    return [el("div", { class: "cn-fields" }, place, list, url),
      el("p", { class: "dim" }, "Only the booked dates come in. The guest's details stay out, and the link isn't kept."),
      el("button", { type: "button", class: "btn btn-ghost", onclick: look }, "Preview"), box];
  }

  function draw(page) {
    const body = { file: fileSource, rental_calendar: () => rentalSource(page.properties || []) };
    $("panel").replaceChildren(
      ...page.connectors.map((c) => el("section", { class: "glass money-section cn-source", "aria-label": c.name },
        el("h2", {}, c.name),
        el("p", {}, c.how + ". Lands in " + c.lands + "."),
        c.examples.length ? el("p", { class: "dim" }, "From " + c.examples.join(", ") + ".") : null,
        ...(body[c.id] ? body[c.id]() : []))),
      el("section", { class: "glass money-section" }, el("h2", {}, "Coming Next"),
        el("ul", {}, (page.coming || []).map((c) => el("li", {}, c)))));
  }

  MIAShell.start(async () => draw(await MIA.connect()));
})();
