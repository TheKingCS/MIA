/*
 * assistant.js — MIA Assistant (DEC-0018, claude). Typed turns go through
 * MIA.talk; spoken ones are recorded here, turned into the mono 16-bit WAV
 * MIA's voice path expects, and sent with MIA.voice. Her spoken reply plays
 * when her computer has a voice.
 */
(function () {
  "use strict";
  const { el, say } = MIAShell;
  const $ = (id) => document.getElementById(id);
  const params = new URLSearchParams(location.search);
  const SUGGESTIONS = ["What should I focus on today?", "What's due this week?", "How are my finances?", "What did I get done?"];

  function bubble(who, text) {
    const b = el("div", { class: "chat-bubble " + who }, who === "mia" ? el("span", { class: "chat-who", "aria-hidden": "true" }, "✦") : null,
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
      MIAShell.refresh();
    } catch (e) {
      reply.textContent = e.message;
    }
    reply.parentElement.classList.remove("thinking");
  }

  // ------------------------------------------------------------ voice
  let recorder = null;
  let chunks = [];
  function wav(samples, rate) {
    const buffer = new ArrayBuffer(44 + samples.length * 2);
    const v = new DataView(buffer);
    const str = (o, s) => [...s].forEach((c, i) => v.setUint8(o + i, c.charCodeAt(0)));
    str(0, "RIFF"); v.setUint32(4, 36 + samples.length * 2, true); str(8, "WAVE"); str(12, "fmt ");
    v.setUint32(16, 16, true); v.setUint16(20, 1, true); v.setUint16(22, 1, true); v.setUint32(24, rate, true);
    v.setUint32(28, rate * 2, true); v.setUint16(32, 2, true); v.setUint16(34, 16, true); str(36, "data");
    v.setUint32(40, samples.length * 2, true);
    samples.forEach((x, i) => v.setInt16(44 + i * 2, Math.max(-1, Math.min(1, x)) * 0x7fff, true));
    return new Blob([buffer], { type: "audio/wav" });
  }
  async function toWav(blob) {
    const ctx = new AudioContext();
    const audio = await ctx.decodeAudioData(await blob.arrayBuffer());
    ctx.close();
    const rate = 16000;
    const offline = new OfflineAudioContext(1, Math.ceil(audio.duration * rate), rate);
    const source = offline.createBufferSource();
    source.buffer = audio;
    source.connect(offline.destination);
    source.start();
    return wav((await offline.startRendering()).getChannelData(0), rate);
  }
  async function startListening() {
    if (!navigator.mediaDevices || !window.MediaRecorder) {
      note("This browser can't record here. Voice works in MIA's phone app, or on the PC.");
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      chunks = [];
      recorder = new MediaRecorder(stream);
      recorder.ondataavailable = (e) => chunks.push(e.data);
      recorder.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop());
        $("mic").classList.remove("listening");
        const reply = bubble("mia thinking", "…");
        try {
          const turn = await MIA.voice(await toWav(new Blob(chunks)));
          if (turn.transcript) reply.parentElement.before(el("div", { class: "chat-bubble me" }, el("p", {}, turn.transcript)));
          reply.textContent = turn.reply_text || "Done.";
          if (turn.audio_wav_base64) new Audio("data:audio/wav;base64," + turn.audio_wav_base64).play().catch(() => {});
          MIAShell.refresh();
        } catch (e) { reply.textContent = e.message; }
        reply.parentElement.classList.remove("thinking");
      };
      recorder.start();
      $("mic").classList.add("listening");
      note("Listening… tap the mic again when you're done.");
    } catch (e) {
      note(window.isSecureContext ? "MIA needs permission to use the microphone." :
        "The browser only allows the microphone on a secure address. Voice works in MIA's phone app, or on the PC.");
    }
  }
  function toggleMic() {
    if (recorder && recorder.state === "recording") { recorder.stop(); note(""); }
    else startListening();
  }
  function note(text) { $("note").textContent = text; $("note").hidden = !text; }

  // ------------------------------------------------------------ start
  $("form").addEventListener("submit", (e) => { e.preventDefault(); const t = $("input").value; $("input").value = ""; send(t); });
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
