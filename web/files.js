/*
 * files.js — the Files screen (claude, 2026-10-16; Zac: the app only opened
 * a chat). Renders MIA.files(path) (core/web_more.py, core/my_files.py): your
 * own MIA files folder, with folders, Upload (from this phone or computer),
 * Open (a picture, PDF, song or text shows here; anything else downloads),
 * Rename and Delete. Never the computer's whole disk.
 */
(function () {
  "use strict";
  const { el, act, form, say } = MIAShell;
  const $ = (id) => document.getElementById(id);
  let page = null;
  let here = decodeURIComponent(location.hash.slice(1));

  const btn = (label, cls, onclick) => el("button", { type: "button", class: "btn " + cls, onclick }, label);
  const buttons = (...list) => el("div", { class: "row-buttons" }, list.filter(Boolean));
  const day = (iso) => iso ? new Date(iso + "T00:00:00").toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" }) : "";
  const fileUrl = (path) => "/api/files/file?path=" + encodeURIComponent(path);

  async function go(path) {
    here = path;
    history.replaceState(null, "", path ? "#" + encodeURIComponent(path) : location.pathname);
    page = await MIA.files(here);
    draw();
  }

  async function newFolder() {
    const v = await form("New Folder", [{ name: "name", label: "Name", type: "text", required: true, options: [], default: null }], {});
    if (v) act({ kind: "myfile.folder", params: { path: page.path, name: v.name } });
  }
  async function rename(item) {
    const v = await form("Rename " + item.name, [{ name: "name", label: "New name", type: "text", required: true, options: [], default: item.name }], {});
    if (v) act({ kind: "myfile.rename", params: { path: item.path, name: v.name } });
  }
  const remove = (item) => act({ kind: "myfile.delete", params: { path: item.path } });

  function upload() {
    const input = el("input", { type: "file", multiple: true, hidden: true });
    input.addEventListener("change", async () => {
      for (const file of input.files) {
        try {
          const r = await MIA.upload("/api/files/upload?path=" + encodeURIComponent(page.path), file);
          say(r.message);
        } catch (e) {
          say("Couldn't upload " + file.name + ": " + e.message);
        }
      }
      input.remove();
      go(page.path);
    });
    document.body.append(input);
    input.click();
  }

  async function open(f) {
    let blob;
    try {
      blob = await MIA.download(fileUrl(f.path));
    } catch (e) {
      say("Couldn't open " + f.name + ".");
      return;
    }
    const url = URL.createObjectURL(blob);
    if (!["image", "pdf", "audio", "video", "text"].includes(f.kind)) {
      const a = el("a", { href: url, download: f.name });
      document.body.append(a); a.click(); a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 60000);
      return;
    }
    const dialog = el("dialog", { class: "confirm form-dialog file-view", "aria-label": f.name });
    const close = () => { dialog.close(); dialog.remove(); URL.revokeObjectURL(url); };
    let body;
    if (f.kind === "image") body = el("img", { src: url, alt: f.name });
    else if (f.kind === "audio") body = el("audio", { src: url, controls: true, autoplay: true });
    else if (f.kind === "video") body = el("video", { src: url, controls: true, playsinline: true });
    else if (f.kind === "pdf") body = el("iframe", { src: url, title: f.name });
    else { body = el("pre", { class: "file-text" }); body.textContent = (await blob.text()).slice(0, 200000); }
    dialog.append(el("h3", {}, f.name), el("p", { class: "dim" }, f.size_text + " · " + day(f.modified)), body,
      el("div", { class: "confirm-actions" },
        el("a", { class: "btn btn-ghost", href: url, download: f.name }, "Download"),
        btn("Close", "btn-ghost", close)));
    dialog.oncancel = (ev) => { ev.preventDefault(); close(); };
    document.body.append(dialog);
    dialog.showModal();
  }

  // The design canvas (DEC-0113): the path, Upload, then one list: line icons (folders in cyan), the name and a
  // short meta line, and ⋯ for Rename and Delete. Only this folder, never the whole disk.
  const KIND = { image: "Image", pdf: "PDF", audio: "Audio", video: "Video", text: "Text", file: "File" };
  const SVG = { folder: "M3 6.5A1.5 1.5 0 0 1 4.5 5H10l2 2.5h7.5A1.5 1.5 0 0 1 21 9v9.5a1.5 1.5 0 0 1-1.5 1.5h-15A1.5 1.5 0 0 1 3 18.5Z",
    doc: "M6 3.5h9l3.5 3.5v13.5H6ZM15 3.5V7h3.5" };
  const glyph = (which) => {
    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.setAttribute("viewBox", "0 0 24 24"); svg.setAttribute("aria-hidden", "true"); svg.setAttribute("class", "fl-ico " + which);
    svg.innerHTML = '<path d="' + SVG[which] + '"/>';
    return svg;
  };
  let menu = null;  // the row whose ⋯ is open
  function row(item, isFolder) {
    const key = (isFolder ? "d:" : "f:") + item.path;
    const meta = isFolder ? "Folder · " + item.count + (item.count === 1 ? " item" : " items")
      : [KIND[item.kind] || "File", item.size_text, day(item.modified)].filter(Boolean).join(" · ");
    return el("div", { class: "fl-row" },
      el("button", { type: "button", class: "fl-open", onclick: () => (isFolder ? go(item.path) : open(item)), "aria-label": (isFolder ? "Open folder " : "Open ") + item.name },
        glyph(isFolder ? "folder" : "doc"),
        el("span", { class: "fl-text" }, el("span", { class: "fl-name" }, item.name), el("span", { class: "fl-meta" }, meta))),
      menu === key ? buttons(btn("Rename", "btn-ghost btn-small", () => rename(item)), btn("Delete", "btn-ghost btn-small", () => remove(item)))
        : el("button", { type: "button", class: "fl-more", "aria-label": "More for " + item.name, onclick: () => { menu = key; draw(); } }, "⋯"));
  }
  function draw() {
    $("strip").replaceChildren(
      el("div", { class: "cell ok" }, el("span", { class: "n" }, page.folders.length), el("span", { class: "t" }, "Folders Here")),
      el("div", { class: "cell ok" }, el("span", { class: "n" }, page.files.length), el("span", { class: "t" }, "Files Here")),
      el("div", { class: "cell ok" }, el("span", { class: "n" }, page.used_text), el("span", { class: "t" }, "Used")));
    const crumbs = el("nav", { class: "fl-crumbs", "aria-label": "Folder path" }, page.crumbs.map((c, i) => [
      i ? el("span", { class: "dim" }, "/") : null,
      i === page.crumbs.length - 1 ? el("span", { class: "fl-here" }, c.name) : el("a", { href: "#", onclick: (ev) => { ev.preventDefault(); go(c.path); } }, c.name)]).flat());
    const rows = [...page.folders.map((d) => row(d, true)), ...page.files.map((f) => row(f, false))];
    $("panel").replaceChildren(
      crumbs,
      el("div", { class: "journal-actions fl-actions" }, btn("Upload", "btn-green", upload), btn("New Folder", "btn-ghost", newFolder)),
      rows.length ? el("div", { class: "glass fl-list" }, rows)
        : el("p", { class: "empty" }, page.path ? "This folder is empty." : "No files yet. Upload photos, receipts, manuals: anything you want to keep with MIA."),
      el("p", { class: "dim fl-note" }, "Only this folder. Never the computer's whole disk. Your own files: other people on this MIA can't see them."));
  }

  MIAShell.start(async () => {
    page = await MIA.files(here);
    if (!page.available) {
      $("panel").replaceChildren(el("p", { class: "empty" }, "Files aren't set up on this MIA."));
      return;
    }
    here = page.path;
    draw();
  });
})();
