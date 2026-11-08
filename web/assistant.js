/*
 * assistant.js — MIA Assistant (DEC-0018, claude; the canvas's Talk, DEC-0113:
 * her orb and state in the header, What I used under each answer). Typed
 * turns go through MIA.talk; spoken ones are recorded with the shell's
 * recorder (the mono 16-bit WAV MIA's voice path expects) and sent with
 * MIA.voice. Her spoken reply plays when her computer has a voice.
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

  // Her orb and its label in the header follow the turn (DEC-0113: one orb, one set of states).
  function orb(state, label) {
    const o = $("chat-orb");
    if (o) o.dataset.state = state;
    if ($("chat-state")) $("chat-state").textContent = label;
  }

  // What I Used (DEC-0029): the memories this answer was given, shown under it; a page she opened, as a link.
  function usedLine(turn) {
    const used = turn.used || [];
    if (!used.length && !turn.open) return null;
    const line = el("details", { class: "used" },
      el("summary", {}, used.length ? "What I used: " + used.length + (used.length === 1 ? " memory" : " memories") : "Opened"));
    used.forEach((m) => line.append(el("div", {}, el("b", {}, m.category ? m.category + ": " : ""), m.text)));
    if (turn.open) line.append(el("a", { href: turn.open }, "Open it"));
    return line;
  }

  async function send(text) {
    text = (text || "").trim();
    if (!text) return;
    bubble("me", text);
    const reply = bubble("mia thinking", "…");
    orb("thinking", "Thinking");
    try {
      const turn = await MIA.talk(text);
      reply.textContent = turn.reply_text || "Done.";
      const used = usedLine(turn);
      if (used) reply.after(used);
      reply.parentElement.append(MIAShell.notRight(text, turn.reply_text));  // the Fix-It Log (DEC-0049)
      if (turn.comparable) MIAShell.twoWays(turn.reply_text, reply.parentElement, reply.parentElement.parentElement);  // DEC-0138
      MIAShell.refresh();
      orb("idle", "Ready");
    } catch (e) {
      reply.textContent = e.message;
      orb("offline", "Can't Reach MIA");
    }
    reply.parentElement.classList.remove("thinking");
  }

  // ------------------------------------------------------------ voice (the shared recorder, web/shell.js)
  const recorder = MIAShell.voiceRecorder();
  async function toggleMic() {
    if (!recorder.recording) {
      try { await recorder.start(); } catch (e) { note(e.message); return; }
      $("mic").classList.add("listening");
      orb("listening", "Listening");
      note("Listening… tap the mic again when you're done.");
      return;
    }
    $("mic").classList.remove("listening");
    note("");
    const reply = bubble("mia thinking", "…");
    orb("thinking", "Thinking");
    try {
      const turn = await MIA.voice(await recorder.stop());
      if (turn.transcript) reply.parentElement.before(el("div", { class: "chat-bubble me" }, el("p", {}, turn.transcript)));
      reply.textContent = turn.reply_text || "Done.";
      const used = usedLine(turn);
      if (used) reply.after(used);
      orb("idle", "Ready");
      if (turn.audio_wav_base64) {  // her voice, with the orb speaking while it plays
        const audio = new Audio("data:audio/wav;base64," + turn.audio_wav_base64);
        audio.onplay = () => orb("speaking", "Speaking");
        audio.onended = () => orb("idle", "Ready");
        audio.play().catch(() => orb("idle", "Ready"));
      }
      MIAShell.refresh();
    } catch (e) { reply.textContent = e.message; orb("offline", "Can't Reach MIA"); }
    reply.parentElement.classList.remove("thinking");
  }
  function note(text) { $("note").textContent = text; $("note").hidden = !text; }

  // ------------------------------------------------------------ history (the Qt Assistant's History, on the web)
  // Past conversations (MIA.conversations, core/web_conversations.py): newest first; one opens to read, with Pick It
  // Back Up (Talk continues it) and Delete (conversation.delete, undoable). Only what was kept: never private turns.
  const when = (iso) => iso ? new Date(iso).toLocaleString(undefined, { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" }) : "";
  async function showHistory() {
    const box = $("history");
    let list;
    try { list = await MIA.conversations(); } catch (e) { say(e.message); return; }
    box.replaceChildren(
      el("div", { class: "chat-history-head" }, el("p", { class: "pw-label" }, "Past Conversations" + (list.total ? " · " + list.total : "")),
        el("button", { type: "button", class: "btn btn-quiet btn-small", onclick: () => toggleHistory(false) }, "Close")),
      ...(list.conversations.length ? list.conversations.map((c) => el("button", { type: "button", class: "chat-past" + (c.current ? " on" : ""),
        onclick: () => readOne(c.id) },
        el("span", { class: "chat-past-title" }, c.title + (c.current ? " · now" : "")),
        el("span", { class: "dim chat-past-meta" }, when(c.when) + " · " + c.count + " messages" + (c.first ? " · " + c.first : ""))))
        : [el("p", { class: "dim" }, "Nothing kept yet. Conversations show here once you've talked.")]));
  }
  async function readOne(id) {
    const box = $("history");
    let c;
    try { c = await MIA.conversation(id); } catch (e) { say(e.message); return; }
    box.replaceChildren(
      el("div", { class: "chat-history-head" },
        el("button", { type: "button", class: "btn btn-quiet btn-small", onclick: showHistory }, "‹ All"),
        el("p", { class: "pw-label" }, c.title)),
      el("div", { class: "chat-past-log" }, ...c.messages.map((m) => el("div", { class: "chat-bubble " + (m.role === "user" ? "me" : "mia") }, el("p", {}, m.content)))),
      el("div", { class: "row-buttons" },
        el("button", { type: "button", class: "btn btn-small", onclick: async () => {
          try {
            await MIA.continueChat(id);
            $("log").replaceChildren(...c.messages.slice(-12).map((m) => el("div", { class: "chat-bubble " + (m.role === "user" ? "me" : "mia") }, el("p", {}, m.content))));
            toggleHistory(false);
            say("Picked back up: " + c.title);
          } catch (e) { say(e.message); }
        } }, "Pick It Back Up"),
        el("button", { type: "button", class: "btn btn-quiet btn-small", onclick: async () => {
          if (await MIAShell.act({ kind: "conversation.delete", params: { conversation_id: id } })) showHistory();
        } }, "Delete")));
  }
  function toggleHistory(open) {
    const box = $("history");
    box.hidden = !open;
    $("history-btn").setAttribute("aria-expanded", String(open));
    if (open) showHistory();
  }
  $("history-btn").addEventListener("click", () => toggleHistory($("history").hidden));
  $("new-chat").addEventListener("click", async () => {
    try {
      await MIA.newChat();
      $("log").replaceChildren();
      bubble("mia", "New chat. What's on your mind?");
    } catch (e) { say(e.message); }
  });

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
      if (params.get("voice")) toggleMic();  // ?voice=1: start listening (startListening() no longer exists)
      history.replaceState(null, "", location.pathname);
    }
  }, { refreshOnChange: false, talk: false });
})();
