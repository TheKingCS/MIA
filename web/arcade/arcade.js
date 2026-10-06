/* Lens Arcade storefront logic.
   BUY FLOW (demo): purchases are simulated and stored in localStorage.
   For launch, point buyGame()/buyPass() at real Stripe Payment Links:
   swap the simulatePurchase() calls for location.href = STRIPE_LINKS[id],
   and fulfill on the Stripe success redirect (e.g. ?bought=pass). */
(function () {
  "use strict";

  var STORE = "lensArcadeOwned.v1"; // { pass: bool, games: {id: true} }

  var GAMES = [
    {
      id: "tictactoe", name: "Tic-Tac-Toe", art: "⭕", glow: "rgba(246,196,83,0.5)",
      hook: "The classic, against an AI that trash-talks politely.",
      how: "Tap a square. Three difficulties — Hard is genuinely unbeatable.",
      price: 0, path: "games/tictactoe.html", live: true,
    },
    {
      id: "hangman", name: "Hangman", art: "🪢", glow: "rgba(180,140,242,0.5)",
      hook: "Guess the word before the gallows fills in.",
      how: "Tap letters on the on-screen picker. Six wrong guesses and it's over.",
      price: 1, path: "games/hangman.html", live: true,
    },
    {
      id: "magic8ball", name: "Magic 8 Ball", art: "🎱", glow: "rgba(140,170,255,0.5)",
      hook: "Ask a question, tap the ball, accept your fate.",
      how: "Think of a yes-or-no question — ask it out loud — tap the ball to shake.",
      price: 1, path: "games/magic8ball.html", live: true,
    },
    {
      id: "dice", name: "Dice Roller", art: "🎲", glow: "rgba(246,196,83,0.55)",
      hook: "Every die you'll ever need, on your face.",
      how: "Pick d4 through d100, roll up to six at once. Tabletop approved.",
      price: 1, path: "games/dice.html", live: true,
    },
    {
      id: "coin", name: "Coin Flip", art: "🪙", glow: "rgba(255,237,184,0.55)",
      hook: "Settle it the old-fashioned way.",
      how: "Tap the coin. Heads or tails, with streak tracking.",
      price: 1, path: "games/coin.html", live: true,
    },
    {
      id: "pet", name: "Mote", art: "🔆", glow: "rgba(246,196,83,0.6)",
      hook: "A tiny mote of light that lives in your glasses.",
      how: "Feed it, play with it, pet it, tuck it in. It needs you — check in daily.",
      price: 1, path: "games/pet.html", live: true,
    },
    {
      id: "snake", name: "Snake", art: "🐍", glow: "rgba(95,214,200,0.55)",
      hook: "The timeless one. Eat, grow, don't bite yourself.",
      how: "Swipe or use the D-pad. Speeds up every bite.",
      price: 1, path: "games/snake.html", live: true,
    },
    {
      id: "reaction", name: "Reaction", art: "⚡", glow: "rgba(242,140,140,0.55)",
      hook: "How fast are you, really?",
      how: "Wait for green, then tap. Too soon counts against you.",
      price: 1, path: "games/reaction.html", live: true,
    },
    {
      id: "orbit", name: "Orbit", art: "🛰️", glow: "rgba(180,140,242,0.55)",
      hook: "An idle space station that grows while you're not looking.",
      how: "Tap the station, buy generators, collect while you sleep.",
      price: 1, path: "games/orbit.html?v=3", live: true,
    },
    {
      id: "sayit", name: "Say It", art: "🗣️", glow: "rgba(242,140,140,0.5)",
      hook: "Voice trivia — 60-second blitz. Think it, tap it.",
      how: "Question appears, tap the right answer. +100 each, no penalties.",
      price: 1, path: "games/sayit.html", live: true,
    },
    {
      id: "drift", name: "Drift", art: "✨", glow: "rgba(246,196,83,0.6)",
      hook: "A one-tap dodger. Guide the light past everything.",
      how: "Classic or Levels — tap to pulse upward, dodge the gates.",
      price: 1, path: "games/drift.html", live: true,
    },
    {
      id: "stack", name: "Stack", art: "🗼", glow: "rgba(180,140,242,0.55)",
      hook: "One tap, perfect timing, endless tower.",
      how: "Tap to drop each block. Miss the edge and it slices off.",
      price: 1, path: "games/stack.html", live: true,
    },
    {
      id: "breakout", name: "Breakout", art: "🧱", glow: "rgba(95,214,200,0.55)",
      hook: "The brick-breaker. Pure arcade nostalgia.",
      how: "Slide the paddle, smash every brick. 3 lives per run.",
      price: 1, path: "games/breakout.html", live: true,
    },
    {
      id: "2048", name: "2048", art: "🔢", glow: "rgba(246,196,83,0.6)",
      hook: "The swipe-number legend. Merge to 2048.",
      how: "Swipe to slide tiles. Matching tiles merge — chase 2048.",
      price: 1, path: "games/2048.html", live: true,
    },
    {
      id: "fruitslice", name: "Fruit Slice", art: "🍉", glow: "rgba(255,120,90,0.55)",
      hook: "Swipe to slice. Don't hit the bombs.",
      how: "Fruits arc upward — slice them mid-air. 3 misses and you're out.",
      price: 1, path: "games/fruitslice.html", live: true,
    },
  ];

  function load() {
    try { return JSON.parse(localStorage.getItem(STORE)) || { pass: false, games: {} }; }
    catch (e) { return { pass: false, games: {} }; }
  }
  function save(state) { localStorage.setItem(STORE, JSON.stringify(state)); }
  var owned = load();
  function owns(id) {
    var g = GAMES.filter(function (x) { return x.id === id; })[0];
    if (g && g.price === 0) return true; // free games are always owned
    return owned.pass || !!owned.games[id];
  }

  var grid = document.getElementById("grid");

  function tile(g) {
    var b = document.createElement("button");
    b.className = "tile" + (g.live ? "" : " soon");
    b.type = "button";
    var status = g.live
      ? (g.price === 0 ? '<span class="price owned">FREE</span>'
        : owns(g.id) ? '<span class="price owned">PLAY</span>' : '<span class="price">$1</span>')
      : '<span class="badge">soon</span>';
    b.innerHTML =
      '<span class="art" style="--glow:' + g.glow + '">' + g.art + "</span>" +
      "<h3>" + g.name + "</h3><p>" + g.hook + "</p>" +
      '<span class="row">' + status +
      (g.live ? '<span class="badge live">playable</span>' : "") + "</span>";
    b.addEventListener("click", function () { openSheet(g); });
    return b;
  }

  function render() {
    grid.replaceChildren.apply(grid, GAMES.map(tile));
    document.getElementById("pass-banner").hidden = !!owned.pass;
  }

  /* ---- detail sheet ---- */
  var sheet = document.getElementById("sheet");
  function openSheet(g) {
    document.getElementById("sheet-kicker").textContent = g.live
      ? (g.price === 0 ? "free forever" : owns(g.id) ? "in your collection" : "$1 — yours forever")
      : "coming soon";
    document.getElementById("sheet-title").textContent = g.name;
    document.getElementById("sheet-hook").textContent = g.hook;
    document.getElementById("sheet-how").textContent = g.how;
    var actions = document.getElementById("sheet-actions");
    actions.innerHTML = "";
    function btn(label, cls, fn, note) {
      var el = document.createElement("button");
      el.type = "button"; el.className = "btn " + (cls || ""); el.textContent = label;
      el.addEventListener("click", fn);
      actions.appendChild(el);
      if (note) { var f = document.createElement("p"); f.className = "fine"; f.textContent = note; actions.appendChild(f); }
    }
    if (!g.live) {
      btn("Coming soon", "", function () {}, "Season 1 keeps growing — pass holders get it on drop day.");
    } else if (g.price === 0 || owns(g.id)) {
      btn("Play now", "primary", function () { location.href = g.path; });
    } else {
      btn("Play now", "primary", function () { location.href = g.path; }, "Demo: playing free while we build. Checkout connects at launch.");
      btn("Buy — $1", "", function () { simulatePurchase(g.id, g.name); }, "Demo purchase — no charge. Real checkout plugs in here.");
    }
    sheet.hidden = false;
  }
  document.getElementById("sheet-close").addEventListener("click", function () { sheet.hidden = true; });
  sheet.addEventListener("click", function (e) { if (e.target === sheet) sheet.hidden = true; });

  /* ---- purchases (simulated) ---- */
  function simulatePurchase(id, label) {
    owned.games[id] = true; save(owned); render();
    openSheet(GAMES.filter(function (g) { return g.id === id; })[0]);
  }
  document.getElementById("pass-buy").addEventListener("click", function () {
    owned.pass = true; save(owned); render();
  });

  /* ---- arcade profile (universal progression) ---- */
  function renderProfile() {
    if (!window.ArcadeProgress) return;
    var p = ArcadeProgress.visit();
    var box = document.getElementById("profile");
    box.hidden = false;
    document.getElementById("profile-level").textContent = "⭐ LVL " + p.level;
    document.getElementById("profile-streak").textContent = p.streak > 1 ? "🔥 " + p.streak + "-day streak" : "";
    document.getElementById("profile-trophies").textContent = "🏆 " + p.achievementCount + "/" + ArcadeProgress.achievements.length;
    document.getElementById("profile-xpfill").style.width = Math.round(p.progress * 100) + "%";
    var toNext = p.levelNext - p.xp;
    document.getElementById("profile-xptext").textContent =
      p.xp + " XP · " + toNext + " to Level " + (p.level + 1) + " · " + p.gameCount + "/11 games played";
    var achBox = document.getElementById("profile-ach");
    achBox.innerHTML = "";
    p.achievements.forEach(function (id) {
      var a = null;
      ArcadeProgress.achievements.forEach(function (x) { if (x.id === id) a = x; });
      if (!a) return;
      var pill = document.createElement("span");
      pill.className = "ach-pill";
      pill.textContent = "🏆 " + a.name;
      pill.title = a.desc;
      achBox.appendChild(pill);
    });
  }

  render();
  renderProfile();
})();
