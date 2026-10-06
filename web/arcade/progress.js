/* Lens Arcade — universal progression.
   One XP/level/achievement profile shared across every game.
   Games include this file, then call:
     ArcadeProgress.award('snake', 'newbest', 50)
   The module persists to localStorage, handles the daily streak,
   unlocks achievements, and shows gold toast notifications by itself —
   games don't need any UI for it. */
(function () {
  "use strict";
  var STORE = "lensArcadeProgress.v1";

  // XP needed to reach each level (cumulative)
  function xpForLevel(n) { return Math.floor(100 * n * (n + 1) / 2); } // L1:100 L2:300 L3:600 L4:1000…

  var ACHIEVEMENTS = [
    { id: "first",   name: "First Steps",   desc: "Play any game", xp: 25 },
    { id: "explorer",name: "Explorer",      desc: "Play 5 different games", xp: 60 },
    { id: "fullset", name: "Completionist", desc: "Play all 11 games", xp: 150 },
    { id: "streak3", name: "Warming Up",    desc: "3-day streak", xp: 80 },
    { id: "streak7", name: "On Fire",       desc: "7-day streak", xp: 200 },
    { id: "level5",  name: "Rising Star",   desc: "Reach level 5", xp: 100 },
  ];
  var ACH = {};
  ACHIEVEMENTS.forEach(function (a) { ACH[a.id] = a; });

  function blank() {
    return { xp: 0, games: {}, ach: {}, streak: 0, lastDay: null, visits: 0 };
  }
  function load() {
    try {
      var p = JSON.parse(localStorage.getItem(STORE));
      if (p && typeof p.xp === "number") { p.games = p.games || {}; p.ach = p.ach || {}; return p; }
    } catch (e) {}
    return blank();
  }
  function save(p) { try { localStorage.setItem(STORE, JSON.stringify(p)); } catch (e) {} }
  function dayStr(d) { return d.getFullYear() + "-" + (d.getMonth() + 1) + "-" + d.getDate(); }

  function levelForXp(xp) {
    var n = 0;
    while (xp >= xpForLevel(n + 1)) n++;
    return n;
  }

  /* ---- toasts (the module brings its own UI) ---- */
  var toastBox = null;
  function ensureToasts() {
    if (toastBox || !document.body) return;
    toastBox = document.createElement("div");
    toastBox.id = "ap-toasts";
    var st = document.createElement("style");
    st.textContent =
      "#ap-toasts{position:fixed;left:50%;bottom:26px;transform:translateX(-50%);z-index:9999;" +
      "display:grid;gap:8px;justify-items:center;pointer-events:none;}" +
      ".ap-toast{background:rgba(10,9,5,.92);border:1px solid rgba(246,196,83,.55);color:#ffedb8;" +
      "border-radius:99px;padding:9px 22px;font:700 14px system-ui,sans-serif;letter-spacing:.06em;" +
      "box-shadow:0 0 22px rgba(246,196,83,.35);animation:apIn .25s ease;white-space:nowrap;}" +
      ".ap-toast.big{font-size:17px;padding:12px 30px;border-width:2px;}" +
      ".ap-toast.out{opacity:0;transition:opacity .4s;}" +
      "@keyframes apIn{from{transform:translateY(12px);opacity:0;}}";
    document.head.appendChild(st);
    document.body.appendChild(toastBox);
  }
  function toast(text, big) {
    try {
      ensureToasts();
      var t = document.createElement("div");
      t.className = "ap-toast" + (big ? " big" : "");
      t.textContent = text;
      toastBox.appendChild(t);
      setTimeout(function () { t.classList.add("out"); setTimeout(function () { t.remove(); }, 450); }, big ? 2600 : 1600);
    } catch (e) {}
  }

  /* ---- core ---- */
  function touchDay(p) {
    var today = dayStr(new Date());
    if (p.lastDay === today) return;
    var y = new Date(); y.setDate(y.getDate() - 1);
    p.streak = (p.lastDay === dayStr(y)) ? p.streak + 1 : 1;
    p.lastDay = today;
    p.visits++;
  }

  function unlock(p, id, out) {
    if (p.ach[id]) return;
    var a = ACH[id];
    if (!a) return;
    p.ach[id] = Date.now();
    out.push(a);
  }

  function checkAchievements(p, out) {
    var gameCount = Object.keys(p.games).length;
    if (gameCount >= 1) unlock(p, "first", out);
    if (gameCount >= 5) unlock(p, "explorer", out);
    if (gameCount >= 11) unlock(p, "fullset", out);
    if (p.streak >= 3) unlock(p, "streak3", out);
    if (p.streak >= 7) unlock(p, "streak7", out);
    if (levelForXp(p.xp) >= 5) unlock(p, "level5", out);
  }

  function award(gameId, eventId, xp) {
    if (!gameId || !(xp > 0)) return { leveledUp: false, unlocked: [] };
    var p = load();
    var before = levelForXp(p.xp);
    touchDay(p);
    p.games[gameId] = (p.games[gameId] || 0) + 1;
    p.xp += xp;
    var after = levelForXp(p.xp);
    var unlocked = [];
    checkAchievements(p, unlocked);
    save(p);
    // celebrate: achievement toasts first, then XP, then level-up
    unlocked.forEach(function (a, i) {
      setTimeout(function () { toast("🏆 " + a.name + " (+" + a.xp + " XP)"); }, i * 900);
      p.xp += 0; // achievement XP already counted in design; kept simple
    });
    // grant achievement bonus XP quietly (no double toast)
    var bonus = unlocked.reduce(function (s, a) { return s + a.xp; }, 0);
    if (bonus > 0) { p.xp += bonus; save(p); after = levelForXp(p.xp); }
    var delay = unlocked.length * 900;
    setTimeout(function () { toast("+" + xp + " XP"); }, delay);
    var leveled = after > before;
    if (leveled) {
      (function (lvl) {
        setTimeout(function () { toast("⭐ LEVEL UP — Level " + lvl, true); }, delay + 900);
      })(after);
      checkAchievements(p, []); // level5 achievement check after bonus
      save(p);
    }
    return { leveledUp: leveled, level: after, unlocked: unlocked.map(function (a) { return a.id; }) };
  }

  function profile() {
    var p = load();
    var lvl = levelForXp(p.xp);
    var cur = xpForLevel(lvl), next = xpForLevel(lvl + 1);
    return {
      xp: p.xp,
      level: lvl,
      levelBase: cur,
      levelNext: next,
      progress: next > cur ? (p.xp - cur) / (next - cur) : 1,
      gamesPlayed: Object.keys(p.games),
      gameCount: Object.keys(p.games).length,
      achievements: Object.keys(p.ach),
      achievementCount: Object.keys(p.ach).length,
      streak: p.streak,
      visits: p.visits,
    };
  }

  // hub calls this on load so visits/streak tick even without playing
  function visit() {
    var p = load();
    touchDay(p);
    var unlocked = [];
    checkAchievements(p, unlocked);
    save(p);
    return profile();
  }

  window.ArcadeProgress = {
    award: award,
    profile: profile,
    visit: visit,
    achievements: ACHIEVEMENTS,
    xpForLevel: xpForLevel,
  };
})();
