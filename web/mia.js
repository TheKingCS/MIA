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
 *   MIA.journal() / workshop() / expeditions() / music() / files(folder)
 *                               -> those screens (core/web_more.py); a song plays from
 *                                  /api/music/track/<id>/audio, a file opens from /api/files/file?path=
 *   MIA.calendar(month)         -> everything with a date: Past Due, Today, Due Soon, a month (core/calendar_view.py)
 *   MIA.glasses() / glassesPanel(app, item) -> the glasses' app cards and a quick action's panel
 *   MIA.money(strategy)         -> the Money screen: bills, income, expenses, debts, budgets, trends
 *   MIA.kitchen() / MIA.workout() / MIA.realEstate() -> those screens (core/web_screens.py)
 *   MIA.missions() / MIA.skills() / MIA.character() -> those screens (core/web_progress.py)
 *   MIA.profile() / MIA.settings() -> the gear's screens (core/web_account.py)
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

  const DEMO_THREAD = [  // placeholder words for the demo's conversation log
    { role: "user", content: "Hey MIA, what's on today?" },
    { role: "assistant", content: "This is the demo, so here's a placeholder: two things on the calendar and one mission step." },
    { role: "user", content: "Remind me about the step at lunch." },
    { role: "assistant", content: "Placeholder answer: with MIA running, the whole conversation you've had shows here, and it's the same one on your phone and computer." },
  ];
  const DEMO_BOOT = { done: false, phase: "awakening", beats: [  // the shape of /api/first-boot
    { look: "swarm", say: "A new connection is forming…", seconds: 7, phase: "awakening" },
    { look: "flare", say: "", seconds: 5, phase: "awakening" },
    { look: "core", say: "", seconds: 6, phase: "connecting" },
    { look: "voice", say: "Hello.", seconds: 4, speak: true, phase: "introduction" },
    { look: "voice", say: "I'm MIA, your Multifunctional Intelligent Assistant.", seconds: 6, speak: true, phase: "introduction" },
    { look: "voice", say: "I'm here to help you organize your life, reach your goals, and make the most of every day.", seconds: 9, speak: true, phase: "introduction" },
    { look: "voice", say: "Next, I'd like to get to know you.", seconds: 6, speak: true, phase: "introduction" },
  ] };
  class MiaError extends Error {
    constructor(status, message) { super(message); this.status = status; }
  }

  // The shape of /api/user-sync, for trying the screen with ?demo&sync.
  const DEMO_SYNC = { active: true, begun: true, offer: false, done: false, paused: false, topic: "meals", title: "Meals", number: 1, topics: 1, step: "ask",
    question: "What do you usually eat on weeknights?", heard: "", chips: [], percent: 0, say: "" };
  const DEMO_REVIEW = Object.assign({}, DEMO_SYNC, { step: "review", question: "Here's what I've got. Does that look right?", percent: 50,
    heard: "Chicken and rice, sometimes tacos. I meal prep on Sundays.",
    chips: [{ app: "Recipe book", text: "Chicken and rice" }, { app: "Recipe book", text: "Tacos" }, { app: "Missions", text: "Sunday meal prep" }] });
  const DEMO_PHONE = Object.assign({}, DEMO_SYNC, { step: "phone", title: "Your phone", number: 1, question: "First, your phone. Tap Allow on it for each of these.",
    rows: [{ id: "microphone", label: "Microphone", status: "allowed" }, { id: "notifications", label: "Notifications", status: "allowed" },
      { id: "location", label: "Location", status: "not yet" }, { id: "photos", label: "Photos", status: "waiting" }, { id: "glasses", label: "Glasses", status: "waiting" }] });
  const DEMO_NEXT = Object.assign({}, DEMO_SYNC, { step: "next", question: "Next is work. Keep going, or finish later?", percent: 14 });
  const demoSync = () => ({ review: DEMO_REVIEW, phone: DEMO_PHONE, next: DEMO_NEXT })[params.get("sync")] || DEMO_SYNC;
  // The shape of /api/welcome, for trying the screens with ?demo&welcome=mission, home, apps, tour or explore.
  const DEMO_MISSION = { name: "Know your system", summary: "Learn MIA by using her. Finishing this tour is your first completed mission.", xp: 100, percent: 25,
    objectives: [{ text: "Meet MIA", done: true }, { text: "Tour your Home", done: false }, { text: "Explore the app menu", done: false }, { text: "Talk to MIA on your own", done: false }] };
  const DEMO_PLAYING = { track: "demo", number: 2, total: 12, playing: true, seconds: 74, length: 212 };
  const DEMO_TILES = ["Missions", "Calendar", "Kitchen", "Workout"];
  const demoWelcome = () => {
    const stage = params.get("welcome");
    const out = { stage, paused: false, left: true, ready: false, mission: DEMO_MISSION, tour: null, apps: [], ideas: [] };
    if (stage === "home") out.tour = { app: "home", name: "Home", number: 1, of: 4, text: "Your missions live here: real goals broken into steps, each worth XP. Your first one is already running.",
      tiles: DEMO_TILES.map((label, i) => ({ label, on: i === 0 })) };
    if (stage === "tour") out.tour = { app: "kitchen", name: "Kitchen", number: 2, of: 4, text: "What's planned to eat today.",
      tiles: ["Recipes", "Today's Meal Plan", "My Pantry", "Grocery List"].map((label, i) => ({ label, on: i === 1 })) };
    if (stage === "apps") out.apps = [["budget", "Budget", "Tour ready", "Spending, bills and savings goals.", ["Save for a van is on your missions, from earlier."]],
      ["missions", "Missions", "Tour done", "Your goals, broken into steps, each worth XP.", []], ["workout", "Workout", "Paused · step 2", "Your training plan, what's on today and how it's going.", []],
      ["kitchen", "Kitchen", "Tour ready", "Your recipes, your pantry, and what's for dinner.", []]].map(([id, name, status, what, yours]) => ({ id, name, status, intro: { what, yours } }));
    if (stage === "explore") out.ideas = [{ label: "Plan my week", say: "" }, { label: "Set a goal", say: "" }, { label: "Just talk", say: "" }];
    return out;
  };
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

  const images = {};

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

  // The phone's first start: does this device still need its first
  // account? Then make it, signed in (POST /api/setup; the phone app only).
  async function setupStatus() {
    if (demo) return { needed: false };
    try {
      const response = await fetch("/api/setup");
      return response.ok ? await response.json() : { needed: false };
    } catch (e) { return { needed: false }; }
  }
  async function setup(details) {
    const response = await fetch("/api/setup", {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(details),
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new MiaError(response.status, data.detail || "Couldn't make your account.");
    token = data.token;
    try { sessionStorage.setItem("mia.token", token); } catch (e) { /* this tab only */ }
    window.MIA.signedIn = true;
    return data;
  }

  // The account menu's "Log out": ends the session here and forgets it.
  async function signOut() {
    if (token && !demo) {
      await fetch("/api/logout", { method: "POST", headers: { Authorization: "Bearer " + token } }).catch(() => {});
    }
    token = null;
    try { sessionStorage.removeItem("mia.token"); } catch (e) { /* this tab only */ }
    window.MIA.signedIn = false;
  }

  window.MIA = {
    demo,
    signIn,
    signOut,
    setupStatus,
    setup,
    signedIn: Boolean(token) || demo,
    MiaError,
    state: () => read("/api/state", "life_state"),
    shell: () => read("/api/shell", "shell"),
    dashboard: () => read("/api/dashboard", "dashboard"),
    apps: () => read("/api/apps", "apps"),
    calendar: (month) => read("/api/calendar" + (month ? "?month=" + encodeURIComponent(month) : ""), "calendar"),
    // The glasses' app cards and one menu item's panel (core/glasses.py).
    // In the demo every panel comes from one example file, keyed "app/item".
    // `mission`: the mission the glasses' Missions card shows (optional).
    glasses: (mission) => read("/api/glasses" + (mission ? "?mission=" + encodeURIComponent(mission) : ""), "glasses"),
    // Meeting MIA (core/first_boot.py): what's left. In the demo, only with ?boot.
    firstBoot: () => demo ? Promise.resolve(params.has("boot") ? DEMO_BOOT : { done: true, beats: [] }) : call("GET", "/api/first-boot"),
    // User Sync (core/user_sync.py). In the demo, only with ?sync; ?sync=review, =phone or =next starts there.
    userSync: () => demo ? Promise.resolve(params.has("sync") ? demoSync() : { done: true, offer: false, active: false }) : call("GET", "/api/user-sync"),
    userSyncStep: (step) => demo ? Promise.resolve({ ...demoSync(), say: "" }) : call("POST", "/api/user-sync", step),
    // The council (core/council.py, build plan step 16): the PC owner's only.
    council: () => demo ? Promise.resolve({ messages: [], members: [] }) : call("GET", "/api/council"),
    councilSay: (body) => demo ? Promise.resolve({}) : call("POST", "/api/council", body),
    // The Operating Journal, games played and Good News Radio (DEC-0097, 0098, 0096); changes go through actions.
    diagnostics: () => demo ? Promise.resolve({ error: "", checks: [
      { id: "pc_ready", title: "Is the PC ready for MIA?", ok: true, passed: 5, failed: [], unknown: [] },
      { id: "network", title: "The network", ok: false, passed: 2, failed: ["The wired connection is running at 100 Mb/s, under a gigabit."], unknown: [] },
      { id: "big_download", title: "Room for a big download", ok: true, passed: 2, failed: [], unknown: ["disk.D.free_gb"] }] })
      : call("GET", "/api/diagnostics"),
    lifeNotes: () => demo ? Promise.resolve({ kinds: [
      { kind: "commitment", title: "Promises", notes: [
        { id: "n1", line: "a promise to Sam: fix his gate (by Saturday)", status: "open", at: "2026-11-06", due: "2026-11-07" },
        { id: "n2", line: "a promise to my sister: call her", status: "done", at: "2026-10-30", due: "" }] },
      { kind: "decision", title: "Decisions", notes: [
        { id: "n3", line: "a decision: the metal roof, because it lasts longer", status: "open", at: "2026-11-02", due: "" }] },
      { kind: "idea", title: "Ideas", notes: [
        { id: "n4", line: "an idea: selling honey at the market", status: "open", at: "2026-11-01", due: "" }] },
      { kind: "dropped_goal", title: "Goals set aside", notes: [] }] }) : call("GET", "/api/life-notes"),
    operatingJournal: () => demo ? Promise.resolve({ lines: [], sections: {} }) : call("GET", "/api/operating-journal"),
    play: () => demo ? Promise.resolve({ played: [], weeks: [], lines: [], efforts: {} }) : call("GET", "/api/play"),
    news: () => demo ? Promise.resolve({ on: false, day: null, stories: [], personalities: [] }) : call("GET", "/api/news"),
    // Her voice saying one line; rejected where this MIA has none (the words still show).
    // Music on the glasses: the phone plays it (Music.kt), through the relay. Elsewhere, the Music screen.
    musicPlay: () => demo ? Promise.resolve(DEMO_PLAYING) : Promise.reject(new MiaError(400, "Music plays from the glasses' page.")),
    musicControl: () => demo ? Promise.resolve(DEMO_PLAYING) : Promise.reject(new MiaError(400, "Music plays from the glasses' page.")),
    musicNow: () => Promise.resolve(demo ? DEMO_PLAYING : {}),
    // The glasses' log: the thread and the conversations before it.
    history: (limit) => demo ? MIA.thread(limit) : call("GET", "/api/talk/thread?limit=" + (limit || 200) + "&earlier=1"),
    // The first mission and tours (core/welcome.py). In the demo, only with ?welcome=<stage>.
    welcome: () => demo ? Promise.resolve(params.has("welcome") ? demoWelcome() : { stage: "none", left: false }) : call("GET", "/api/welcome"),
    welcomeStep: (step) => demo ? Promise.resolve(demoWelcome()) : call("POST", "/api/welcome", step),
    speak: (text) => demo ? demoOnly() : call("POST", "/api/heavy/speak", { text }),
    // What her orb is doing (core/glasses_feed.py), polled while the glasses are on.
    glassesOrb: () => demo ? Promise.resolve({ state: "idle" }) : call("GET", "/api/glasses/orb"),
    glassesPanel: (app, item, mission) => demo
      ? read("", "glasses_panels").then((all) => all[app + "/" + item] || Promise.reject(new MiaError(404, "No such menu item.")))
      : call("GET", "/api/glasses/" + encodeURIComponent(app) + "/" + encodeURIComponent(item) +
             (mission ? "?mission=" + encodeURIComponent(mission) : "")),
    // The Heads-Up screen's new cards since `since` (core/glasses_feed.py). In the
    // demo, the example's cards arrive once, a few seconds after it starts.
    glassesFeed: (since) => demo
      ? read("", "glasses_feed").then((ex) => {
          const first = !since || MIA._feedShown;
          MIA._feedShown = MIA._feedShown || !!since;
          return { now: ex.now, items: first ? [] : ex.items };
        })
      : call("GET", "/api/glasses/feed" + (since ? "?since=" + encodeURIComponent(since) : "")),
    kitchen: () => read("/api/kitchen", "kitchen"),
    recipe: (id) => read("/api/kitchen/recipe/" + encodeURIComponent(id), "recipe"),
    fitness: () => read("/api/fitness", "fitness"),
    fitnessWeek: (day) => read("/api/fitness/week" + (day ? "?day=" + encodeURIComponent(day) : ""), "fitness_week"),
    workout: () => read("/api/workout", "workout"),
    realEstate: () => read("/api/real-estate", "real_estate"),
    missions: () => read("/api/missions", "missions"),
    skills: () => read("/api/skills", "skills"),
    character: () => read("/api/character", "character"),
    profile: () => read("/api/profile", "profile"),
    modelTest: () => demo ? Promise.resolve({ available: false, models: [] }) : call("GET", "/api/model-test"),
    modelStep: (step, body) => demo ? demoOnly() : call("POST", "/api/model-test/" + step, body || {}),
    settings: () => read("/api/settings", "settings"),
    // Not actions: a password never sits in a proposal (server/app.py).
    changePassword: (current, next) => demo ? demoOnly() : call("POST", "/api/account/password", { current: current, new: next }),
    newRecoveryCode: (password) => demo ? demoOnly() : call("POST", "/api/account/recovery-code", { password: password }),
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
    // A stored picture (a recipe's photo) as an object URL for an <img>,
    // fetched with this tab's sign-in; null when there isn't one (or in the demo).
    image: (path) => {
      if (!path) return Promise.resolve(null);
      images[path] = images[path] || MIA.download(path).then((blob) => URL.createObjectURL(blob)).catch(() => null);
      return images[path];
    },
    // Send a file (raw body + X-Filename), e.g. a manual onto an asset.
    upload: (path, file, headers) => demo ? demoOnly() : (async () => {
      if (!token) throw new MiaError(401, "Not signed in.");
      const response = await fetch(path, { method: "POST", body: file,
        headers: Object.assign({ Authorization: "Bearer " + token, "X-Filename": encodeURIComponent(file.name) }, headers || {}) });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new MiaError(response.status, data.detail || response.statusText);
      return data;
    })(),
    inbox: () => read("/api/inbox", "inbox"),
    shop: () => read("/api/shop", "shop"),
    journal: () => read("/api/journal", "journal"),
    people: () => read("/api/people", "people"),
    business: () => read("/api/business", "business"),
    // Email drafts (core/email_drafts.py): MIA only drafts; an email goes only when Send is pressed.
    emailDrafts: () => demo ? Promise.resolve({ drafts: [], can_send: false }) : call("GET", "/api/email/drafts"),
    sendDraft: (id) => demo ? demoOnly() : call("POST", "/api/email/drafts/" + encodeURIComponent(id) + "/send"),
    discardDraft: (id) => demo ? demoOnly() : call("POST", "/api/email/drafts/" + encodeURIComponent(id) + "/discard"),
    receiptMatch: (recipeId, receipt) => demo ? demoOnly()
      : call("GET", "/api/workshop/receipt_match?recipe_id=" + encodeURIComponent(recipeId) + "&receipt=" + encodeURIComponent(receipt)),
    showoff: () => read("/api/showoff", "showoff"),
    grow: () => read("/api/grow", "grow"),
    chronicle: () => read("/api/chronicle", "chronicle"),
    worldmap: () => read("/api/worldmap", "worldmap"),
    party: () => read("/api/party", "party"),
    places: () => read("/api/places", "places"),
    security: () => read("/api/security", "security"),
    // Compliance (core/web_compliance.py, DEC-0040): tax and compliance deadlines.
    compliance: () => read("/api/compliance", "compliance"),
    // Freedom (core/freedom.py, DEC-0038): the plan, the date, progress, the shift, the builds.
    freedom: () => read("/api/freedom", "freedom"),
    // The Fix-It Log (core/failure_log.py, DEC-0049): where MIA stumbled; a page reports its own errors.
    failures: () => read("/api/failures", "failures"),
    // The development dashboard (core/work_dashboard.py): the device's owner only.
    // What MIA made (core/creations.py, DEC-0091): the list, one drawn, and making a draft from a need.
    madeList: () => demo ? Promise.resolve({ creations: [] }) : call("GET", "/api/made"),
    made: (id) => demo ? Promise.reject(new MiaError(400, "Not in the demo.")) : call("GET", "/api/made/" + encodeURIComponent(id)),
    make: (need) => demo ? demoOnly() : call("POST", "/api/made", { need }),
    madeImport: (name, csv) => demo ? demoOnly() : call("POST", "/api/made/import", { name, csv }),
    madeDry: (id) => demo ? demoOnly() : call("POST", "/api/made/" + encodeURIComponent(id) + "/dry"),
    dev: (query) => demo ? Promise.resolve({ available: false }) : call("GET", "/api/dev" + (query ? "?q=" + encodeURIComponent(query) : "")),
    pageError: (page, message) => demo || !token ? Promise.resolve(null) : call("POST", "/api/failures/page", { page, message }),
    pageOpened: (page) => demo || !token ? Promise.resolve(null) : call("POST", "/api/usage/page", { page }),
    // The Sunday check-in (core/weekly_checkin.py, DEC-0047): last week's recap, this week laid out.
    checkin: () => read("/api/checkin", "checkin"),
    // The Dungeon (core/web_dungeon.py, DEC-0046): runs, loot earned / projected / banked, bosses, hard mode.
    dungeon: () => read("/api/dungeon", "dungeon"),
    // Chickens (core/web_flock.py, DEC-0037): eggs, lay rate, feed cost per dozen, cartons.
    flock: () => read("/api/flock", "flock"),
    // The insurance check-up (core/insurance.py): policies, checks, quotes side by side.
    insurance: () => read("/api/insurance", "insurance"),
    // Passwords (core/password_vault.py): never through actions; a password comes back only from reveal.
    passwords: () => read("/api/passwords", "passwords"),
    vaultSetup: (master) => demo ? demoOnly() : call("POST", "/api/passwords/setup", { master }),
    vaultUnlock: (master, recovery, fresh) => demo ? demoOnly() : call("POST", "/api/passwords/unlock", { master, recovery, new: fresh || "" }),
    vaultLock: () => demo ? demoOnly() : call("POST", "/api/passwords/lock"),
    vaultChange: (master, fresh) => demo ? demoOnly() : call("POST", "/api/passwords/change", { master, new: fresh }),
    vaultSave: (login) => demo ? demoOnly() : call("POST", "/api/passwords/login", login),
    vaultDelete: (id) => demo ? demoOnly() : call("DELETE", "/api/passwords/login/" + encodeURIComponent(id)),
    vaultReveal: (id) => demo ? demoOnly() : call("POST", "/api/passwords/login/" + encodeURIComponent(id) + "/reveal"),
    vaultImport: (text) => demo ? demoOnly() : call("POST", "/api/passwords/import", { text }),
    // The memory vault (core/memory_vault.py): one month of photos at a time.
    vault: (month) => read("/api/vault" + (month ? "?month=" + encodeURIComponent(month) : ""), "vault"),
    vaultFreePlan: (what) => demo ? demoOnly() : call("POST", "/api/vault/free/plan", { what }),
    vaultFreeDone: (paths, what) => demo ? demoOnly() : call("POST", "/api/vault/free/done", { paths, what }),
    vaultNow: () => demo ? demoOnly() : call("POST", "/api/vault/now"),
    saveCamera: (camera) => demo ? demoOnly() : call("POST", "/api/security/camera", camera),
    // One MIA everywhere (DEC-0029): the conversation Talk continues, and a fresh one.
    thread: (limit) => demo ? Promise.resolve({ messages: limit ? DEMO_THREAD : [] })
      : call("GET", "/api/talk/thread" + (limit ? "?limit=" + limit : "")),
    homeConnect: (url, who, password) => demo ? demoOnly() : call("POST", "/api/home_pc/connect", { url, who, password }),
    homeDisconnect: () => demo ? demoOnly() : call("POST", "/api/home_pc/disconnect"),
    syncNow: () => demo ? demoOnly() : call("POST", "/api/sync/now"),
    newChat: () => demo ? Promise.resolve({ reset: true }) : call("POST", "/api/voice/reset"),
    workshop: () => read("/api/workshop", "workshop"),
    expeditions: () => read("/api/expeditions", "expeditions"),
    music: () => read("/api/music", "music"),
    files: (folder) => read("/api/files" + (folder ? "?path=" + encodeURIComponent(folder) : ""), "files"),
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
