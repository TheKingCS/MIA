/*
 * mia.js — the engine client every MIA surface shares (Phase 2, DEC-0012).
 *
 * The ONLY place the web front end talks to MIA's engine. Screens call
 * these functions and render what comes back; they never compute facts,
 * totals or permissions themselves (DEC-0004, DEC-0013).
 *
 *   MIA.state()                 -> Life State v2 (docs/schema/life_state.schema.json)
 *   MIA.propose(kind, params)   -> a proposal (docs/schema/action.schema.json)
 *   MIA.approve(id) / reject(id) / undo(id)
 *   MIA.onChange(callback)      -> calls back whenever MIA's data changes
 *   MIA.talk(text)              -> one Assistant turn: {replies, reply_text, draft, ...}
 *   MIA.voice(wavBlob)          -> the same, spoken (mono 16-bit WAV): {transcript, reply_text, audio_wav_base64}
 *   MIA.shell()                 -> the sidebar: the person's apps, level and XP (core/web_surfaces.py)
 *   MIA.dashboard()             -> the Dashboard: greeting, Today's Focus, glance cards
 *   MIA.apps()                  -> every app, grouped, with what MIA can do in each
 *   MIA.money(strategy)         -> the Money screen: bills, income, expenses, debts, budgets, trends
 *   MIA.kitchen() / MIA.workout() / MIA.realEstate() -> those screens (core/web_screens.py)
 *   MIA.missions() / MIA.skills() / MIA.character() -> those screens (core/web_progress.py)
 *   MIA.equipment(scope)        -> Garage / Property / Greenhouse / Maintenance
 *   MIA.asset(id)               -> one asset's page (tasks, stats, missions, documents, costs, history)
 *   MIA.download(path) / MIA.upload(path, file) -> files (an asset's documents)
 *   MIA.demo                    -> true when showing the placeholder example
 *
 * Sign-in: the desktop opens this page with #token=... (its own session);
 * on the phone, MIA.signIn(email, password). The token is kept for this
 * tab only. With ?demo (always, on the public GitHub Pages preview), it
 * reads the published placeholder example instead, and actions are
 * disabled.
 * No dependencies, no network beyond MIA itself (offline-first).
 */
