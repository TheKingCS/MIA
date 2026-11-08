/*
 * grow.js — the old Grow page now lives in the Greenhouse (its Growing tab); this sends you there, keeping the
 * part of the page asked for. Its own file because MIA's pages run no inline script (Content-Security-Policy,
 * docs/SECURITY.md).
 */
location.replace("greenhouse.html" + (location.hash || "#growing"));
