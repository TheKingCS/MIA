/*
 * yourdata.js — Your Data (claude, 2026-11-08; docs/SECURITY.md step 8). Renders MIA.yourData() (core/your_data.py):
 * the person's own files and their household's shared ones, each with what it is, how many records, its size and
 * whether it's sealed on disk (DEC-0126); her latest answers with the tools she used and how many memories went in;
 * then Export (password, optionally with the household's files: a .zip download) and Delete Account (password, a
 * confirm, optionally erased for good). Formatting only.
 */
(function () {
  "use strict";
  const { el, say } = MIAShell;
  const $ = (id) => document.getElementById(id);

  const when = (iso) => new Date(iso).toLocaleString(undefined, { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" });
  const size = (n) => n >= 1048576 ? (n / 1048576).toFixed(1) + " MB" : n >= 1024 ? Math.round(n / 1024) + " KB" : n + " bytes";
  const PASSWORD = { name: "password", label: "Your password", type: "password", required: true, options: [], default: null };

  function files(title, list, empty) {
    return el("section", { class: "glass money-section", "aria-label": title },
      el("h2", {}, title),
      list.length ? el("div", { class: "rows" }, list.map((f) => el("div", { class: "row" },
        el("div", {}, el("div", { class: "row-title" }, f.what),
          el("div", { class: "row-sub" }, [f.records === null || f.records === undefined ? null : f.records + (f.records === 1 ? " record" : " records"),
            size(f.bytes), f.sealed ? "sealed" : null, f.file].filter(Boolean).join(" · "))))))
        : el("p", { class: "empty" }, empty));
  }

  async function exportAll() {
    const v = await MIAShell.form("Export Your Data", [PASSWORD,
      { name: "household", label: "Your household's shared files", type: "choice", required: true, options: ["Only mine", "Mine and the household's"], default: "Only mine" }], {});
    if (!v) return;
    try {
      const blob = await MIA.exportData(v.password, v.household !== "Only mine");
      const url = URL.createObjectURL(blob);
      const link = el("a", { href: url, download: "MIA-data.zip" });
      document.body.append(link);
      link.click();
      link.remove();
      setTimeout(() => URL.revokeObjectURL(url), 60000);
      say("Your data is downloading as MIA-data.zip.");
    } catch (e) { say(e.message); }
  }

  async function deleteAll() {
    if (!(await MIAShell.confirm("Delete your account? You'll be signed out everywhere. Unless you also choose to erase it, your folder is kept aside on this computer and can be brought back."))) return;
    const v = await MIAShell.form("Delete Your Account", [PASSWORD,
      { name: "erase", label: "Your data", type: "choice", required: true, options: ["Keep it aside on this computer", "Erase it for good"], default: "Keep it aside on this computer" }], {});
    if (!v) return;
    try { await MIA.deleteAccount(v.password, v.erase === "Erase it for good"); location.href = "index.html"; }
    catch (e) { say(e.message); }
  }

  function draw(page) {
    $("panel").replaceChildren(
      el("section", { class: "glass money-section" },
        el("p", {}, page.sealing ? "Your most private files are sealed on disk: only your Windows account on this computer opens them."
          : "Your files aren't sealed on this device."),
        el("p", { class: "dim" }, "Nothing here leaves your devices unless you export it."),
        el("div", { class: "acct-actions" },
          el("button", { type: "button", class: "btn btn-green", onclick: exportAll }, "Export Everything"),
          el("button", { type: "button", class: "btn btn-ghost", onclick: deleteAll }, "Delete My Account"))),
      files("Yours", page.mine || [], "Nothing kept yet."),
      files("Shared with Your Household", page.home || [], "Nothing shared."),
      el("section", { class: "glass money-section", "aria-label": "What she read to answer you" },
        el("h2", {}, "What She Read to Answer You"),
        el("p", { class: "dim" }, "Your latest questions, the tools she used and how many of your memories went in. Private and off-the-record talks are never kept here."),
        (page.answers || []).length ? el("div", { class: "rows" }, page.answers.map((a) => el("div", { class: "row" },
          el("div", {}, el("div", { class: "row-title" }, a.asked || "(no words)"),
            el("div", { class: "row-sub" }, [when(a.at), a.tools.length ? "used " + a.tools.join(", ") : "no tools",
              a.memories ? a.memories + (a.memories === 1 ? " memory" : " memories") : null].filter(Boolean).join(" · "))))))
          : el("p", { class: "empty" }, "No answers yet.")));
  }

  MIAShell.start(async () => draw(await MIA.yourData()));
})();
