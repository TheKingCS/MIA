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
  // Shown inside MIA's desktop window (it passes ?desktop=1 once; kept for the pages after): apps that live only in
  // the PC app open there (a /desktop-open/<id> link the window catches, modules/web_home).
  let desktop = params.get("desktop") === "1";
  try {
    if (desktop) sessionStorage.setItem("mia.desktop", "1");
    else desktop = sessionStorage.getItem("mia.desktop") === "1";
  } catch (e) { /* no storage: only the first page knows */ }
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
  // Two-step sign-in (core/two_step.py): a 401 marked X-MIA-Two-Step asks for the authenticator's code (err.twoStep).
  async function signIn(who, password, code) {
    const response = await fetch("/api/login", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ profile_id: who, password: password, code: code || "" }),
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      const err = new MiaError(response.status, data.detail || "Couldn't sign in.");
      err.twoStep = !!response.headers.get("X-MIA-Two-Step");
      throw err;
    }
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
    desktop,  // inside MIA's desktop window: PC-only apps open there
    signIn,
    signOut,
    setupStatus,
    setup,
    signedIn: Boolean(token) || demo,
    MiaError,
    state: () => read("/api/state", "life_state"),
    shell: () => read("/api/shell", "shell"),
    health: () => read("/api/health", "health"),
    nexus: () => read("/api/nexus", "nexus"),
    themes: () => read("/api/themes", "themes"),  // the Theme Studio (DEC-0136)
    designTheme: (description) => demo ? demoOnly() : call("POST", "/api/themes/design", { description }),
    mixThemes: (first, second, parts) => demo ? demoOnly() : call("POST", "/api/themes/mix", { first, second, parts }),  // Mix Two
    art: () => read("/api/art", "art"),  // MIA's paintings (DEC-0140)
    directions: () => read("/api/directions", "directions"),  // My Directions (DEC-0141)
    answers: () => read("/api/answers", "answers"),  // How MIA Answers (DEC-0138)
    about: () => read("/api/about", "about"),  // About MIA (DEC-0142)
    trailMaps: () => read("/api/trail-maps", "trail_maps"),  // Trail Maps (core/web_trails.py)
    trailMapFetch: (park, state, url, notes) => demo ? demoOnly() : call("POST", "/api/trail-maps/fetch", { park, state, url, notes: notes || "" }),
    worlds: (campaign) => read("/api/worlds" + (campaign ? "?campaign=" + encodeURIComponent(campaign) : ""), "worlds"),  // Living Worlds (DEC-0134)
    // After a reply in Talk, now and then: the same answer a second way to pick from ({} when none; never in the demo).
    compareAnswer: (reply, isPrivate) => demo ? Promise.resolve({}) : call("POST", "/api/talk/compare", { reply, private: !!isPrivate }),
    paint: (description, use, apply) => demo ? demoOnly() : call("POST", "/api/art/paint", { description, use: use || "backdrop", apply: !!apply }),
    // The ID wallet (core/id_wallet.py): numbers travel only in these calls, never in an action.
    wallet: () => read("/api/wallet", "wallet"),
    walletCard: (id) => demo ? read("", "wallet").then((d) => ({ ...d.cards.find((c) => c.id === id), number: "D1234-5678-9012" })) : call("GET", "/api/wallet/" + encodeURIComponent(id)),
    walletSave: (id, card) => demo ? demoOnly() : call(id ? "PUT" : "POST", "/api/wallet" + (id ? "/" + encodeURIComponent(id) : ""), card),
    communications: () => read("/api/communications", "communications"),
    hub: (area) => demo ? read("", "hub").then((d) => ({ ...d, ...(d.by_area[area] || d.by_area.home) })) : call("GET", "/api/hub/" + encodeURIComponent(area)),
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
    maps: () => demo ? Promise.resolve({ center: { lat: 40.005, lon: -105.0 }, zoom: 13, max_zoom: 16, osm_max_zoom: 4, vector: [],
      waypoints: [{ id: "w1", name: "Spring", category: "Water", lat: 40.01, lon: -105.0 },
                  { id: "w2", name: "Trailhead", category: "Trail", lat: 40.0, lon: -105.0 }] })
      : call("GET", "/api/maps"),
    memories: () => demo ? (() => {
      const elk = { id: "e1", name: "Elk Creek", where: "the high country", start: "2025-11-06", end: "2025-11-08", days: 3, km: 18.4,
        photos: 42, activities: [{ kind: "hike", trips: 2, km: 18.4, kmh: 3.1 }], places: [{ kind: "Camp", count: 3 }, { kind: "Water", count: 2 }],
        highlights: ["Saw a moose at dawn"],
        map: { w: 100, h: 62.4, points: [{ x: 8, y: 54.4, name: "Trailhead" }, { x: 31.5, y: 40.2, name: "Elk meadow" },
          { x: 55, y: 28.9, name: "Lower falls" }, { x: 92, y: 8, name: "Ridge camp" }] } };
      return Promise.resolve({ recaps: [elk], on_this_day: [elk] });
    })() : call("GET", "/api/memories"),
    observations: () => demo ? Promise.resolve({
      findings: [{ title: "A bill before payday", claim: "Rent is due Friday; your pay comes Monday, and the account is $120 short.",
        why: "Paid late, it costs a fee.", next: "Move it to Monday, or move $120 over.", app: "budget", sure: "DERIVED",
        kind: "Needs You", tone: "attention", used: "Money", open: { label: "Open in Money", href: "money.html" } },
        { title: "A heavy work week", claim: "Long shifts this week; two workouts were cut short.", why: "both short sessions followed 12-hour runs",
          next: "Move a training day to your day off.", app: "workout", sure: "DERIVED", kind: "Noticed", tone: "accent",
          used: "Workout · The Dungeon", open: { label: "Open in Workout", href: "workout.html" } }],
      insights: [{ source: "Upkeep", items: [{ title: "Oil change is overdue", message: "The mower's oil change was due 12 days ago.",
        next: "Mark it done, or reschedule it.", since: "2026-11-01", kind: "Noticed", tone: "accent", used: "Maintenance",
        open: { label: "Open in Maintenance", href: "maintenance.html" } }] }] })
      : call("GET", "/api/observations"),
    navigation: (start = "", end = "") => demo ? Promise.resolve({ day: "2026-11-06", waypoints: [
      { id: "w1", name: "Spring", category: "Water", lat: 40.01, lon: -105.0, grid: "13T DE 91476 30318" },
      { id: "w2", name: "Trailhead", category: "Trail", lat: 40.0, lon: -105.0, grid: "13T DE 91497 29207" }],
      route: start && end ? { from: start, to: end, km: 1.11, miles: 0.69, bearing: 0, toward: "N" } : null,
      sky: { at: "w2", name: "Trailhead", sunrise: "06:31", sunset: "16:51", moon: "Full moon" } })
      : call("GET", "/api/navigation?start=" + encodeURIComponent(start) + "&end=" + encodeURIComponent(end)),
    // The Household (core/household_routines.py): routines, Done Today, paused ones (DEC-0113 canvas).
    household: () => read("/api/household", "household"),
    classroom: () => demo ? Promise.resolve({ available: true, subjects: [
      { id: "s1", name: "Welding", category: "Trade skills", done: 2, total: 4, courses: [
        { id: "c1", name: "MIG basics", done: 2, total: 3, lessons: [
          { id: "l1", name: "Safety and setup", done: true, done_at: "2026-10-20", xp: 30 },
          { id: "l2", name: "Bead on plate", done: true, done_at: "2026-10-27", xp: 30, notes: "Push angle 10 to 15 degrees.\nListen for the bacon sizzle.",
            skill: { id: "welding", name: "Welding", xp: 30 } },
          { id: "l3", name: "Butt joints", done: false, done_at: "", xp: 30 }] },
        { id: "c2", name: "Stick welding", done: 0, total: 1, lessons: [{ id: "l4", name: "Striking an arc", done: false, done_at: "", xp: 30 }] }] }],
      continue: { subject: "Welding", course_id: "c1", course: "MIG basics", done: 2, total: 3, lessons: [
        { id: "l2", name: "Bead on plate", done: true, done_at: "2026-10-27", xp: 30 },
        { id: "l3", name: "Butt joints", done: false, done_at: "", xp: 30 }] },
      skills: [{ id: "welding", name: "Welding" }, { id: "metalwork", name: "Metalwork" }],
      textbooks: { available: true, books: [{ id: "b1", title: "Welding Fundamentals", pages: 312, added: "2026-10-12", reading: false, error: "",
        course: "", chapters: [{ title: "Chapter 1: Safety", page: 9 }, { title: "Chapter 6: Gas Metal Arc Welding", page: 101 }] }] } })
      : call("GET", "/api/classroom"),
    knowledge: (q = "") => demo ? Promise.resolve({ available: true, root: "reference_library", packs: [
      { id: "wikipedia_en_medicine", title: "Wikipedia: Medicine", description: "Medical articles, offline", articles: 52000 }],
      hits: q ? [{ pack_id: "wikipedia_en_medicine", pack_title: "Wikipedia: Medicine", path: "A/Hypothermia", title: "Hypothermia", snippet: "Hypothermia is a body core temperature below 35.0 °C. Shivering and confusion come first…" }] : [] })
      : call("GET", "/api/knowledge?q=" + encodeURIComponent(q)),
    knowledgeArticle: (pack, path) => demo ? Promise.resolve({ title: "Hypothermia",
      text: "Hypothermia is defined as a body core temperature below 35.0 °C. Symptoms depend on the temperature..." })
      : call("GET", "/api/knowledge/article?pack=" + encodeURIComponent(pack) + "&path=" + encodeURIComponent(path)),
    // MIA's own browser (core/web_browser.py): what it's on, steps waiting with their screenshots (MIA.download
    // "/api/browser/shot?id="), and the tasks she was taught.
    browser: () => demo ? Promise.resolve({ available: true, open: { title: "County Tax Office", url: "https://tax.example.gov/pay" },
      learning: null,
      waiting: [{ id: "p1", proposal_id: "", summary: "On tax.example.gov, press \"Pay now\" (\"Pay now\" changes something)",
        why: "\"Pay now\" changes something", site: "tax.example.gov", shot: false }],
      tasks: [{ id: "t1", name: "Pay the property tax", start: "https://tax.example.gov", state: "practising",
        summary: "Pay the property tax: 6 steps, practising, last run finished", steps: ["open https://tax.example.gov", "sign in yourself", "press \"Pay now\""],
        last: { at: "2026-11-07T10:00:00", clean: true, note: "" } }] })
      : call("GET", "/api/browser"),
    // The person working her browser from the live view (frames: MIA.download("/api/browser/frame")).
    browserInput: (body) => demo ? demoOnly() : call("POST", "/api/browser/input", body),
    // The Library's plans shelf (core/plan_library.py): the plans, one plan, and a plan's file (MIA.download).
    knowledgePlans: (q = "") => demo ? Promise.resolve({ available: true, folder: "reference_library/plans",
      sources: [{ name: "University of Tennessee Extension plan file", what: "300+ farm building plans", url: "https://trace.tennessee.edu/utk_agexfarmbld/" }],
      plans: [{ id: "builtin:gable-shed", title: "Gable shed", kind: "structure", summary: "A floor, four walls and a gable roof; any size.", where: "Built in, any size", file: false },
        { id: "builtin:raised-bed", title: "Raised garden bed", kind: "garden", summary: "Two boards tall with corner posts; any size.", where: "Built in, any size", file: false }] })
      : call("GET", "/api/knowledge/plans?q=" + encodeURIComponent(q)),
    knowledgePlan: (id, sizes) => demo ? Promise.resolve({ id, title: "Raised garden bed", kind: "garden", summary: "Two boards tall with corner posts.",
      where: "Built in, any size", file: false, materials_title: "8 x 4 ft raised bed, 11 in tall",
      items: [{ name: "2x6 x 8 ft", qty: 6, unit: "", note: "" }, { name: "soil and compost mix", qty: 1.09, unit: "cu yd", note: "29.3 cu ft" }],
      cuts: [{ part: "side", qty: 4, length: "8 ft", stock: "2x6 x 8 ft" }], notes: [], tools: ["saw", "drill/driver"],
      steps: ["Cut the sides, ends and corner posts.", "Screw it together and fill it."], source: { name: "MIA (worked out in code)" },
      sizes: [{ name: "length_ft", label: "Length", unit: "ft", value: 8 }, { name: "width_ft", label: "Width", unit: "ft", value: 4 },
        { name: "height_in", label: "Height", unit: "in", value: 11 }], sized: false, problem: "", kept: false,
      shopping: { rows: [{ item: "2x6 x 8 ft", unit: "", need: 6, have: 2, buy: 4, cost: 31.92, cost_text: "$31.92" },
        { item: "soil and compost mix", unit: "cu yd", need: 1.09, have: 0, buy: 1.09 }], to_buy: [], known_cost: 31.92, known_cost_text: "$31.92", priced: 1 } })
      : call("GET", "/api/knowledge/plan?id=" + encodeURIComponent(id) +
        (sizes ? "&sizes=" + encodeURIComponent(Object.entries(sizes).map(([k, v]) => k + "=" + v).join(",")) : "")),
    diagnostics: () => demo ? Promise.resolve({ error: "", checks: [
      { id: "pc_ready", title: "Is the PC ready for MIA?", ok: true, passed: 5, failed: [], unknown: [] },
      { id: "network", title: "The network", ok: false, passed: 2, failed: ["The wired connection is running at 100 Mb/s, under a gigabit."], unknown: [] },
      { id: "big_download", title: "Room for a big download", ok: true, passed: 2, failed: [], unknown: ["disk.D.free_gb"] }],
      hardware: [{ name: "Computer", value: "shop-pc", note: "x86_64" }, { name: "Processor", value: "AMD Ryzen 7 7700", note: "8 cores · 16 threads" },
        { name: "Memory", value: "32 GB", note: "38% in use" }, { name: "Drive C", value: "953.9 GB", note: "412 GB free · 56.8% full" },
        { name: "Network Wi-Fi", value: "192.168.1.20", note: "" }, { name: "Python", value: "3.12.4", note: "" }],
      problems: [{ when: "2026-11-07 18:02:00", level: "warning", where: "core.music_manager", text: "A song in the library couldn't be read; it was skipped." }] })
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
    operatingJournal: () => demo ? Promise.resolve({ sections: { values: "What I value", priorities: "My priorities", day: "My ideal day", week: "My ideal week", rules: "Rules I keep" }, lines: [
      { id: "o1", text: "Pay myself first on payday.", section: "rules", how: "checked against what's spent on Savings each month", self_rated: false, score: { pct: 75, text: "3 of 4 months" } },
      { id: "o2", text: "Train on the days the plan says.", section: "week", how: "checked against your workouts each week", self_rated: false, score: { pct: 75, text: "3 of 4 weeks" } },
      { id: "o3", text: "No phone at dinner.", section: "rules", how: "yours to rate, 1 to 5, each week", self_rated: true, score: { pct: 80, text: "4 / 5 last week" } }] })
      : call("GET", "/api/operating-journal"),
    // Sign-ins and Security (core/security_log.py): this account's sign-ins and changes, and sign out everywhere.
    securityLog: () => demo ? Promise.resolve({ available: true, other_sessions: 1, two_step: false, on_this_pc: true,
      at_rest: { sealing: true, protection: "dpapi", why_not: "", files: 10 }, events: [
      { at: "2026-11-08T08:12:00", kind: "sign_in", what: "Signed in", device: "Android phone · 100.64.0.7", detail: "" },
      { at: "2026-11-07T22:40:00", kind: "sign_in_failed", what: "Wrong password", device: "Edge on Windows · 100.64.0.9", detail: "" },
      { at: "2026-11-07T19:03:00", kind: "sign_in", what: "Signed in", device: "Edge on Windows · 100.64.0.9", detail: "a new device" }] })
      : call("GET", "/api/security/log"),
    signOutEverywhere: () => demo ? demoOnly() : call("POST", "/api/security/sign-out-everywhere"),
    // Your Data (core/your_data.py): what MIA keeps about you and what she read to answer you.
    yourData: () => demo ? Promise.resolve({ sealing: true, mine: [
      { file: "conversations.json", what: "Conversations with MIA", records: 42, bytes: 81234, sealed: true },
      { file: "user_memories.json", what: "What MIA remembers about you", records: 17, bytes: 6120, sealed: true },
      { file: "workouts.json", what: "Workouts", records: 9, bytes: 2210, sealed: false }],
      home: [{ file: "kitchen.json", what: "Kitchen", records: 64, bytes: 15800, sealed: false }],
      answers: [{ at: "2026-11-08T14:02:00+00:00", asked: "What's on my calendar tomorrow?", route: "tools", tools: ["get_calendar"], memories: 1 },
        { at: "2026-11-08T13:40:00+00:00", asked: "How much did I spend on food this week?", route: "plan", tools: ["get_budget"], memories: 0 }] })
      : call("GET", "/api/your-data"),
    // Everything of yours as a .zip (a Blob), after the password; and deleting the account. Not actions: a password
    // never sits in a proposal.
    exportData: async (password, includeHousehold) => {
      if (demo) return demoOnly();
      if (!token) throw new MiaError(401, "Not signed in.");
      const response = await fetch("/api/account/export", { method: "POST",
        headers: { Authorization: "Bearer " + token, "Content-Type": "application/json" },
        body: JSON.stringify({ password: password, include_household: !!includeHousehold }) });
      if (!response.ok) throw new MiaError(response.status, (await response.json().catch(() => ({}))).detail || response.statusText);
      return response.blob();
    },
    deleteAccount: (password, erase) => demo ? demoOnly() : call("POST", "/api/account/delete", { password: password, erase: !!erase }),
    // Sealed files (core/at_rest.py, DEC-0126): the recovery key, with the password, on the PC itself only.
    recoveryKey: (password) => demo ? demoOnly() : call("POST", "/api/security/recovery-key", { password }),
    // Connect Apps (core/connectors.py): the sources to import from, and an import's preview before it's approved.
    connect: () => demo ? Promise.resolve({ connectors: [
      { id: "file", name: "A file from another app", how: "Choose the file you downloaded", lands: "Calendar, People & Pets, or Money",
        examples: ["Google Calendar or Outlook (.ics)", "phone or Google contacts (.vcf)", "your bank's \"download transactions\" (.csv)"] },
      { id: "rental_calendar", name: "A rental's calendar link", how: "Paste the listing's private calendar link (.ics)",
        lands: "Calendar: a check-in and a check-out for each booked stay", examples: ["Airbnb", "VRBO", "Hostaway", "OwnerRez"] }],
      properties: ["Maple Duplex", "Oak Street House"], coming: ["Hostaway and OwnerRez (a key from their settings)", "Google Sheets", "QuickBooks"] })
      : call("GET", "/api/connect"),
    connectPreview: (body) => demo ? demoOnly() : call("POST", "/api/connect/preview", body),
    // Power (core/web_power.py, DEC-0125): the battery and the energy sources tracked by hand.
    power: () => read("/api/power", "power"),
    // The Lab (core/web_lab.py, DEC-0125): the Data Logger's series, and one in full (?series=).
    lab: (series = "") => read("/api/lab?series=" + encodeURIComponent(series), "lab"),
    // Notifications (core/web_notifications.py): newest first, with why MIA sent each one she sent on her own.
    notifications: () => read("/api/notifications", "notifications"),
    // Recent Changes (core/web_changes.py): what can be undone, and the fortnight's history.
    changes: () => read("/api/changes", "changes"),
    // The Field Kit (core/web_field_kit.py, DEC-0125): devices, network checks (worked out in core), scripts.
    fieldKit: () => read("/api/field-kit", "field_kit"),
    fieldKitCheck: (tool, value) => demo
      ? read("", "field_kit").then((f) => Object.assign({ demo: true }, (f.demo_answers || {})[tool] || { error: "The demo can't check." }))
      : call("GET", "/api/field-kit/check?" + new URLSearchParams({ tool, value }).toString()),
    // The Toolbox (core/web_toolbox.py, DEC-0125): calculators, alarms, tools; a calculator is worked out in core.
    // The demo can't calculate, so it answers with the example's own result.
    toolbox: () => read("/api/toolbox", "toolbox"),
    why: () => read("/api/why", "why"),
    projects: () => read("/api/projects", "projects"),
    backups: () => demo ? Promise.resolve({ folder: "C:\\Users\\you\\MIA Backups", count: 3, last: "12 days ago", days: 12,
      backups: [{ name: "mia_backup_2026-10-26_2130.miabackup", size: "48.2 MB", when: "Oct 26, 2026 21:30", locked: true }] })
      : call("GET", "/api/backups"),
    voiceChoice: () => demo ? Promise.resolve({ available: true, current: "kokoro:af_heart", effect: true, volume: 100, voices: [
      { id: "kokoro:af_heart", name: "Heart (American)", engine: "kokoro" }, { id: "kokoro:bf_emma", name: "Emma (British)", engine: "kokoro" },
      { id: "en_US-amy-medium", name: "Amy", engine: "piper" }] }) : call("GET", "/api/settings/voice"),
    chooseVoice: (change) => demo ? demoOnly() : call("POST", "/api/settings/voice", change),
    search: (q) => demo ? read("", "search").then((d) => ({ query: q, results: d.results.filter((r) =>
      q.toLowerCase().split(/\s+/).filter(Boolean).every((w) => r.title.toLowerCase().includes(w))) }))
      : call("GET", "/api/search?q=" + encodeURIComponent(q)),
    suggestMission: () => demo ? demoOnly() : call("POST", "/api/missions/idea", {}),
    checkCaptures: () => demo ? demoOnly() : call("POST", "/api/journal/captures/check", {}),
    deletePack: (id, confirm) => demo ? demoOnly() : call("POST", "/api/knowledge/pack/delete", { id, confirm }),
    backupNow: (passphrase) => demo ? demoOnly() : call("POST", "/api/backups", { passphrase: passphrase || "" }),
    textbookSearch: (q, book) => demo ? Promise.resolve({ query: q, hits: q ? [{ book_id: "b1", book: "Welding Fundamentals", page: 112,
      chapter: "Chapter 6: Gas Metal Arc Welding", text: "Hold the gun at a 10 to 15 degree push angle. Too steep an angle traps gas and leaves porosity in the bead…" }] : [] })
      : call("GET", "/api/classroom/textbooks/search?q=" + encodeURIComponent(q) + (book ? "&book=" + encodeURIComponent(book) : "")),
    toolboxCalc: (id, values) => demo
      ? read("", "toolbox").then((t) => Object.assign({ demo: true }, (t.demo_answers || {})[id] || { error: "The demo can't calculate." }))
      : call("GET", "/api/toolbox/calc?" + new URLSearchParams(Object.assign({ id }, values)).toString()),
    play: () => demo ? Promise.resolve({ efforts: { easy: 3, moderate: 5, hard: 7 }, lines: [],
      weeks: [60, 90, 45, 120, 75, 100].map((m, i) => ({ week: ["2026-09-28", "2026-10-05", "2026-10-12", "2026-10-19", "2026-10-26", "2026-11-02"][i], played: 2, play_minutes: m, play_load: m * 5, workouts: 2, workout_minutes: 90 })),
      played: [{ id: "g1", what: "Pickup basketball", minutes: 60, effort: 7, effort_word: "Hard", with: [], date: "2026-11-05", load: 420 },
        { id: "g2", what: "Disc golf, 18 holes", minutes: 40, effort: 3, effort_word: "Easy", with: [], date: "2026-11-01", load: 120 }] })
      : call("GET", "/api/play"),
    news: () => demo ? Promise.resolve({ on: true, day: "2026-11-07", now: "morning", scripts: { morning: "Good morning. Three good things today…" }, tracks: {},
      personalities: [{ key: "morning", name: "Morning" }],
      stories: [{ title: "A river cleanup removed 12 tons of trash in a weekend.", topic: "Environment", known: "confirmed", tag: "Confirmed by two outlets", tone: "ok",
        caveats: ["Numbers are the organizers' count."], links: ["https://example.org/a", "https://example.org/b"], outlets: ["Example News", "Example Daily"] },
        { title: "A seed library opens its third rural branch.", topic: "Community", known: "from the source", tag: "From the source itself", tone: "",
          caveats: ["Announced by the library; not yet reported elsewhere."], links: ["https://example.org/c"], outlets: ["The library"] },
        { title: "Monarch counts up along the eastern route.", topic: "Nature", known: "one outlet", tag: "One outlet", tone: "attention",
          caveats: ["Early estimate; the full survey comes in spring."], links: ["https://example.org/d"], outlets: ["Example Weekly"] }] })
      : call("GET", "/api/news"),
    // Guitar (core/guitar.py, DEC-0111): the stage, stats and open checks; a check heard from a WAV recording.
    guitar: (pathId) => demo ? Promise.resolve({ id: "guitar", name: "Guitar", stats: { started: "2026-11-02", stage: 1, stage_name: "First sounds",
        plan: { minutes_a_day: 15, days_a_week: 5 }, week_days: 3, week_minutes: 55, streak: 2, hours: 1.2,
        checks_passed: 2, checks: 18, stages: 5, bests: { changes_em_am: 16 } },
      next: "Stage 1, First sounds: next is \"Play A minor so every note rings\" (play it to me and I'll listen).",
      open: [{ id: "tuned", what: "Tune all six strings; let MIA hear each one", how: "heard_tuning", chord: "" },
             { id: "am_clean", what: "Play A minor so every note rings", how: "heard_chord", chord: "Am" },
             { id: "changes_em_am", what: "One-minute changes: E minor to A minor and back", how: "counted", chord: "" }],
      stage_checks: [{ id: "em_clean", what: "Play E minor so every note rings", how: "heard_chord", passed: true, state: "Passed · MIA heard it" },
             { id: "tuned", what: "Tune all six strings; let MIA hear each one", how: "heard_tuning", passed: false, state: "Open · MIA listens" },
             { id: "am_clean", what: "Play A minor so every note rings", how: "heard_chord", passed: false, state: "Open · MIA listens" },
             { id: "changes_em_am", what: "One-minute changes: E minor to A minor and back", how: "counted", passed: false, state: "Open · counted by you" }],
      homework: "Practise on 5 days; Practise 75 minutes in all this week." })
      : call("GET", "/api/paths").then((all) => {
        const one = all.paths.find((p) => p.id === (pathId || "guitar")) || all.paths[0];
        return one ? { stats: one.stats, next: one.next, open: one.open.map((c) => Object.assign({ chord: c.about }, c)),
                       id: one.id, name: one.name, stage_checks: one.stage_checks || [], homework: one.homework || "" }
          : { name: "Learning", stats: { started: false }, next: "Tell MIA what you'd like to learn.", open: [] };
      }),
    // Learning paths (core/paths.py, DEC-0112): every path started, and a check its program verifies (a recording).
    paths: () => demo ? Promise.resolve({ paths: [], drafts: [] }) : call("GET", "/api/paths"),
    guitarListen: (check, file, string, pathId) => MIA.upload("/api/paths/" + (pathId || "guitar") + "/verify", file,
      Object.assign({ "X-Check": check }, string ? { "X-String": String(string) } : {})),
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
    recipe: (id, servings) => read("/api/kitchen/recipe/" + encodeURIComponent(id) + (servings ? "?servings=" + servings : ""), "recipe"),
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
    // This tab's sign-in as a header, for a library that fetches by itself (the map's PMTiles reader).
    authHeaders: () => (token ? { Authorization: "Bearer " + token } : {}),
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
    // Start Here (core/web_guide.py): what she does and how, and what's new.
    guide: () => demo ? Promise.resolve({ topics: [{ id: "talk", title: "Talk to her", icon: "mia",
      how: "The glowing orb at the bottom right of every page opens Talk.", say: ["What can you do?", "What's on today?"],
      page: "index.html" }], new: [{ when: "2026-11-07", what: "This Start Here page.", page: "start.html" }] })
      : call("GET", "/api/guide"),
    // The inbox's mailbox (core/inbox_mail.py): set up, unlock, check now. Each answers with its status.
    inboxEmailSetup: (fields) => demo ? demoOnly() : call("POST", "/api/inbox/email", fields),
    inboxEmailUnlock: (passphrase) => demo ? demoOnly() : call("POST", "/api/inbox/email/unlock", { passphrase }),
    inboxEmailCheck: () => demo ? demoOnly() : call("POST", "/api/inbox/email/check"),
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
    homeConnect: (url, who, password, code) => demo ? demoOnly() : call("POST", "/api/home_pc/connect", { url, who, password, code: code || "" }),
    // Two-step sign-in (core/two_step.py): start (password: a key and a link), confirm (a code turns it on), off.
    twoStepStart: (password) => demo ? demoOnly() : call("POST", "/api/account/two-step/start", { password }),
    twoStepConfirm: (code) => demo ? demoOnly() : call("POST", "/api/account/two-step/confirm", { code }),
    twoStepOff: (password, code) => demo ? demoOnly() : call("POST", "/api/account/two-step/off", { password, code }),
    homeDisconnect: () => demo ? demoOnly() : call("POST", "/api/home_pc/disconnect"),
    syncNow: () => demo ? demoOnly() : call("POST", "/api/sync/now"),
    newChat: () => demo ? Promise.resolve({ reset: true }) : call("POST", "/api/voice/reset"),
    conversations: () => read("/api/talk/conversations", "conversations"),  // past conversations (core/web_conversations.py)
    conversation: (id) => demo ? read("", "conversation") : call("GET", "/api/talk/conversations/" + encodeURIComponent(id)),
    continueChat: (id) => demo ? demoOnly() : call("POST", "/api/talk/continue", { conversation_id: id }),
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
