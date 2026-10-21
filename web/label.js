/*
 * label.js — printable labels for a homestead good (DEC-0036). Reads
 * MIA.workshop()'s goods: ?recipe=<id> (today's date) or &job=<batch> (that
 * batch's made date). Formatting only; the words are the person's own.
 */
(function () {
  "use strict";
  const $ = (id) => document.getElementById(id);
  const q = new URLSearchParams(location.search);

  function el(tag, cls, text) {
    const node = document.createElement(tag);
    if (cls) node.className = cls;
    if (text) node.textContent = text;
    return node;
  }
  const day = (iso) => iso ? new Date(iso + "T00:00:00").toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" }) : "";

  function one(l) {
    const box = el("div", "label");
    box.append(el("h2", "", l.name));
    if (l.net) box.append(el("p", "", "Net: " + l.net));
    if (l.ingredients) box.append(el("p", "", "Ingredients: " + l.ingredients));
    if (l.allergens) box.append(el("p", "", l.allergens));
    if (l.made) box.append(el("p", "small", "Made " + day(l.made)));
    if (l.business) box.append(el("p", "small", l.business));
    if (l.address) l.address.split("\n").forEach((line) => box.append(el("p", "small", line)));
    if (l.statement) box.append(el("p", "statement", l.statement));
    return box;
  }

  async function draw() {
    let page;
    try { page = await MIA.workshop(); } catch (e) { $("note").textContent = e.message; return; }
    const good = (page.goods || []).find((g) => g.recipe_id === q.get("recipe"));
    if (!good) { $("note").textContent = "That recipe isn't there anymore."; return; }
    const lot = good.lots.find((l) => l.job_id === q.get("job"));
    if (lot && first) $("count").value = String(Math.max(1, Math.ceil(lot.left)));  // one per jar left
    first = false;
    const l = lot ? lot.label : good.label;
    const notes = [];
    if (l.missing.length) notes.push("Missing: " + l.missing.join(", ") + ". Add them in the recipe (Edit) or Goods → Label Info.");
    if (!l.ordered) notes.push("Check the ingredient order: list them heaviest first (the recipe's “Label: ingredients” sets it).");
    $("note").textContent = notes.join(" ");
    $("note").className = "note" + (notes.length ? " warn" : "");
    const count = Math.max(1, Math.min(200, parseInt($("count").value, 10) || 1));
    $("sheet").replaceChildren(...Array.from({ length: count }, () => one(l)));
    document.title = l.name + " labels — MIA";
  }

  let first = true;
  $("count").addEventListener("change", draw);
  $("print").addEventListener("click", () => window.print());
  draw();
})();
