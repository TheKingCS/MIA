/*
 * player.js — the one music player every page shares (claude, 2026-11-10;
 * Zac: a song has to keep playing with the Music app closed and while moving
 * through the other apps). A song used to live in the Music page's own
 * <audio>, so it stopped the moment another page opened. Now whoever can
 * keep playing does the playing:
 *   - in the phone app, the phone's own player (android-phone Music.kt,
 *     through window.MIAPhoneMusic): it plays on with the screen off;
 *   - in the desktop window, MIA herself (core/music_manager.py, through
 *     /api/music/now, /play and /control): the pages only ask;
 *   - in a plain browser, this page's <audio>. What was playing and where
 *     is kept for the tab, and the next page carries on from that second
 *     (a short gap while the page changes is all a browser allows).
 * Pages use MIAPlayer.play(tracks, at), .control(what), .now() and .on(fn);
 * the frame (shell.js) shows the small now-playing bar from the same calls.
 * Only library tracks play, by id.
 */
(function () {
  "use strict";
  const KEPT = "mia.player", NAMES = "mia.player.names";
  const idle = () => ({ track: "", title: "", artist: "", album: "", number: 0, total: 0, playing: false, seconds: 0, length: 0 });
  const listeners = [];
  let state = idle(), source = null, timer = null;

  const keep = (key, value) => { try { sessionStorage.setItem(key, JSON.stringify(value)); } catch (e) { /* a private window: nothing kept */ } };
  const kept = (key) => { try { return JSON.parse(sessionStorage.getItem(key) || "null"); } catch (e) { return null; } };
  // What each song in the list is called: the phone's player only knows ids.
  let names = kept(NAMES) || {};

  function set(now) {
    const next = Object.assign(idle(), now || {});
    const named = names[next.track] || {};
    next.title = next.title || named.title || "";
    next.artist = next.artist || named.artist || "";
    next.album = next.album || named.album || "";
    state = next;
    listeners.forEach((fn) => { try { fn(state); } catch (e) { /* one listener never stops the rest */ } });
    if (state.track && !state.title) nameIt(state.track);
  }

  // A song somebody else started (the glasses, her voice): its name comes from the library, asked once.
  let asked = false;
  async function nameIt(id) {
    if (asked) return;
    asked = true;
    try {
      const library = await MIA.music();
      (library.tracks || []).forEach((t) => { names[t.id] = { title: t.title, artist: t.artist, album: t.album }; });
      if (names[id] && state.track === id) set(state);
    } catch (e) { /* it shows as "Playing" */ }
  }

  // --- the phone app: Android plays (Music.kt). It answers with what's playing, or nothing when it refuses.
  const told = (text) => {
    const now = text ? JSON.parse(text) : null;
    if (!now) throw new Error("Couldn't play that.");
    return now;
  };
  const phone = {
    play: async (ids, at) => told(window.MIAPhoneMusic.play(JSON.stringify(ids), at)),
    control: async (what) => told(window.MIAPhoneMusic.control(what)),
    now: async () => told(window.MIAPhoneMusic.now()),
    polled: true,
  };

  // --- the desktop window: MIA plays, on the computer's own speakers.
  const engine = {
    play: (ids, at) => MIA.playerPlay(ids, at),
    control: (what) => MIA.playerControl(what),
    now: () => MIA.playerNow(),
    polled: true,
  };

  // --- a plain browser: this page plays, and the next page picks it up.
  const audio = new Audio();
  audio.preload = "none";
  // wanted: whether the person means a song to be playing (kept for the next page). stalled: this page
  // couldn't get it (a download cut short as the page closes must not read as a pause on the next one).
  let queue = [], at = -1, url = null, wanted = false, stalled = false, loading = false, from = 0, savedAt = 0, turn = 0;
  const here = () => ({
    track: at >= 0 ? queue[at] : "", number: at + 1, total: queue.length, playing: wanted && !stalled,
    seconds: Math.floor(audio.src ? audio.currentTime : from), length: Math.floor(audio.duration || 0), loading,
  });
  const save = () => keep(KEPT, { queue, at, playing: wanted, seconds: audio.src ? audio.currentTime : from });
  async function load(i, second, strict) {
    if (i < 0 || i >= queue.length) { quiet(); return; }
    const mine = ++turn;  // a song picked while this one is still coming wins
    at = i;
    from = second || 0;
    loading = true;
    stalled = false;
    set(here());
    try {
      if (MIA.demo) throw new Error("Songs play from your MIA, not in the demo.");
      const blob = await MIA.download("/api/music/track/" + encodeURIComponent(queue[i]) + "/audio");
      if (mine !== turn) return;
      if (url) URL.revokeObjectURL(url);
      url = URL.createObjectURL(blob);
      audio.src = url;
      if (from) audio.currentTime = from;
      // A browser may refuse sound on a page nobody has touched yet: then it waits, paused, for Play.
      if (wanted) await audio.play().catch(() => { wanted = false; });
    } catch (e) {
      if (mine === turn) stalled = true;
      if (strict) throw (MIA.demo ? e : new Error("Couldn't play " + ((names[queue[i]] || {}).title || "that song") + "."));
    } finally {
      if (mine === turn) { loading = false; if (!stalled) save(); set(here()); }
    }
  }
  function quiet() {
    turn += 1;
    loading = false;
    audio.pause();
    audio.removeAttribute("src");
    queue = []; at = -1; wanted = false; stalled = false; from = 0;
    save();
    set(here());
  }
  audio.addEventListener("ended", () => { wanted = true; load(at + 1, 0).catch(() => {}); });
  audio.addEventListener("timeupdate", () => {
    set(here());
    if (Date.now() - savedAt > 2000) { savedAt = Date.now(); save(); }
  });
  window.addEventListener("pagehide", () => { if (source === page && at >= 0) save(); });
  const page = {
    play: async (ids, start) => { queue = ids.slice(); wanted = true; await load(start, 0, true); return here(); },
    control: async (what) => {
      if (what === "stop") quiet();
      else if (what === "next") { wanted = true; await load(at + 1, 0, true); }
      else if (what === "previous") { wanted = true; await load(Math.max(0, at - 1), 0, true); }
      else if (what === "pause") { wanted = false; stalled = false; audio.pause(); save(); }
      else if (what === "resume" && at >= 0) {
        wanted = true;
        if (audio.src && !stalled) await audio.play(); else await load(at, from, true);
        save();
      }
      return here();
    },
    now: async () => here(),
    polled: false,
    // What the last page was playing: carried on from the same second (or left paused there).
    wake: () => {
      const last = kept(KEPT);
      if (!last || !Array.isArray(last.queue) || !(last.at >= 0) || last.at >= last.queue.length) return;
      queue = last.queue; at = last.at; from = last.seconds || 0; wanted = !!last.playing;
      if (wanted) load(at, from).catch(() => {}); else set(here());
    },
  };

  async function choose() {
    if (window.MIAPhoneMusic) return phone;
    if (MIA.desktop && !MIA.demo) {
      try { if ((await MIA.playerNow()).here) return engine; } catch (e) { /* not this MIA: the page plays */ }
    }
    return page;
  }

  // The phone's and the computer's player are asked how far along they are: each second while a song is
  // on, now and then otherwise (a song can be started by voice, or from the glasses).
  async function poll() {
    clearTimeout(timer);
    if (!document.hidden) { try { set(await source.now()); } catch (e) { /* asked again next time */ } }
    timer = setTimeout(poll, state.track ? 1000 : 5000);
  }

  const ready = choose().then((chosen) => {
    source = chosen;
    if (source.polled) poll(); else source.wake();
  });

  async function ask(run) {
    await ready;
    set(await run());
    if (source.polled) poll();
    return state;
  }

  window.MIAPlayer = {
    // tracks: [{id, title, artist, album}] (or bare ids); at: which one first.
    play: (tracks, at) => {
      const ids = tracks.map((t) => (typeof t === "string" ? t : t.id));
      tracks.forEach((t) => { if (t && t.id && t.title) names[t.id] = { title: t.title, artist: t.artist || "", album: t.album || "" }; });
      keep(NAMES, Object.fromEntries(ids.filter((id) => names[id]).map((id) => [id, names[id]])));
      return ask(() => source.play(ids, at || 0));
    },
    // what: pause, resume, next, previous or stop.
    control: (what) => ask(() => source.control(what)),
    now: () => state,
    on: (fn) => { listeners.push(fn); fn(state); },
    ready,
  };
})();
