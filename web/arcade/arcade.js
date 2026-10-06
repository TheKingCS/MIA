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
      id: "orbit", name: "Orbit", art: "🛰️", glow: "rgba(95,214,200,0.5)",
      hook: "An idle space station that grows while you're not looking.",
      how: "Glance, tap to collect, spend on upgrades. The ultimate face-screen loop.",
      price: 1, path: null, live: false,
    },
    {
      id: "sayit", name: "Say It", art: "🗣️", glow: "rgba(242,140,140,0.5)",
      hook: "Voice trivia — the question appears, you just say the answer.",
      how: "60-second blitz rounds. Built for the glasses' microphone.",
      price: 1, path: null, live: false,
    },
    {
      id: "drift", name: "Drift", art: "✨", glow: "rgba(246,196,83,0.6)",
      hook: "A one-tap dodger. Guide the light past everything.",
      how: "Tap to pulse. Thirty-second runs, high-score chase.",
      price: 1, path: null, live: false,
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

  render();
})();
