/*
 * security.js — Security (claude, 2026-10-18, DEC-0033). Renders
 * MIA.security() (core/security_cams.py) in tabs: Cameras (a live grid:
 * each tile asks MIA for the camera's picture every few seconds while
 * it's on screen; tap one for a full view, refreshed every second, with
 * Save Picture), Pictures (what you saved), and Set Up (add a camera:
 * name, where, brand, its address, its login). The password goes to
 * MIA.saveCamera only, never through an action, and is never shown again.
 * Formatting only.
 */
(function () {
  "use strict";
  const { el, act, form } = MIAShell;
  const $ = (id) => document.getElementById(id);
  const TABS = [["cameras", "Cameras"], ["pictures", "Pictures"], ["setup", "Set Up"]];
  const GRID_MS = 3000, FULL_MS = 1000;
  let page = null, loops = [], full = null;
  const answering = new Map();  // camera id → answering right now (the strip's count)
  // The Cameras cell says the worst camera state: ok while all answer, soon when any doesn't (Muse, H-0059).
  function camerasTone() {
    const down = page.cameras.some((c) => c.problem || answering.get(c.id) === false) || (page.home && page.home.linked && !page.home.reachable);
    return down ? "soon" : "ok";
  }
  function countAnswering() {
    const n = $("answering");
    if (n) n.textContent = String([...answering.values()].filter(Boolean).length);
    const cell = $("cams-cell");
    if (cell) cell.className = "cell " + camerasTone();
  }
  let tab = TABS.some(([t]) => t === location.hash.slice(1)) ? location.hash.slice(1) : "cameras";

  const btn = (label, cls, onclick) => el("button", { type: "button", class: "btn " + cls, onclick }, label);
  const section = (title, actions, ...body) =>
    el("section", { class: "glass money-section" }, el("div", { class: "sect" }, el("h2", {}, title), actions), ...body);
  const when = (iso) => new Date(iso).toLocaleString(undefined, { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" });

  // ------------------------------------------------------------ live pictures
  function stopAll() { loops.forEach((stop) => stop()); loops = []; }
  // Keep one <img> showing the camera's latest picture; the status line says when it's offline.
  function live(cam, img, status, every) {
    let url = null, alive = true, timer = null;
    const tick = async () => {
      if (!alive || !img.isConnected) return;
      if (document.visibilityState === "visible") {
        try {
          const blob = await MIA.download(cam.frame + "?t=" + Date.now());
          const next = URL.createObjectURL(blob);
          img.src = next;
          if (url) URL.revokeObjectURL(url);
          url = next;
          status.textContent = "● Live";
          status.className = "cam-status ok";
          answering.set(cam.id, true);
        } catch (e) {
          status.textContent = e.message || "Offline";
          status.className = "cam-status bad";
          answering.set(cam.id, false);
        }
      }
      countAnswering();
      timer = setTimeout(tick, every);
    };
    timer = setTimeout(tick, 0);  // after the tile is on the page
    const stop = () => { alive = false; clearTimeout(timer); if (url) URL.revokeObjectURL(url); };
    loops.push(stop);
    return stop;
  }

  function camTile(cam) {
    const img = el("img", { alt: cam.name, class: "cam-img" });
    const status = el("span", { class: "cam-status" }, page.demo ? "Demo" : "Connecting…");
    const tile = el("button", { type: "button", class: "glass cam-tile", "aria-label": "Open " + cam.name, onclick: () => openFull(cam) },
      el("div", { class: "cam-frame" }, img, status),
      el("div", { class: "cam-caption" }, el("strong", {}, cam.name),
        el("span", { class: "dim" }, [cam.location !== cam.name ? cam.location : null, cam.on_pc ? "via PC" : null].filter(Boolean).join(" · "))));
    if (!page.demo) live(cam, img, status, GRID_MS);
    return tile;
  }

  function openFull(cam) {
    if (full) full.close();
    const img = el("img", { alt: cam.name, class: "cam-img" });
    const status = el("span", { class: "cam-status" }, "Connecting…");
    const dialog = el("dialog", { class: "confirm form-dialog cam-full", "aria-label": cam.name });
    let stop = null;
    const close = () => { if (stop) stop(); dialog.close(); dialog.remove(); full = null; };
    dialog.append(
      el("div", { class: "sect" }, el("h3", {}, cam.name),
        el("span", { class: "dim" }, [cam.location, cam.on_pc ? "via PC" : null].filter(Boolean).join(" · "))),
      el("div", { class: "cam-frame big" }, img, status),
      el("div", { class: "confirm-actions" },
        btn("Save Picture", "btn-amber", () => act({ kind: "security.save_picture", params: { camera_id: cam.id } })),
        btn("Close", "btn-ghost", close)));
    dialog.oncancel = (e) => { e.preventDefault(); close(); };
    document.body.append(dialog);
    dialog.showModal();
    full = { close };
    if (!page.demo) stop = live(cam, img, status, FULL_MS);
  }

  // ------------------------------------------------------------ set up
  function fields(cam) {
    return [
      { name: "name", label: "Camera name", type: "text", required: true, options: [], default: null },
      { name: "location", label: "Where it is", type: "choice", required: true, options: page.locations, default: "Front Door" },
      { name: "brand", label: "Brand", type: "choice", required: true, options: page.brands.map((b) => b.name), default: page.brands[0].name },
      { name: "host", label: "Its address on your network (like 192.168.1.40)", type: "text", required: true, options: [], default: null },
      { name: "path", label: "Picture or stream path (only for Other)", type: "text", required: false, options: [], default: null },
      { name: "user", label: "Camera username", type: "text", required: false, options: [], default: "admin" },
      { name: "password", label: cam && cam.has_password ? "Camera password (leave empty to keep it)" : "Camera password", type: "password", required: false, options: [], default: null },
    ];
  }
  const ON_PC = "On the home computer's Wi-Fi", HERE = "On this device's Wi-Fi";
  async function editCamera(cam) {
    // Linked to the home computer: a new camera lives there by default, so the phone sees it from anywhere.
    const ask = !cam && page.home && page.home.linked;
    const list = (ask ? [{ name: "where", label: "Where the camera is", type: "choice", required: true, options: [ON_PC, HERE], default: ON_PC }] : [])
      .concat(fields(cam));
    const v = await form(cam ? "Change " + cam.name : "Add A Camera", list,
      cam ? { name: cam.name, location: cam.location, brand: cam.brand, host: cam.host, path: cam.path, user: cam.user } : {});
    if (!v) return;
    const onPc = cam ? !!cam.on_pc : v.where === ON_PC;
    delete v.where;
    const body = Object.assign({}, v, { camera_id: cam ? cam.id : null, on_pc: onPc });
    if (cam && !v.password) body.password = null;
    try {
      MIAShell.say((await MIA.saveCamera(body)).message);
      page = await MIA.security(); draw();
    } catch (e) { MIAShell.say(e.message); }
  }

  // The home computer: cameras on its Wi-Fi come through it, from anywhere (core/home_link.py).
  function homeNote() {
    const h = page.home || {};
    if (h.linked && !h.reachable) return section("Home Computer", null,
      el("p", { class: "dim" }, "⚠ " + (h.problem || "Can't reach the home computer right now.") + " Its cameras show here again as soon as it answers."));
    if (!h.linked && !page.demo) return el("p", { class: "dim cam-hint" },
      "Cameras on your PC's Wi-Fi: link this phone in Settings → Home Computer and you can watch them from anywhere.");
    return null;
  }

  // ------------------------------------------------------------ views
  const VIEWS = {
    cameras: () => [homeNote(), page.cameras.length
      ? section("Cameras", btn("Add Camera", "btn-ghost btn-small", () => editCamera(null)),
          el("div", { class: "cam-grid" }, page.cameras.map(camTile)))
      : section("Cameras", null, el("p", { class: "empty" }, "No cameras yet. MIA shows cameras that stream on your home network: see which ones work in Set Up → Which Cameras Work."),
          el("div", { class: "row-buttons" }, btn("Add A Camera", "btn-amber", () => editCamera(null))))].filter(Boolean),
    pictures: () => section("Saved Pictures", null, page.pictures.length
      ? el("div", { class: "media-grid" }, page.pictures.map((p) => {
          const img = el("img", { alt: p.camera + ", " + when(p.at), loading: "lazy" });
          MIA.image("/api/security/pictures/" + encodeURIComponent(p.name)).then((src) => { if (src) img.src = src; });
          return el("div", { class: "media-tile kind-image" }, img, el("span", { class: "craft-tag" }, p.camera + " · " + when(p.at)),
            el("button", { type: "button", class: "btn btn-ghost btn-small cam-del", "aria-label": "Delete this picture",
              onclick: () => act({ kind: "security.picture_delete", params: { name: p.name } }) }, "✕"));
        }))
      : el("p", { class: "empty" }, "Nothing saved. Open a camera and press Save Picture.")),
    setup: () => [
      section("Your Cameras", btn("Add Camera", "btn-amber btn-small", () => editCamera(null)),
        page.cameras.length ? el("div", { class: "rows" }, page.cameras.map((c) => el("div", { class: "row money-row" },
          el("div", {}, el("div", { class: "row-title" }, c.name),
            el("div", { class: "row-sub" }, [c.location, c.brand, c.host, c.problem ? "⚠ " + c.problem : null,
              c.needs_ffmpeg ? "needs ffmpeg on this device" : null].filter(Boolean).join(" · "))),
          el("div", { class: "row-buttons" }, btn("Change", "btn-ghost btn-small", () => editCamera(c)),
            btn("Remove", "btn-ghost btn-small", () => act({ kind: "camera.remove", params: { camera_id: c.id } }))))))
          : el("p", { class: "empty" }, "No cameras yet.")),
      section("Which Cameras Work", null,
        el("p", { class: "dim" }, "MIA watches cameras over your own network, never through a company's cloud. Cameras that work out of the box:"),
        el("ul", { class: "cam-brands" }, page.brands.map((b) => el("li", {}, el("strong", {}, b.name), " · ", b.help))),
        el("p", { class: "dim" }, "Ring, Nest, Blink and Arlo only stream through their cloud, so MIA can't show them. " +
          (page.ffmpeg ? "This device can read video streams (ffmpeg is installed)." : "Stream-only cameras (Tapo, Wyze) need ffmpeg on the device running MIA: on the PC, winget install ffmpeg."))),
    ],
  };

  function draw() {
    stopAll();
    const c = page.counts;
    $("strip").replaceChildren(
      el("div", { class: "cell " + camerasTone(), id: "cams-cell" }, el("span", { class: "n" }, c.cameras), el("span", { class: "t" }, "Cameras")),
      el("div", { class: "cell ok" }, el("span", { class: "n", id: "answering" },
        page.demo ? page.cameras.length : [...answering.values()].filter(Boolean).length), el("span", { class: "t" }, "Answering")),
      el("div", { class: "cell ok" }, el("span", { class: "n" }, c.pictures), el("span", { class: "t" }, "Saved Pictures")));
    $("tabs").hidden = false;
    $("tabs").replaceChildren(...TABS.map(([id, l]) => el("button", { type: "button", role: "tab", "aria-selected": String(id === tab),
      onclick: () => { tab = id; history.replaceState(null, "", "#" + id); draw(); } }, l)));
    $("panel").replaceChildren(...[].concat(VIEWS[tab]()));
  }

  MIAShell.start(async () => {
    page = await MIA.security();
    if (!page.available) { $("panel").replaceChildren(el("p", { class: "empty" }, "Security isn't set up on this MIA.")); return; }
    page.demo = MIA.demo;
    draw();
  });
})();
