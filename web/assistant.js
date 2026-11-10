/*
 * assistant.js — MIA Assistant (DEC-0018, claude; the canvas's Talk, DEC-0113:
 * her orb and state in the header, What I used under each answer). Typed
 * turns go through MIA.talk; spoken ones are recorded with the shell's
 * recorder (the mono 16-bit WAV MIA's voice path expects) and sent with
 * MIA.voice. Her spoken reply plays when her computer has a voice.
 * Every answer of hers has Copy; Summary and Export take the whole
 * conversation out of the chat (core/conversation_export.py).
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

  // Under each answer of hers: Copy (the whole message, as she wrote it) and, for an answer to something asked,
  // 👍/👎 (the Fix-It Log, DEC-0049).
  function tools(reply, asked) {
    const row = el("div", { class: "chat-tools" }, MIAShell.copyButton(() => reply.textContent));
    if (asked != null) row.append(MIAShell.notRight(asked, reply.textContent));
    reply.parentElement.append(row);
  }
  const past = (m) => {
    const b = el("div", { class: "chat-bubble " + (m.role === "user" ? "me" : "mia"), title: when(m.at) }, el("p", {}, m.content));
    if (m.role !== "user") b.append(el("div", { class: "chat-tools" }, MIAShell.copyButton(m.content)));
    return b;
  };

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
      tools(reply, text);
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
      tools(reply, turn.transcript || "");
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
  function when(iso) { return iso ? new Date(iso).toLocaleString(undefined, { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" }) : ""; }
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
      el("div", { class: "chat-past-log" }, ...c.messages.map(past)),
      el("div", { class: "row-buttons" },
        el("button", { type: "button", class: "btn btn-small", onclick: async () => {
          try {
            await MIA.continueChat(id);
            $("log").replaceChildren(...c.messages.slice(-12).map(past));
            toggleHistory(false);
            say("Picked back up: " + c.title);
          } catch (e) { say(e.message); }
        } }, "Pick It Back Up"),
        el("button", { type: "button", class: "btn btn-ghost btn-small", onclick: () => showSummary(id, c.title) }, "Summary"),
        el("button", { type: "button", class: "btn btn-ghost btn-small", onclick: () => showExport(id, c.title) }, "Export"),
        el("button", { type: "button", class: "btn btn-quiet btn-small", onclick: async () => {
          if (await MIAShell.act({ kind: "conversation.delete", params: { conversation_id: id } })) showHistory();
        } }, "Delete")));
  }
  function toggleHistory(open) {
    const box = $("history");
    box.hidden = !open;
    if (open) $("panel").hidden = true;
    $("history-btn").setAttribute("aria-expanded", String(open));
    if (open) showHistory();
  }
  $("history-btn").addEventListener("click", () => toggleHistory($("history").hidden));

  // ------------------------------------------------------------ summary and export (core/conversation_export.py)
  // Either one is of the conversation Talk is in (id "current") or of a past one opened in History. The summary
  // is the model's reading of the whole conversation, with a first line counted in code; the export is the
  // record itself, as Markdown or JSON, to copy or to save in Files (conversation.export).
  function panel(title, ...body) {
    toggleHistory(false);
    const box = $("panel");
    box.hidden = false;
    box.replaceChildren(el("div", { class: "chat-history-head" }, el("p", { class: "pw-label" }, title),
      el("button", { type: "button", class: "btn btn-quiet btn-small", onclick: () => { box.hidden = true; } }, "Close")), ...body);
    box.scrollIntoView({ block: "nearest", behavior: "smooth" });
  }
  async function showSummary(id, title) {
    const text = el("p", { class: "chat-summary dim" }, "Reading the whole conversation…");
    panel("Summary" + (title ? " · " + title : ""), text);
    orb("thinking", "Summarizing");
    try {
      const s = await MIA.summarize(id || "current");
      text.textContent = s.text;
      text.classList.remove("dim");
      if (s.count) text.after(el("div", { class: "row-buttons" }, MIAShell.copyButton(s.text, "Copy Summary", "btn btn-small")),
        s.by === "model" ? el("p", { class: "dim" }, "My reading of the whole conversation. The export is the exact record.") : null);
    } catch (e) { text.textContent = e.message; }
    orb("idle", "Ready");
  }
  async function showExport(id, title, form) {
    form = form === "json" ? "json" : "markdown";
    let made = null;
    const text = el("textarea", { class: "chat-export-text", readonly: true, rows: "9", "aria-label": "The conversation, exported" });
    const told = el("p", { class: "dim", role: "status" });
    const pick = (f, label) => el("button", { type: "button", class: "btn btn-small" + (f === form ? "" : " btn-ghost"),
      "aria-pressed": String(f === form), onclick: () => showExport(id, title, f) }, label);
    const save = el("button", { type: "button", class: "btn btn-small", onclick: async () => {
      if (!made) return;
      const done = await MIAShell.act({ kind: "conversation.export", params: { conversation_id: made.id, form } }, { quick: true });
      if (done) told.replaceChildren((done.result || "Saved") + ". ", el("a", { href: "files.html#Conversations" }, "Open Files"));
    } }, "Save to Files");
    panel("Export" + (title ? " · " + title : ""), el("div", { class: "row-buttons" }, pick("markdown", "Markdown"), pick("json", "JSON")),
      text, el("div", { class: "row-buttons" }, MIAShell.copyButton(() => text.value, "Copy", "btn btn-small"), save), told);
    try {
      made = await MIA.exportConversation(id || "current", form);
      text.value = made.text;
      told.textContent = made.count ? made.count + (made.count === 1 ? " message" : " messages") + ", in order, each with who said it and when."
        : "Nothing has been said in this conversation yet.";
      if (!made.count) made = null;
    } catch (e) { told.textContent = e.message; }
  }
  $("summary-btn").addEventListener("click", () => showSummary("current", ""));
  $("export-btn").addEventListener("click", () => showExport("current", ""));
  $("new-chat").addEventListener("click", async () => {
    try {
      await MIA.newChat();
      $("log").replaceChildren();
      $("panel").hidden = true;
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
      const ask = params.get("ask");  // sent at once from MIA's own pages; a link from elsewhere only fills the box
      if (ask && MIAShell.askedHere(ask)) send(ask); else if (ask) { $("input").value = ask; $("input").focus(); }
      if (params.get("draft")) { $("input").value = params.get("draft"); $("input").focus(); }
      if (params.get("voice")) toggleMic();  // ?voice=1: start listening (startListening() no longer exists)
      history.replaceState(null, "", location.pathname);
    }
  }, { refreshOnChange: false, talk: false });
})();
