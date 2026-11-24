/*
 * youtube-player.js — YouTube popped out of Music into its own window (claude, 2026-11-24; see
 * youtube-player.html). Its address carries the songs: ?v=id,id,...&t=title. Only well-formed 11-character ids
 * are used, and the player is YouTube's privacy-enhanced embed, the one outside frame MIA's pages allow.
 */
(function () {
  "use strict";
  const params = new URLSearchParams(location.search);
  const ids = (params.get("v") || "").split(",").filter((v) => /^[A-Za-z0-9_-]{11}$/.test(v)).slice(0, 50);
  const title = (params.get("t") || "").slice(0, 150);
  const what = document.getElementById("what");
  if (!ids.length) { what.textContent = "Nothing to play."; return; }
  what.textContent = title ? "▶ " + title : "From YouTube";
  document.title = (title || "YouTube") + " — MIA";
  const frame = document.createElement("iframe");
  frame.src = "https://www.youtube-nocookie.com/embed/" + ids[0] + "?autoplay=1&rel=0&modestbranding=1" +
    (ids.length > 1 ? "&playlist=" + ids.slice(1).join(",") : "");
  frame.title = "YouTube player";
  frame.allow = "autoplay; encrypted-media; picture-in-picture";
  frame.allowFullscreen = true;
  frame.referrerPolicy = "strict-origin-when-cross-origin";
  document.getElementById("frame").append(frame);
})();
