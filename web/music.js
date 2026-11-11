/*
 * music.js — the Music screen (claude, 2026-10-16; Zac: the app only opened
 * a chat). Renders MIA.music() (core/web_more.py): Songs (search), Playlists
 * and Artists. A song plays through the shared player (player.js; Zac,
 * 2026-11-10: it has to keep playing with this page closed), so it carries
 * on in the other apps; the next one in the list follows. Playlists and
 * Scan Library are actions.
 */
(function () {
  "use strict";
  const { el, act, form, say } = MIAShell;
  const $ = (id) => document.getElementById(id);
  const TABS = [["songs", "Songs"], ["playlists", "Playlists"], ["artists", "Artists"]];
  let page = null, query = "", openList = null, artist = null;
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

  const play = (ids, start) => MIAPlayer.play(ids.map((id) => byId(id) || id), start || 0).catch((e) => say(e.message));
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
    $("panel").replaceChildren(...[empty, ...[].concat(lib.count ? VIEWS[tab]() : []),
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
