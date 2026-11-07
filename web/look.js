/*
 * look.js — Look: show MIA something (claude, 2026-11-07, build plan step 15).
 * A photo (the camera, or one you have) and a question ("what is this?",
 * "read this label", "inspect this part"), answered on MIA's PC by her local
 * vision model (core/sight.py, POST /api/sight). The photo isn't kept. She
 * never says who a person is. Formatting only; the look is muse's.
 */
(function () {
  "use strict";
  const { el } = MIAShell;
  const $ = (id) => document.getElementById(id);
  const ASKS = ["What is this?", "Read this label", "Inspect this part"];
  let question = ASKS[0];

  // The design canvas (DEC-0113): the photo you picked (shown here only, never kept), the three questions as chips,
  // MIA's answer with how she knows it, then Take a Photo and Choose One.
  let preview = null;
  function answer(got) {
    const [first, ...rest] = String(got.said || "").split(/(?<=[.!?])\s+/);
    return [el("p", { class: "lk-first" }, first), rest.length ? el("p", { class: "lk-rest" }, rest.join(" ")) : null,
      got.how === "refused" ? null : el("span", { class: "kind " + (got.how === "read" ? "ok" : "") },
        got.how === "read" ? "Read from the photo's text" : "Estimate · from MIA's vision model on the PC")].filter(Boolean);
  }
  function pick(capture) {
    const input = el("input", { type: "file", hidden: true, accept: "image/*", capture: capture || null });
    input.addEventListener("change", async () => {
      const file = input.files && input.files[0];
      input.remove();
      if (!file) return;
      if (preview) URL.revokeObjectURL(preview);
      preview = URL.createObjectURL(file);  // in this page only: the photo isn't kept
      paint();
      $("look-answer").hidden = false;
      $("look-answer").replaceChildren(el("p", { class: "dim" }, "Looking…"));
      try {
        const got = await MIA.upload("/api/sight", file, { "X-Question": encodeURIComponent(question) });
        $("look-answer").replaceChildren(...answer(got));
      } catch (e) {
        $("look-answer").replaceChildren(el("p", {}, e.message));
      }
    });
    document.body.append(input);
    input.click();
  }

  function paint() {
    const box = el("input", { type: "text", class: "lk-ask", value: question, "aria-label": "Or ask your own question",
      oninput: (e) => { question = e.target.value || ASKS[0]; } });
    const kept = $("look-answer") ? [...$("look-answer").childNodes] : [];
    $("panel").replaceChildren(
      el("section", { class: "lk-head" }, el("h2", {}, "Show MIA something")),
      el("div", { class: "glass lk-photo", role: "img", "aria-label": preview ? "The photo you picked" : "No photo yet" },
        preview ? el("img", { src: preview, alt: "" }) : el("span", { class: "dim" }, "Take or choose a photo"),
        el("span", { class: "lk-tag" }, "Your Photo · Not Kept")),
      el("div", { class: "lk-chips" }, ASKS.map((a) => el("button", { type: "button", class: "lk-chip", "aria-pressed": String(a === question),
        onclick: () => { question = a; paint(); } }, a))),
      box,
      el("article", { class: "glass lk-answer", id: "look-answer", "aria-label": "MIA's answer", "aria-live": "polite", hidden: !kept.length }, ...kept),
      el("div", { class: "lk-actions" }, el("button", { type: "button", class: "btn btn-big btn-green", onclick: () => pick("environment") }, "Take a Photo"),
        el("button", { type: "button", class: "btn btn-big quiet", onclick: () => pick() }, "Choose One")),
      el("p", { class: "dim lk-note" }, "She looks on your PC and never says who a person is."));
  }

  MIAShell.start(async () => { paint(); });
})();
