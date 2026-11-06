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

  const button = (label, onclick, cls) => el("button", { type: "button", class: "btn " + (cls || "btn-ghost"), onclick }, label);

  function pick(capture) {
    const input = el("input", { type: "file", hidden: true, accept: "image/*", capture: capture || null });
    input.addEventListener("change", async () => {
      const file = input.files && input.files[0];
      input.remove();
      if (!file) return;
      $("look-answer").replaceChildren(el("p", { class: "dim" }, "Looking…"));
      try {
        const got = await MIA.upload("/api/sight", file, { "X-Question": encodeURIComponent(question) });
        $("look-answer").replaceChildren(el("p", { class: "council-text" }, got.said),
          el("p", { class: "dim" }, got.how === "read" ? "Read from the photo's text." : got.how === "refused" ? "" :
            "A judgment from the picture: check it if it matters."));
      } catch (e) {
        $("look-answer").replaceChildren(el("p", {}, e.message));
      }
    });
    document.body.append(input);
    input.click();
  }

  function paint() {
    const box = el("input", { type: "text", class: "sync-box", value: question, "aria-label": "Your question",
      oninput: (e) => { question = e.target.value || ASKS[0]; } });
    $("panel").replaceChildren(
      el("section", { class: "glass money-section" },
        el("p", {}, "Show MIA something and ask about it. She looks on your PC; the photo isn't kept, and she never says who a person is."),
        el("div", { class: "row-buttons" }, ASKS.map((a) => button(a, () => { question = a; box.value = a; }, "btn-small"))),
        box,
        el("div", { class: "row-buttons" }, button("Take a photo", () => pick("environment"), "btn-amber"), button("Choose a photo", () => pick()))),
      el("section", { class: "glass money-section", id: "look-answer" }));
  }

  MIAShell.start(async () => { paint(); });
})();
