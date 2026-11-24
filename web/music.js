/*
 * music.js — the Music screen (claude, 2026-10-16; Zac: the app only opened
 * a chat). Renders MIA.music() (core/web_more.py): Songs (search), Playlists
 * and Artists. A song plays through the shared player (player.js; Zac,
 * 2026-11-10: it has to keep playing with this page closed), so it carries
 * on in the other apps; the next one in the list follows. Playlists and
 * Scan Library are actions.
 * YouTube (2026-11-24, core/youtube_music.py): its tab searches YouTube (with
 * his key) or takes a pasted link, plays in YouTube's own embedded player (a
 * YouTube song plays here, on this page, never through the file player), and
 * saves songs as links (youtube.save) that sit in playlists beside his files.
 * MIA's pick by voice (play_on_youtube) waits at the top for one press. Pop Out moves the player to its own
 * window (youtube-player.html), so a song keeps playing across MIA's pages.
 */
(function () {
  "use strict";
  const { el, act, form, say } = MIAShell;
  const $ = (id) => document.getElementById(id);
  const TABS = [["songs", "Songs"], ["playlists", "Playlists"], ["artists", "Artists"], ["youtube", "YouTube"], ["canplay", "Can Play"]];
  let page = null, query = "", openList = null, artist = null;
  let ytWords = "", ytFound = null, ytProblem = "", ytNeedsKey = false, ytNow = null;
  let tab = TABS.some(([t]) => t === location.hash.slice(1)) ? location.hash.slice(1) : "songs";
  // What's playing is the shared player's (player.js), not this page's: it keeps going when the page closes.
  let now = MIAPlayer.now(), shown = "";
  const progress = () => (now.length ? Math.min(100, Math.round(100 * now.seconds / now.length)) : 0) + "%";

  // Songs already on the phone: Android has to say yes first (Permissions.kt).
  const phoneAsks = () => { try { return window.MIAPhonePermissions && !JSON.parse(window.MIAPhonePermissions.status()).music; } catch (e) { return false; } };
  window.MIAPermissions = { changed: () => { if (!phoneAsks()) act({ kind: "music.scan", params: {} }); } };
  const btn = (label, cls, onclick) => el("button", { type: "button", class: "btn " + cls, onclick }, label);
  const buttons = (...list) => el("div", { class: "row-buttons" }, list.filter(Boolean));
  const section = (title, actions, ...body) =>
    el("section", { class: "glass money-section" }, el("div", { class: "sect" }, el("h2", {}, title), actions), ...body);
  const byId = (id) => (page ? page.tracks.find((t) => t.id === id) : null);

  // A list may hold YouTube songs: one of those plays the list's YouTube songs in YouTube's player here; a song
  // from a file plays the list's files through the shared player.
  const isYt = (id) => !!(byId(id) || {}).youtube;
  function play(ids, start) {
    start = start || 0;
    const chosen = ids[start];
    if (chosen && isYt(chosen)) {
      const yt = ids.filter(isYt);
      const from = yt.indexOf(chosen);
      ytPlay(yt.slice(from).concat(yt.slice(0, from)).map((id) => ({ video_id: byId(id).youtube, title: byId(id).title })));
      return;
    }
    const files = ids.filter((id) => !isYt(id));
    if (!files.length) return;
    MIAPlayer.play(files.map((id) => byId(id) || id), Math.max(0, files.indexOf(chosen))).catch((e) => say(e.message));
  }
  // YouTube's own player, embedded (the privacy-enhanced host). Starting it pauses a song from a file.
  function ytPlay(songs) {
    if (!songs.length) return;
    if (now.playing) control("pause");
    ytNow = songs;
    const ids = songs.map((s) => s.video_id).filter((v) => /^[A-Za-z0-9_-]{11}$/.test(v));
    const src = "https://www.youtube-nocookie.com/embed/" + ids[0] + "?autoplay=1&rel=0&modestbranding=1" +
      (ids.length > 1 ? "&playlist=" + ids.slice(1, 50).join(",") : "");
    let box = $("yt-player");
    if (!box) { box = el("section", { class: "glass yt-player", id: "yt-player", "aria-label": "Playing from YouTube" }); $("panel").before(box); }
    // Pop Out: the same songs in their own small window (youtube-player.html), which keeps playing while this
    // window moves between MIA's pages.
    const popOut = () => {
      const url = "youtube-player.html?v=" + ids.join(",") + "&t=" + encodeURIComponent(songs[0].title || "");
      const win = window.open(url, "mia-youtube", "popup,width=480,height=330");
      if (win) { box.remove(); ytNow = null; } else say("Your browser kept the window from opening; it plays here instead.");
    };
    box.replaceChildren(
      el("div", { class: "sect" }, el("h2", {}, "▶ " + (songs[0].title || "YouTube")),
        buttons(btn("Pop Out", "btn-ghost btn-small", popOut),
          btn("Close", "btn-ghost btn-small", () => { box.remove(); ytNow = null; }))),
      el("div", { class: "yt-frame" }, el("iframe", { src, title: "YouTube player", allow: "autoplay; encrypted-media; picture-in-picture",
        allowfullscreen: true, referrerpolicy: "strict-origin-when-cross-origin" })),
      songs.length > 1 ? el("p", { class: "dim" }, songs.length - 1 + " more after this one.") : null);
  }
  const control = (what) => MIAPlayer.control(what).catch((e) => say(e.message));

  // The canvas's Now Playing bar (DEC-0113): the song, its controls, and a progress line that follows it.
  function drawPlayer() {
    if (!$("player")) return;
    const t = now.track ? (byId(now.track) || now) : null;
    const icon = (label, text, what) => el("button", { type: "button", class: "mu-ctl", "aria-label": label, title: label, onclick: () => control(what) }, text);
    $("player").replaceChildren(
      el("div", { class: "mu-bar" },
        el("div", { class: "music-now" }, el("span", { class: "mu-label" }, "Now Playing"),
          el("strong", {}, t ? t.title || "Playing" : "Nothing playing"),
          el("span", { class: "dim" }, now.loading ? "Loading…" : (t ? [t.artist, t.album].filter(Boolean).join(" · ") : "Pick a song to play it here."))),
        t ? el("div", { class: "mu-ctls" }, icon("Previous", "⏮", "previous"),
          now.playing ? icon("Pause", "❚❚", "pause") : icon("Play", "▶", "resume"),
          icon("Next", "⏭", "next"), icon("Stop", "■", "stop")) : null),
      el("div", { class: "mu-progress" }, el("div", { class: "meter" }, el("div", { class: "meter-fill", style: "width:" + progress() }))));
    $("player").hidden = !t;
    document.querySelectorAll(".music-row").forEach((r) => r.classList.toggle("playing", !!t && r.dataset.id === now.track));
  }
  MIAPlayer.on((state) => {
    const key = state.track + "|" + state.playing + "|" + !!state.loading;
    now = state;
    if (key !== shown) { shown = key; drawPlayer(); return; }
    const fill = document.querySelector(".mu-progress .meter-fill");
    if (fill) fill.style.width = progress();
  });

  async function toPlaylist(t) {
    if (!page.playlists.length) { say("Make a playlist first (Playlists → New Playlist)."); return; }
    const v = await form("Add " + t.title + " To…", [{ name: "playlist_id", label: "Playlist", type: "pick", required: true, options: ["playlists"], default: null }],
      {}, { playlists: page.playlists.map((p) => ({ id: p.id, name: p.name })) });
    if (v) act({ kind: "playlist.add_track", params: { playlist_id: v.playlist_id, track_id: t.id } });
  }
  // Songs from this phone or computer (Zac, 2026-10-16: "upload mp3 files from my device's files").
  function uploadSongs() {
    const input = el("input", { type: "file", multiple: true, hidden: true, accept: "audio/*,.mp3,.m4a,.flac,.ogg,.opus,.wav" });
    input.addEventListener("change", async () => {
      const files = [...input.files];
      for (const [i, file] of files.entries()) {
        try {
          say((files.length > 1 ? "Uploading " + (i + 1) + " of " + files.length + "… " : "Uploading… ") + file.name);
          say((await MIA.upload("/api/music/upload", file)).message);
        } catch (e) { say("Couldn't add " + file.name + ": " + e.message); }
      }
      input.remove();
      page = await MIA.music();
      draw();
    });
    document.body.append(input);
    input.click();
  }

  async function saveTo(s) {
    const v = await form("Save " + (s.title || s.shown || "this song") + " To…", [{ name: "playlist_id", label: "Playlist", type: "pick", required: true, options: ["playlists"], default: null }],
      {}, { playlists: page.playlists.map((p) => ({ id: p.id, name: p.name })) });
    if (v) act({ kind: "youtube.save", params: { video: s.video_id, title: s.title, channel: s.channel, playlist_id: v.playlist_id } });
  }
  // His YouTube key, for search: sent once to MIA (kept sealed there), never shown again or kept in a proposal.
  function keyForm() {
    const input = el("input", { type: "password", id: "yt-key", autocomplete: "off", placeholder: "YouTube Data API key", "aria-label": "YouTube API key" });
    return el("div", { class: "yt-key" },
      el("p", {}, "Search needs a free YouTube Data API key of your own: in Google Cloud Console make a project, turn on " +
        "“YouTube Data API v3”, then Credentials → Create API key. A pasted YouTube link plays without one."),
      el("div", { class: "row-buttons" }, input, btn("Save Key", "btn-amber", async () => {
        try { say((await MIA.youtubeKey(input.value)).said); page = await MIA.music(); ytNeedsKey = false; draw(); }
        catch (e) { say(e.message); }
      })));
  }

  async function newPlaylist() {
    const v = await form("New Playlist", [{ name: "name", label: "Name", type: "text", required: true, options: [], default: null }], {});
    if (v) act({ kind: "playlist.add", params: v });
  }
  async function rename(p) {
    const v = await form("Rename " + p.name, [{ name: "name", label: "Name", type: "text", required: true, options: [], default: p.name }], {});
    if (v) act({ kind: "playlist.rename", params: { playlist_id: p.id, name: v.name } });
  }

  function songRows(ids, extra) {
    if (!ids.length) return el("p", { class: "empty" }, "No songs here.");
    return el("div", { class: "mu-rows" }, ids.map((id, i) => {
      const t = byId(id);
      const playing = now.track === id;
      // The canvas's song row: tap it to play; title and artist, its length on the right; the one playing in cyan.
      return el("div", { class: "music-row" + (playing ? " playing" : ""), "data-id": id },
        el("button", { type: "button", class: "mu-song", "aria-label": "Play " + t.title, onclick: () => play(ids, i) },
          el("span", { class: "mu-titles" }, el("span", { class: "mu-title" }, t.title), el("span", { class: "mu-artist" }, [t.artist, t.album].filter(Boolean).join(" · "))),
          el("span", { class: "mu-len" }, t.duration || "")),
        extra ? extra(t) : null);
    }));
  }

  const VIEWS = {
    songs: () => {
      const q = query.toLowerCase().split(/\s+/).filter(Boolean);
      const ids = page.tracks.filter((t) => q.every((w) => (t.title + " " + t.artist + " " + t.album + " " + t.genre).toLowerCase().includes(w))).map((t) => t.id);
      const search = el("input", { type: "search", class: "journal-search", placeholder: "Search songs, artists, albums…", value: query, "aria-label": "Search music",
        oninput: (ev) => { query = ev.target.value; const pos = ev.target.selectionStart; draw(); const box = document.querySelector(".journal-search"); box.focus(); box.setSelectionRange(pos, pos); } });
      return section("Songs", buttons(ids.length ? btn("Play All", "btn-green", () => play(ids)) : null,
          btn("Upload Songs", "btn-amber", uploadSongs)), search,
        songRows(ids, (t) => buttons(el("button", { type: "button", class: "btn btn-ghost btn-small mu-add", "aria-label": "Add " + t.title + " to a playlist",
          onclick: () => toPlaylist(t) }, "+"),
          byId(t.id).uploaded ? btn("Delete", "btn-ghost btn-small", () => act({ kind: "track.delete", params: { track_id: t.id } })) : null)));
    },
    playlists: () => {
      const p = openList && page.playlists.find((x) => x.id === openList);
      if (p) return [el("p", {}, el("a", { href: "#", onclick: (ev) => { ev.preventDefault(); openList = null; draw(); } }, "‹ All Playlists")),
        section(p.name, buttons(p.track_ids.length ? btn("Play", "btn-green", () => play(p.track_ids)) : null,
            btn("Rename", "btn-ghost", () => rename(p)), btn("Delete", "btn-ghost", () => act({ kind: "playlist.delete", params: { playlist_id: p.id } }))),
          songRows(p.track_ids, (t) => buttons(btn("Remove", "btn-ghost btn-small", () => act({ kind: "playlist.remove_track", params: { playlist_id: p.id, track_id: t.id } })))))];
      return section("Playlists", btn("New Playlist", "btn-amber", newPlaylist),
        page.playlists.length ? el("div", { class: "rows" }, page.playlists.map((x) => el("div", { class: "row money-row" },
          el("div", {}, el("div", { class: "row-title" }, x.name), el("div", { class: "row-sub" }, x.track_ids.length + (x.track_ids.length === 1 ? " song" : " songs"))),
          buttons(x.track_ids.length ? btn("Play", "btn-green btn-small", () => play(x.track_ids)) : null, btn("Open", "btn-ghost btn-small", () => { openList = x.id; draw(); })))))
          : el("p", { class: "empty" }, "No playlists yet."));
    },
    youtube: () => {
      const saved = page.tracks.filter((t) => t.youtube);
      const go = async () => {
        ytWords = ($("yt-q") || {}).value || "";
        ytProblem = ""; ytNeedsKey = false;
        const link = /youtu\.?be/.test(ytWords) ? ytWords.match(/(?:v=|youtu\.be\/|shorts\/|embed\/)([A-Za-z0-9_-]{11})/) : null;
        if (link) { ytFound = [{ video_id: link[1], title: "", channel: "", shown: "The song from your link" }]; draw(); return; }
        if (!ytWords.trim()) return;
        say("Looking on YouTube…");
        try {
          const got = await MIA.youtubeSearch(ytWords);
          ytFound = got.songs; ytProblem = got.problem; ytNeedsKey = got.needs_key;
        } catch (e) { ytFound = []; ytProblem = e.message; }
        draw();
      };
      const box = el("input", { type: "search", id: "yt-q", class: "journal-search", placeholder: "Search YouTube, or paste a YouTube link…",
        value: ytWords, "aria-label": "Search YouTube", onkeydown: (ev) => { if (ev.key === "Enter") go(); } });
      const pick = page.youtube_next && byId(page.youtube_next.track_id);
      const results = ytFound === null ? null : (ytFound.length ? el("div", { class: "rows" }, ytFound.map((s) => el("div", { class: "row money-row yt-row" },
        s.thumb ? el("img", { src: s.thumb, alt: "", class: "yt-thumb", loading: "lazy" }) : null,
        el("div", {}, el("div", { class: "row-title" }, s.title || s.shown), el("div", { class: "row-sub" }, s.channel || "YouTube")),
        buttons(btn("Play", "btn-green btn-small", () => ytPlay([s])),
          btn("Save", "btn-ghost btn-small", () => act({ kind: "youtube.save", params: { video: s.video_id, title: s.title, channel: s.channel } })),
          page.playlists.length ? btn("+ Playlist", "btn-ghost btn-small", () => saveTo(s)) : null))))
        : el("p", { class: "empty" }, ytProblem || "Nothing found."));
      return [
        pick ? section("MIA's Pick", btn("Play", "btn-green", () => play([pick.id])),
          el("p", {}, pick.title + (pick.artist ? " · " + pick.artist : ""))) : null,
        section("YouTube", btn("Search", "btn-green", go), box, results,
          ytNeedsKey || !page.youtube_key ? keyForm() : null,
          el("p", { class: "dim music-library" }, "Songs play in YouTube's own player and are saved as links; nothing is downloaded.")),
        section("Saved From YouTube", saved.length ? btn("Play All", "btn-green", () => play(saved.map((t) => t.id))) : null,
          saved.length ? songRows(saved.map((t) => t.id), (t) => buttons(el("button", { type: "button", class: "btn btn-ghost btn-small mu-add",
            "aria-label": "Add " + t.title + " to a playlist", onclick: () => toPlaylist(t) }, "+"),
            btn("Remove", "btn-ghost btn-small", () => act({ kind: "track.delete", params: { track_id: t.id } }))))
            : el("p", { class: "empty" }, "Songs you save from YouTube show here and can go on any playlist.")),
      ].filter(Boolean);
    },
    // His songbook (core/repertoire.py): the songs he can play all the way through, which count toward the Songbook
    // achievements and missions. Taking one back is "undo that". Play Along: the saved YouTube song named like it.
    canplay: () => {
      const add = async () => {
        const v = await form("I Learned A Song", [
          { name: "song", label: "The song", type: "text", required: true, options: [], default: null },
          { name: "instrument", label: "On", type: "choice", required: true, options: page.instruments, default: "guitar" },
          { name: "artist", label: "Who it's by", type: "text", required: false, options: [], default: null }], {});
        if (v) act({ kind: "song.learned", params: v });
      };
      return section("Songs I Can Play", btn("I Learned A Song", "btn-amber", add),
        page.songbook.length ? el("div", { class: "rows" }, page.songbook.map((s) => el("div", { class: "row money-row" },
          el("div", {}, el("div", { class: "row-title" }, "🎵 " + s.song), el("div", { class: "row-sub" },
            [s.artist, s.instrument, s.when ? new Date(s.when).toLocaleDateString() : ""].filter(Boolean).join(" · "))),
          s.play_along ? btn("Play Along", "btn-ghost btn-small", () => play([s.play_along])) : null)))
          : el("p", { class: "empty" }, "When you can play a song all the way through, add it here: each one counts toward your Songbook achievements."));
    },
    artists: () => {
      if (artist) {
        const ids = page.tracks.filter((t) => (t.artist || "Unknown artist") === artist).map((t) => t.id);
        return [el("p", {}, el("a", { href: "#", onclick: (ev) => { ev.preventDefault(); artist = null; draw(); } }, "‹ All Artists")),
          section(artist, btn("Play All", "btn-green", () => play(ids)), songRows(ids))];
      }
      return section("Artists", null, page.artists.length ? el("div", { class: "rows" }, page.artists.map((a) => el("div", { class: "row money-row" },
        el("div", {}, el("div", { class: "row-title" }, a.name), el("div", { class: "row-sub" }, a.count + (a.count === 1 ? " song" : " songs"))),
        buttons(btn("Open", "btn-ghost btn-small", () => { artist = a.name; draw(); })))))
        : el("p", { class: "empty" }, "No artists yet."));
    },
  };

  function draw() {
    const lib = page.library;
    $("strip").replaceChildren(
      el("div", { class: "cell ok" }, el("span", { class: "n" }, lib.count), el("span", { class: "t" }, "Songs")),
      el("div", { class: "cell ok" }, el("span", { class: "n" }, page.playlists.length), el("span", { class: "t" }, "Playlists")),
      el("div", { class: "cell ok" }, el("span", { class: "n" }, lib.minutes), el("span", { class: "t" }, "Minutes")));
    $("tabs").hidden = false;
    $("tabs").replaceChildren(...TABS.map(([id, l]) => el("button", { type: "button", role: "tab", "aria-selected": String(id === tab),
      onclick: () => { tab = id; history.replaceState(null, "", "#" + id); draw(); } }, l)));
    const empty = !lib.count ? section("Your Music Library", buttons(btn("Upload Songs", "btn-amber", uploadSongs),
        btn("Scan Library", "btn-ghost", () => act({ kind: "music.scan", params: {} }))),
      el("p", { class: "music-library" }, "Upload songs (mp3, m4a, flac…) from this device's files" +
        (lib.found ? ", or put them in MIA's music folder and Scan Library." : ". On the PC you can also point MIA at your music folder in Settings.")),
      phoneAsks() ? buttons(btn("Find The Songs On This Phone", "btn-amber", () => window.MIAPhonePermissions.ask("music"))) : null,
      !lib.found && lib.folder ? el("p", { class: "dim music-library" }, "Looking in: " + lib.folder) : null) : null;
    const free = tab === "youtube" || tab === "canplay";  // these need no library of files
    $("panel").replaceChildren(...[free ? null : empty, ...[].concat(lib.count || free ? VIEWS[tab]() : []),
      lib.count ? el("p", { class: "dim music-library" }, "Library: " + lib.folder + " · ", el("a", { href: "#", onclick: (ev) => { ev.preventDefault(); act({ kind: "music.scan", params: {} }); } }, "Scan For New Music")) : null].filter(Boolean));
  }

  MIAShell.start(async () => {
    page = await MIA.music();
    if (!page.available) {
      $("panel").replaceChildren(el("p", { class: "empty" }, "Music isn't set up on this MIA."));
      return;
    }
    if (!$("player")) $("panel").after(el("section", { class: "glass music-player", id: "player", "aria-label": "Now playing", hidden: true }));
    drawPlayer();
    draw();
  });
})();
