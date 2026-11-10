/*
 * news.js — Good News Radio (claude, 2026-11-07, DEC-0096; the station itself 2026-11-10, Zac: "it should list
 * the news stories so I can read more about them, should have an audio card playing the station where I can
 * play or pause it, maybe follow a story").
 * Renders MIA.news() (core/good_news.py screen): the station (each personality's episode, played here: its
 * recording from the music library when there is one, else read aloud a part at a time in MIA's own voice),
 * every story with its summary, how it's known, its caveats and where to read it in full, the stories you
 * follow with what was reported since, and the outlets it reads. Each button is an action (core/news_actions.py)
 * that does what the words do. Formatting and playback only; the look is muse's.
 */
(function () {
  "use strict";
  const { el, act, say } = MIAShell;
  const $ = (id) => document.getElementById(id);
  const WORDS = ["No", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten"];
  const WHEN = { morning: "Morning", afternoon: "Afternoon", evening: "Evening", "late night": "Late night" };
  const KIND = { primary: "The source itself", journalism: "Journalism", solutions: "Solutions journalism", "press release": "Press releases" };
  const IDLE = { key: null, mode: null, at: 0, ahead: null, pending: false };
  let data = null, showing = null, on = IDLE, ticket = 0, url = null, note = "", told = null, again = null;
  let scriptOpen = false, sourcesOpen = false;

  // One player for the page, kept outside the panel so a repaint (an action, a change on another device)
  // never stops what's playing. `wanted` is whether the station is meant to be playing: the element itself
  // is paused between two parts read aloud, and that isn't a pause.
  const audio = el("audio", { preload: "none", class: "music-audio" });
  document.body.append(audio);
  let wanted = false, ours = false;
  audio.addEventListener("ended", () => (on.mode === "spoken" ? speakFrom(on.at + 1, ticket) : stop()));
  audio.addEventListener("timeupdate", progress);
  audio.addEventListener("play", drawAir);
  audio.addEventListener("pause", () => {  // paused from outside the page (a headset button) counts as a pause
    if (ours) ours = false; else if (!audio.ended) wanted = false;
    drawAir();
  });
  const hush = () => { if (!audio.paused) { ours = true; audio.pause(); } };

  const day = (iso, long) => (iso ? new Date(iso.slice(0, 10) + "T00:00:00").toLocaleDateString(undefined,
    long ? { weekday: "long", day: "numeric", month: "long" } : { day: "numeric", month: "short" }) : "");
  const clock = (s) => (isFinite(s) ? Math.floor(s / 60) + ":" + String(Math.floor(s % 60)).padStart(2, "0") : "0:00");
  const btn = (label, cls, onclick, off) => el("button", { type: "button", class: "btn btn-small " + cls, onclick, disabled: !!off }, label);
  const link = (href, text) => el("a", { href, target: "_blank", rel: "noopener noreferrer" }, text);
  const doIt = (kind, params) => act({ kind, params: params || {} }, { quick: true });
  const parts = (key) => String((data.scripts || {})[key] || "").split(/\n\s*\n/).map((p) => p.trim()).filter(Boolean);
  const fill = (node, ...kids) => node.replaceChildren(...kids.flat().filter(Boolean));  // replaceChildren would print a null
  const named = (key) => (data.personalities.find((p) => p.key === key) || {}).name || "";

  // ---------------------------------------------------------------- playing the station
  function stop(why) {
    ticket += 1;
    hush();
    wanted = false;
    on = IDLE;
    note = why || "";
    drawAir();
  }

  // Said once a day, the first time an episode really plays: listening here counts like asking for it.
  function heard(key) {
    if (told === data.day) return;
    told = data.day;
    MIA.newsHeard(key).catch(() => {});
  }

  function failed(e) {
    stop(MIA.demo ? "The station plays from your MIA, not in the demo." : "Couldn't play it: " + ((e && e.message) || "no sound came back") + ".");
  }

  // Read aloud a part at a time (the opening, each story, the close), the next part fetched while this one plays.
  async function speakFrom(i, mine) {
    const key = on.key, list = parts(key);
    if (mine !== ticket) return;
    if (i >= list.length) { stop(); return; }
    const ready = on.ahead && on.ahead.i === i;
    const waiting = ready ? on.ahead.sound : MIA.speak(list[i]);
    on = { key, mode: "spoken", at: i, ahead: null, pending: true };
    note = ready ? "" : "Getting her voice…";
    drawAir();
    try {
      const got = await waiting;
      if (mine !== ticket) return;
      on.pending = false;
      note = "";
      audio.src = "data:audio/wav;base64," + got.audio_wav_base64;
      if (!wanted) { drawAir(); return; }  // paused while it was coming: it waits, ready to go on
      await audio.play();
      if (mine !== ticket) return;
      heard(key);
      if (i + 1 < list.length) {
        const sound = MIA.speak(list[i + 1]);
        sound.catch(() => {});  // asked for again, and answered for, when its turn comes
        on.ahead = { i: i + 1, sound };
      }
      drawAir();
    } catch (e) { if (mine === ticket) failed(e); }
  }

  async function play() {
    const key = showing;
    if (on.key === key && on.pending) { wanted = true; drawAir(); return; }  // its sound is on the way
    if (on.key === key && on.mode && audio.src && audio.paused && !audio.ended) {
      wanted = true;
      audio.play().catch(failed);
      return;
    }
    const mine = ++ticket;
    hush();
    wanted = true;
    on = { key, mode: null, at: 0, ahead: null, pending: false };
    note = "Loading…";
    drawAir();
    const id = (data.audio || {})[key];
    if (id) {
      try {
        const blob = await MIA.download("/api/music/track/" + encodeURIComponent(id) + "/audio");
        if (mine !== ticket) return;
        if (url) URL.revokeObjectURL(url);
        url = URL.createObjectURL(blob);
        audio.src = url;
        on = { key, mode: "track", at: 0, ahead: null, pending: false };
        note = "";
        if (!wanted) { drawAir(); return; }
        await audio.play();
        if (mine !== ticket) return;
        heard(key);
        drawAir();
        return;
      } catch (e) { if (mine !== ticket) return; }  // the recording didn't come: her own voice reads it instead
    }
    if (!parts(key).length) { stop("There's nothing to read in this episode."); return; }
    speakFrom(0, mine);
  }

  const pause = () => { wanted = false; if (audio.paused) drawAir(); else audio.pause(); };

  const share = () => {
    const part = audio.duration ? Math.min(1, audio.currentTime / audio.duration) : 0;
    return on.mode === "spoken" ? (on.at + part) / Math.max(1, parts(on.key).length) : part;
  };

  function progress() {
    const fill = document.querySelector(".nw-meter .meter-fill"), time = $("nw-time");
    if (fill) fill.style.width = (100 * share()).toFixed(1) + "%";
    if (time) time.textContent = timeWords();
    const reading = on.mode === "spoken" ? on.at : -1;
    document.querySelectorAll(".nw-script p").forEach((p, i) => p.classList.toggle("nw-reading", i === reading));
  }

  function timeWords() {
    if (on.mode === "track") return clock(audio.currentTime) + " / " + clock(audio.duration);
    if (on.mode === "spoken") return "Part " + (on.at + 1) + " of " + parts(on.key).length;
    return "";
  }

  // A tap on the line moves to that moment of the recording, or to that part when she's reading it herself.
  function seek(event) {
    const box = event.currentTarget.getBoundingClientRect();
    const at = Math.max(0, Math.min(0.999, (event.clientX - box.left) / Math.max(1, box.width)));
    if (on.mode === "track" && audio.duration) audio.currentTime = at * audio.duration;
    else if (on.mode === "spoken") { hush(); speakFrom(Math.floor(at * parts(on.key).length), ++ticket); }
  }

  // ---------------------------------------------------------------- the page
  function drawAir() {
    const box = $("nw-air");
    if (!box || !data || !data.day) return;
    const mine = on.key === showing, going = mine && wanted, waiting = mine && !!note;
    const voiced = !!(data.audio || {})[showing], name = named(showing);
    const chips = el("div", { class: "nw-voices", role: "group", "aria-label": "Who reads it" }, data.personalities.map((p) => el("button", {
      type: "button", class: "nw-voice" + (p.key === showing ? " on" : ""), "aria-pressed": p.key === showing ? "true" : "false",
      onclick: () => { if (p.key !== showing) { stop(); showing = p.key; drawAir(); } } },
      el("strong", {}, p.name), el("span", {}, WHEN[p.when] || p.when))));
    const script = el("details", { class: "nw-script", open: scriptOpen, ontoggle: (e) => { scriptOpen = e.currentTarget.open; } },
      el("summary", {}, "Read along"), parts(showing).map((text) => el("p", {}, text)));
    fill(box,
      el("div", { class: "sect" }, el("h2", {}, "On the air"), el("span", { class: "mu-label" }, waiting ? "" : going ? "Playing" : mine && on.mode ? "Paused" : "")),
      chips,
      el("div", { class: "nw-player" },
        el("button", { type: "button", class: "mu-ctl nw-play", "aria-label": going ? "Pause" : "Play " + name + "'s episode",
          onclick: () => (going ? pause() : play()) }, going ? "❚❚" : "▶"),
        el("div", { class: "nw-now" },
          el("strong", {}, name + " · " + day(data.day, true)),
          el("span", { class: "dim" }, waiting ? note : voiced ? "In " + name + "'s voice" : "Read in MIA's own voice"),
          el("div", { class: "meter nw-meter", onclick: seek, role: "presentation" }, el("div", { class: "meter-fill", style: "width:0%" })),
          el("span", { class: "nw-time", id: "nw-time" }, ""))),
      !waiting && note ? el("p", { class: "nw-problem", role: "alert" }, note) : null,
      script);
    progress();
  }

  function story(s) {
    return el("article", { class: "glass nw-story" },
      el("div", { class: "nw-tags" }, el("span", { class: "kind " + (s.tone || "") }, s.tag || s.known),
        s.topic ? el("span", { class: "kind" }, s.topic) : null,
        s.misleading ? el("span", { class: "kind bad" }, "You marked it misleading") : null),
      el("h3", { class: "nw-title" }, s.title),
      s.summary ? el("p", { class: "nw-summary" }, s.summary) : null,
      el("p", { class: "nw-caveat" }, [s.how, ...s.caveats].filter(Boolean).join(" ")),
      s.reads.length ? el("p", { class: "nw-reads" }, "Read the full story at ",
        s.reads.flatMap((r, i) => [i ? (i === s.reads.length - 1 ? " or " : ", ") : "", link(r.href, r.outlet || "the source")]), ".") : null,
      el("div", { class: "row-buttons" },
        s.followed ? btn("Following ✓", "btn-amber", () => doIt("news.unfollow", { story_id: s.id }))
          : btn("Follow this story", "btn-ghost", () => doIt("news.follow", { story_id: s.id })),
        btn("This was misleading", "btn-ghost", () => doIt("news.misleading", { story_id: s.id }), s.misleading)));
  }

  function followed(f) {
    const reports = f.updates.map((u) => el("li", { class: "nw-report" },
      el("span", { class: "kind " + (u.good ? "ok" : "") }, u.good ? "Good news" : "Update"),
      el("div", {}, el("p", { class: "nw-title" }, u.href ? link(u.href, u.title) : u.title),
        el("p", { class: "nw-caveat" }, [u.outlet, day(u.published || u.found)].filter(Boolean).join(" · ")),
        u.summary ? el("p", { class: "nw-summary" }, u.summary) : null)));
    return el("article", { class: "glass nw-story" },
      el("h3", { class: "nw-title" }, f.title),
      el("p", { class: "nw-caveat" }, ["Followed since " + day(f.since), f.topic].filter(Boolean).join(" · ")),
      reports.length ? el("ul", { class: "nw-reports" }, reports)
        : el("p", { class: "nw-summary" }, "Nothing new yet. She looks each day the feeds are read."),
      el("div", { class: "row-buttons" }, btn("Stop following", "btn-ghost", () => doIt("news.unfollow", { story_id: f.id }))));
  }

  // Where it reads: every outlet by kind, what leaves this computer (nothing about you), and the off switch.
  function reads(offSwitch) {
    const kinds = [];
    data.sources.forEach((s) => { if (!kinds.includes(s.kind)) kinds.push(s.kind); });
    return el("details", { class: "glass nw-where", open: sourcesOpen, ontoggle: (e) => { sourcesOpen = e.currentTarget.open; } },
      el("summary", {}, "Where it reads (" + data.sources.length + " outlets)"),
      el("p", { class: "nw-caveat" }, "Once a day, public feeds only. Nothing about you is sent."),
      kinds.map((kind) => el("p", { class: "nw-summary" }, el("span", { class: "nw-label" }, KIND[kind] || kind), " ",
        data.sources.filter((s) => s.kind === kind).map((s) => s.name).join(", "))),
      data.failed && data.failed.length ? el("p", { class: "nw-problem" }, "Didn't answer for this episode: " + data.failed.join(", ") + ".") : null,
      offSwitch ? el("div", { class: "row-buttons" }, btn("Turn Good News Radio off", "btn-ghost", () => { stop(); doIt("news.turn_off"); })) : null);
  }

  // Today's episode: a button to start it where it can be made, and a look every 20 seconds while it is.
  function making() {
    clearTimeout(again);
    if (data.making) {
      again = setTimeout(() => MIAShell.refresh(), 20000);
      return el("p", { class: "nw-making", role: "status" }, "Today's episode is being made now: reading the feeds and recording the voices takes a minute or two.");
    }
    return data.can_make ? el("div", { class: "row-buttons" }, btn("Make today's episode", "btn-amber", () => doIt("news.make"))) : null;
  }

  function paint() {
    const panel = $("panel");
    if (!data.on) {
      stop();
      $("news-sub").textContent = "It's off.";
      sourcesOpen = true;
      fill(panel, el("section", { class: "glass money-section nw-off" },
        el("h2", {}, "A few good things, once a day"),
        el("p", {}, "MIA reads credible outlets each morning, keeps the stories she can stand behind, says how each one is known, and reads them to you in four voices. You can read every story in full, follow one to hear what happens next, and mark one that misled you."),
        el("div", { class: "row-buttons" }, btn("Turn it on", "btn-amber", () => doIt("news.turn_on")))), reads(false));
      return;
    }
    if (!data.day) {
      stop();
      $("news-sub").textContent = data.making ? "Today's episode is on its way." : "No episode yet.";
      fill(panel, el("section", { class: "glass money-section nw-off" },
        el("h2", {}, "Nothing on the air yet"),
        data.making || data.can_make ? null : el("p", {}, "Episodes are made on the home computer once a day. The next one appears here when it's ready."),
        making()), data.following.length ? following() : null, reads(true));
      return;
    }
    if (!data.personalities.some((p) => p.key === showing)) showing = data.now;
    const n = data.stories.length;
    $("news-sub").textContent = data.today ? "Today's episode: " + n + (n === 1 ? " story." : " stories.") : "The latest episode is from " + day(data.day, true) + ".";
    fill(panel,
      el("section", { class: "nw-head" }, el("span", { class: "nw-label" }, day(data.day, true)),
        el("h2", {}, (WORDS[n] || String(n)) + (n === 1 ? " story" : " stories") + (data.today ? " today" : "")),
        data.today ? null : making()),
      el("section", { class: "glass money-section nw-air", id: "nw-air" }),
      el("div", { class: "nw-stories" }, data.stories.map(story)),
      data.following.length ? following() : null,
      reads(true));
    drawAir();
  }

  function following() {
    return el("section", { class: "nw-follow" }, el("div", { class: "sect" }, el("h2", {}, "Stories you follow")),
      el("div", { class: "nw-stories" }, data.following.map(followed)));
  }

  MIAShell.start(async () => { data = await MIA.news(); paint(); });
})();
