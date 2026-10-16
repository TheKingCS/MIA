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
  const ICON = { image: "🖼", pdf: "📄", audio: "🎵", video: "🎬", text: "📝", file: "📦" };

  const btn = (label, cls, onclick) => el("button", { type: "button", class: "btn " + cls, onclick }, label);
  const buttons = (...list) => el("div", { class: "row-buttons" }, list.filter(Boolean));
  const section = (title, actions, ...body) =>
    el("section", { class: "glass money-section" }, el("div", { class: "sect" }, el("h2", {}, title), actions), ...body);
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

  function draw() {
    $("strip").replaceChildren(
      el("div", { class: "cell ok" }, el("span", { class: "n" }, page.folders.length), el("span", { class: "t" }, "Folders Here")),
      el("div", { class: "cell ok" }, el("span", { class: "n" }, page.files.length), el("span", { class: "t" }, "Files Here")),
      el("div", { class: "cell ok" }, el("span", { class: "n" }, page.used_text), el("span", { class: "t" }, "Used")));
    const crumbs = el("nav", { class: "file-crumbs", "aria-label": "Folder" }, page.crumbs.map((c, i) => [
      i ? el("span", { class: "dim" }, " › ") : null,
      i === page.crumbs.length - 1 ? el("strong", {}, c.name) : el("a", { href: "#", onclick: (ev) => { ev.preventDefault(); go(c.path); } }, c.name)]).flat());
    const rows = [
      ...page.folders.map((d) => el("div", { class: "row money-row file-row" },
        el("button", { type: "button", class: "file-open", onclick: () => go(d.path), "aria-label": "Open folder " + d.name },
          el("span", { class: "file-ico", "aria-hidden": "true" }, "📁"),
          el("span", {}, el("span", { class: "row-title" }, d.name), el("span", { class: "row-sub" }, d.count + (d.count === 1 ? " item" : " items")))),
        buttons(btn("Rename", "btn-ghost btn-small", () => rename(d)), btn("Delete", "btn-ghost btn-small", () => remove(d))))),
      ...page.files.map((f) => el("div", { class: "row money-row file-row" },
        el("button", { type: "button", class: "file-open", onclick: () => open(f), "aria-label": "Open " + f.name },
          el("span", { class: "file-ico", "aria-hidden": "true" }, ICON[f.kind] || ICON.file),
          el("span", {}, el("span", { class: "row-title" }, f.name), el("span", { class: "row-sub" }, f.size_text + " · " + day(f.modified)))),
        buttons(btn("Rename", "btn-ghost btn-small", () => rename(f)), btn("Delete", "btn-ghost btn-small", () => remove(f))))),
    ];
    $("panel").replaceChildren(
      el("div", { class: "journal-actions" }, btn("Upload", "btn-amber", upload), btn("New Folder", "btn-ghost", newFolder)),
      section(page.crumbs[page.crumbs.length - 1].name, null, page.path ? crumbs : null,
        rows.length ? el("div", { class: "rows" }, rows) : el("p", { class: "empty" }, page.path ? "This folder is empty." : "No files yet. Upload photos, receipts, manuals: anything you want to keep with MIA.")),
      el("p", { class: "dim" }, "These are your own files, kept in your MIA folder. Other people on this MIA can't see them."));
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
