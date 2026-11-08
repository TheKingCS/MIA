/*
 * trails.js — Trail Maps (claude, 2026-11-08; the Qt Maps module's Trail Maps tab on the web).
 * Renders MIA.trailMaps() (core/web_trails.py): the park and trail map PDFs on this
 * MIA by state. Open fetches the PDF with this tab's sign-in and shows it in the
 * browser's own viewer. Add a PDF sends one from this device; From a Link has MIA
 * download it (the engine refuses anything that isn't a PDF). Take Out is the
 * action trail_map.delete (its PDF is set aside, so Undo brings it back).
 */
(function () {
  "use strict";
  const { el, form } = MIAShell;
  const $ = (id) => document.getElementById(id);
  const button = (label, onclick, cls) => el("button", { type: "button", class: "btn " + (cls || "btn-ghost") + " btn-small", onclick }, label);
  const day = (iso) => iso ? new Date(iso + "T00:00:00").toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" }) : "";
  const WHERE = [{ name: "park", label: "Park", type: "text", required: true }, { name: "state", label: "State", type: "text", required: true },
    { name: "notes", label: "Notes", type: "textarea" }];

  async function openMap(m) {
    try {
      const blob = await MIA.download("/api/trail-maps/" + encodeURIComponent(m.id) + "/file");
      const url = URL.createObjectURL(new Blob([blob], { type: "application/pdf" }));
      if (!window.open(url, "_blank")) location.href = url;  // the phone's web view opens it in place
    } catch (e) { MIAShell.say(e.message); }
  }

  async function addFile(input) {
    const file = input.files && input.files[0];
    input.value = "";
    if (!file) return;
    const v = await form("Add " + file.name, WHERE, { park: file.name.replace(/\.pdf$/i, "").replace(/[-_]+/g, " ") });
    if (!v) return;
    try {
      const q = "?park=" + encodeURIComponent(v.park) + "&state=" + encodeURIComponent(v.state) + "&notes=" + encodeURIComponent(v.notes || "");
      const done = await MIA.upload("/api/trail-maps/upload" + q, file, { "X-Filename": encodeURIComponent(file.name) });
      MIAShell.say(done.message);
      MIAShell.refresh();
    } catch (e) { MIAShell.say(e.message); }
  }

  async function addLink() {
    const v = await form("A Trail Map From a Link", WHERE.slice(0, 2).concat([{ name: "url", label: "Link to the PDF", type: "text", required: true }],
      WHERE.slice(2)), {});
    if (!v) return;
    MIAShell.say("Downloading…");
    try {
      const done = await MIA.trailMapFetch(v.park, v.state, v.url, v.notes);
      MIAShell.say(done.message);
      MIAShell.refresh();
    } catch (e) { MIAShell.say(e.message); }
  }

  function row(m) {
    return el("div", { class: "glass tm-row" + (m.here ? "" : " gone") },
      el("div", { class: "tm-ico", "aria-hidden": "true" }, "PDF"),
      el("div", { class: "tm-main" },
        el("p", { class: "tm-park" }, m.park),
        el("p", { class: "dim tm-meta" }, [m.here ? m.size_kb.toLocaleString() + " KB" : "The PDF is missing", m.from_link ? "from a link" : "from a file",
          m.added ? "added " + day(m.added) : ""].filter(Boolean).join(" · ")),
        m.notes ? el("p", { class: "tm-notes" }, m.notes) : null),
      el("div", { class: "row-buttons" },
        m.here ? button("Open", () => openMap(m)) : null,
        button("Take Out", () => MIAShell.act({ kind: "trail_map.delete", params: { trail_map_id: m.id } }), "btn-quiet")));
  }

  function paint(data) {
    if (!data.available) { $("tm-sub").textContent = "Trail maps aren't set up on this MIA."; $("panel").replaceChildren(); return; }
    $("tm-sub").textContent = data.count
      ? "Official park and trail maps, kept here so they open without signal."
      : "None yet. Add the PDF from a park's own site before you go: it opens here with no signal.";
    const file = el("input", { type: "file", accept: "application/pdf,.pdf", hidden: true, onchange: (e) => addFile(e.target) });
    $("panel").replaceChildren(...[
      el("div", { class: "tm-actions" },
        el("button", { type: "button", class: "btn btn-green", onclick: () => file.click() }, "Add a PDF"), file,
        el("button", { type: "button", class: "btn btn-ghost", onclick: addLink }, "From a Link"),
        el("a", { class: "btn btn-quiet", href: "maps.html" }, "The Map")),
      ...data.states.map((g) => el("section", { class: "tm-group" },
        el("p", { class: "pw-label" }, g.state + " · " + g.maps.length),
        ...g.maps.map(row))),
      el("p", { class: "dim tm-say" }, "Say \"what trail maps do I have?\", \"add the trail map for Mammoth Cave from <link>\" or " +
        "\"delete my trail map for Mammoth Cave\" any time."),
    ]);
  }

  MIAShell.start(async () => { paint(await MIA.trailMaps()); }, { refreshOnChange: true });
})();