(function () {
  "use strict";

  const params = new URLSearchParams(location.search);
  // The public preview on GitHub Pages has no MIA behind it: placeholder data only.
  const demo = params.has("demo") || location.hostname.endsWith(".github.io");
  const fromHash = new URLSearchParams(location.hash.slice(1)).get("token");
  if (fromHash) {
    try { sessionStorage.setItem("mia.token", fromHash); } catch (e) { /* private mode */ }
    history.replaceState(null, "", location.pathname + location.search);
  }
  // The person's look, passed by the desktop (text size, high contrast).
  if (params.get("scale")) document.documentElement.style.setProperty("--scale", params.get("scale"));
  if (params.get("contrast") === "high") document.documentElement.dataset.contrast = "high";

  let token = fromHash;
  if (!token) {
    try { token = sessionStorage.getItem("mia.token"); } catch (e) { token = null; }
  }

  class MiaError extends Error {
    constructor(status, message) { super(message); this.status = status; }
  }

  async function call(method, path, body) {
    if (!token) throw new MiaError(401, "Not signed in.");
    const response = await fetch(path, {
      method,
      headers: Object.assign({ Authorization: "Bearer " + token },
                             body ? { "Content-Type": "application/json" } : {}),
      body: body ? JSON.stringify(body) : undefined,
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new MiaError(response.status, data.detail || response.statusText);
    return data;
  }

  // A read: the engine, or in the demo its published placeholder example.
  function read(path, example) {
    // no-cache: the preview's examples change when a screen is added; never show a stale copy.
    if (demo) return fetch(new URL("../schema/" + example + ".example.json", location.href), { cache: "no-cache" })
      .then((r) => r.json());
    return call("GET", path);
  }

  function demoOnly() { return Promise.reject(new MiaError(400, "Actions are off in the demo.")); }

  function onChange(callback) {
    if (demo || !token) return () => {};
    let version = -1, source = null, timer = null, closed = false;
    function connect() {
      if (closed) return;
      source = new EventSource("/api/live?token=" + encodeURIComponent(token) + "&since=" + version);
      source.addEventListener("state", (event) => {
        const next = JSON.parse(event.data).version;
        const first = version === -1;
        version = next;
        if (!first) callback(next);
      });
      source.onerror = () => {
        source.close();
        timer = setTimeout(connect, 3000); // MIA restarting, or the network blinked
      };
    }
    connect();
    return () => { closed = true; if (source) source.close(); clearTimeout(timer); };
  }

  // The phone (and any browser): sign in with the person's email (or
  // name) and password, the same as the phone app (POST /api/login).
  async function signIn(who, password) {
    const response = await fetch("/api/login", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ profile_id: who, password: password }),
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new MiaError(response.status, data.detail || "Couldn't sign in.");
    token = data.token;
    try { sessionStorage.setItem("mia.token", token); } catch (e) { /* this tab only */ }
    window.MIA.signedIn = true;
    return data;
  }

  window.MIA = {
    demo,
    signIn,
    signedIn: Boolean(token) || demo,
    MiaError,
    state: () => read("/api/state", "life_state"),
    shell: () => read("/api/shell", "shell"),
    dashboard: () => read("/api/dashboard", "dashboard"),
    apps: () => read("/api/apps", "apps"),
    kitchen: () => read("/api/kitchen", "kitchen"),
    workout: () => read("/api/workout", "workout"),
    realEstate: () => read("/api/real-estate", "real_estate"),
    missions: () => read("/api/missions", "missions"),
    skills: () => read("/api/skills", "skills"),
    character: () => read("/api/character", "character"),
    equipment: (scope) => read("/api/equipment?scope=" + encodeURIComponent(scope || "maintenance"), "equipment_" + (scope || "maintenance")),
    asset: (id) => read("/api/assets/" + encodeURIComponent(id), "asset"),
    // A stored file (an asset's document) as a Blob, with this tab's sign-in.
    download: async (path) => {
      if (demo) throw new MiaError(400, "Documents need MIA running — this is the placeholder demo.");
      if (!token) throw new MiaError(401, "Not signed in.");
      const response = await fetch(path, { headers: { Authorization: "Bearer " + token } });
      if (!response.ok) throw new MiaError(response.status, (await response.json().catch(() => ({}))).detail || response.statusText);
      return response.blob();
    },
    // Send a file (raw body + X-Filename), e.g. a manual onto an asset.
    upload: (path, file) => demo ? demoOnly() : (async () => {
      if (!token) throw new MiaError(401, "Not signed in.");
      const response = await fetch(path, { method: "POST", body: file,
        headers: { Authorization: "Bearer " + token, "X-Filename": encodeURIComponent(file.name) } });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new MiaError(response.status, data.detail || response.statusText);
      return data;
    })(),
    money: (strategy) => read("/api/money" + (strategy ? "?strategy=" + encodeURIComponent(strategy) : ""), "money"),
    kinds: () => call("GET", "/api/actions/kinds"),
    pending: () => call("GET", "/api/actions"),
    propose: (kind, params) => demo ? demoOnly() : call("POST", "/api/actions/propose", { kind, params: params || {} }),
    approve: (id) => demo ? demoOnly() : call("POST", "/api/actions/" + id + "/approve"),
    reject: (id) => demo ? demoOnly() : call("POST", "/api/actions/" + id + "/reject"),
    undo: (id) => demo ? demoOnly() : call("POST", "/api/actions/" + id + "/undo"),
    onChange,
    // Talk (H-0009's TODO for claude): one Assistant turn, the same
    // engine path as the phone's chat (POST /api/voice/text). Any change
    // MIA makes in a turn is recorded and undoable like everything else.
    // Voice (the phone's path): a mono 16-bit WAV in, MIA's reply (and her
    // spoken reply as WAV, when voice is set up on her computer) out.
    voice: (wavBlob) => demo ? Promise.reject(new MiaError(400, "Voice needs MIA running — this is the placeholder demo."))
      : (async () => {
        if (!token) throw new MiaError(401, "Not signed in.");
        const response = await fetch("/api/voice/turn", { method: "POST", body: wavBlob,
          headers: { Authorization: "Bearer " + token, "Content-Type": "audio/wav" } });
        const data = await response.json().catch(() => ({}));
        if (!response.ok) throw new MiaError(response.status, data.detail || response.statusText);
        return data;
      })(),
    talk: (text) => demo ? Promise.reject(new MiaError(400, "Talk needs MIA running — this is the placeholder demo."))
                         : call("POST", "/api/voice/text", { text }),
  };
})();
