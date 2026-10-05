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
    state: () => demo ? fetch(new URL("../schema/life_state.example.json", location.href)).then((r) => r.json()) : call("GET", "/api/state"),
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
    talk: (text) => demo ? Promise.reject(new MiaError(400, "Talk needs MIA running — this is the placeholder demo."))
                         : call("POST", "/api/voice/text", { text }),
  };
})();
