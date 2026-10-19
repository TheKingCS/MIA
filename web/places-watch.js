/*
 * places-watch.js — location quests (claude, 2026-10-17, DEC-0028 #13).
 * When the person switched them on (Settings → Location quests), MIA.shell()
 * lists their places; while MIA is open this watches the device's position
 * and compares it here, on the device. Nothing about where you are is sent
 * anywhere. Arriving at a place asks first ("You're at Gym. Your workout's
 * ready."); yes records the arrival (place.arrive, which also clears the
 * world map's fog there) and opens the place's screen. Once per place per
 * six hours.
 */
(function () {
  "use strict";
  const QUIET_HOURS = 6;
  let places = [], watchId = null, asking = false;

  const store = {
    get(k) { try { return localStorage.getItem(k); } catch (e) { return null; } },
    set(k, v) { try { localStorage.setItem(k, v); } catch (e) { /* fine */ } },
  };

  // Great-circle distance in meters (core/places.distance_m does the same).
  function meters(a, b, c, d) {
    const R = 6371008.8, r = Math.PI / 180;
    const x = Math.sin((c - a) * r / 2) ** 2 + Math.cos(a * r) * Math.cos(c * r) * Math.sin((d - b) * r / 2) ** 2;
    return 2 * R * Math.asin(Math.sqrt(x));
  }

  function recent(place) {
    const at = Number(store.get("mia.place." + place.id) || 0);
    return Date.now() - at < QUIET_HOURS * 3600 * 1000;
  }

  // Yes to a place: record the arrival and open its screen.
  async function arrive(place) {
    try {
      const p = await MIA.propose("place.arrive", { place_id: place.id });
      await MIA.approve(p.proposal_id);  // the person just said yes
      if (window.MIASound) MIASound.play("chime");
    } catch (e) { /* the screen still opens */ }
    if (window.MIAPlaces.onArrive) window.MIAPlaces.onArrive(place);  // the glasses show it in place
    else if (place.open) location.href = place.open;
  }

  function ask(place) {
    asking = true;
    store.set("mia.place." + place.id, String(Date.now()));
    const dialog = document.createElement("dialog");
    dialog.className = "confirm place-arrival";
    dialog.setAttribute("aria-label", "You're at " + place.name);
    const head = document.createElement("h3");
    head.textContent = "📍 " + place.name;
    const text = document.createElement("p");
    text.textContent = place.say.replace(/^📍 You're at [^.]*\.\s*/, "") || "You're here.";
    const row = document.createElement("div");
    row.className = "confirm-actions";
    const go = document.createElement("button");
    go.type = "button"; go.className = "btn btn-amber"; go.textContent = place.label;
    const no = document.createElement("button");
    no.type = "button"; no.className = "btn btn-ghost"; no.textContent = "Not Now";
    row.append(go, no);
    dialog.append(head, text, row);
    const close = () => { dialog.close(); dialog.remove(); asking = false; };
    no.onclick = close;
    dialog.oncancel = (e) => { e.preventDefault(); close(); };
    go.onclick = () => { close(); arrive(place); };
    document.body.append(dialog);
    dialog.showModal();
    go.focus();
  }

  function check(pos) {
    // Not on My Places itself: you're standing at the place you just added.
    if (asking || /places\.html$/.test(location.pathname)) return;
    const { latitude, longitude, accuracy } = pos.coords;
    const slack = Math.min(accuracy || 0, 100);
    const here = places.find((p) => !recent(p) && meters(latitude, longitude, p.lat, p.lon) <= p.radius + slack);
    if (here) ask(here);
  }

  // The phone app watches them while MIA is closed too (Places.kt): Android's
  // own alerts, a notification on arrival; tapping it opens ?arrive=<id>.
  const native = window.MIAPhonePlaces || null;
  function handOver() {
    if (!native) return;
    try {
      native.watch(JSON.stringify(places.map((p) => ({ id: p.id, name: p.name, lat: p.lat, lon: p.lon,
        radius: p.radius, say: p.say }))));
    } catch (e) { /* an older app: only while open */ }
  }
  function arrivedFromNotification() {
    const id = new URLSearchParams(location.search).get("arrive");
    if (!id) return;
    history.replaceState(null, "", location.pathname + location.hash);
    const place = places.find((p) => p.id === id);
    if (!place) return;
    store.set("mia.place." + place.id, String(Date.now()));
    arrive(place);  // they tapped "You're at Gym": that's their yes
  }

  function configure(list) {
    places = Array.isArray(list) ? list : [];
    handOver();
    arrivedFromNotification();
    if (!places.length || !navigator.geolocation) {
      if (watchId !== null) { navigator.geolocation.clearWatch(watchId); watchId = null; }
      return;
    }
    if (watchId === null) {
      watchId = navigator.geolocation.watchPosition(check, () => {}, { enableHighAccuracy: true, maximumAge: 30000, timeout: 30000 });
    }
  }

  // "on" | "notify" | "foreground" | "off" (Places.kt), or "" off the phone app.
  function background() {
    try { return native ? String(native.background()) : ""; } catch (e) { return ""; }
  }
  function askBackground() { if (native) native.askBackground(); }

  window.MIAPlaces = { configure, meters, onArrive: null, background, askBackground, backgroundChanged: null };
})();
