/*
 * assistant.js — MIA Assistant (DEC-0018, claude). Typed turns go through
 * MIA.talk; spoken ones are recorded with the shell's recorder (the mono
 * 16-bit WAV MIA's voice path expects) and sent with MIA.voice. Her spoken
 * reply plays when her computer has a voice.
 */
(function () {
  "use strict";
  const { el, say } = MIAShell;
  const $ = (id) => document.getElementById(id);
  const params = new URLSearchParams(location.search);
  const SUGGESTIONS = ["What should I focus on today?", "What's due this week?", "How are my finances?", "What did I get done?"];

  function bubble(who, text) {
    const b = el("div", { class: "chat-bubble " + who }, who === "mia" ? el("span", { class: "chat-who", "aria-hidden": "true" }, el("span", { class: "brand-reactor" })) : null,
      el("p", {}, text));
    $("log").append(b);
    b.scrollIntoView({ block: "end", behavior: "smooth" });
    return b.querySelector("p");
  }

  async function send(text) {
    text = (text || "").trim();
    if (!text) return;
    bubble("me", text);
    const reply = bubble("mia thinking", "…");
    try {
      const turn = await MIA.talk(text);
      reply.textContent = turn.reply_text || "Done.";
      reply.after(MIAShell.notRight(text, turn.reply_text));  // the Fix-It Log (DEC-0049)
      MIAShell.refresh();
    } catch (e) {
      reply.textContent = e.message;
    }
    reply.parentElement.classList.remove("thinking");
  }

  // ------------------------------------------------------------ voice (the shared recorder, web/shell.js)
  const recorder = MIAShell.voiceRecorder();
  async function toggleMic() {
    if (!recorder.recording) {
      try { await recorder.start(); } catch (e) { note(e.message); return; }
      $("mic").classList.add("listening");
      note("Listening… tap the mic again when you're done.");
      return;
    }
    $("mic").classList.remove("listening");
    note("");
    const reply = bubble("mia thinking", "…");
    try {
      const turn = await MIA.voice(await recorder.stop());
      if (turn.transcript) reply.parentElement.before(el("div", { class: "chat-bubble me" }, el("p", {}, turn.transcript)));
      reply.textContent = turn.reply_text || "Done.";
      MIAShell.playReply(turn);
      MIAShell.refresh();
    } catch (e) { reply.textContent = e.message; }
    reply.parentElement.classList.remove("thinking");
  }
  function note(text) { $("note").textContent = text; $("note").hidden = !text; }

  // ------------------------------------------------------------ start
  $("form").addEventListener("submit", (e) => { e.preventDefault(); const t = $("input").value; $("input").value = ""; send(t); });
  if (window.MIAIcons) MIAIcons.badge($("mic"), "mic"); else $("mic").textContent = "🎙";  // the line icon (DEC-0023)
  $("mic").addEventListener("click", toggleMic);
  $("chips").replaceChildren(...SUGGESTIONS.map((s) => el("button", { type: "button", class: "chip-button", onclick: () => send(s) }, s)));

  MIAShell.start(async () => {
    if (!$("log").children.length) {
      bubble("mia", "Hi. What can I help with? Ask me anything, or tell me what you did.");
      if (params.get("ask")) send(params.get("ask"));
      if (params.get("draft")) { $("input").value = params.get("draft"); $("input").focus(); }
      if (params.get("voice")) startListening();
      history.replaceState(null, "", location.pathname);
    }
  }, { refreshOnChange: false, talk: false });
})();
