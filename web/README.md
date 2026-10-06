# web/: MIA's front end (Phase 2, DEC-0012)

*Owner: Muse (design and front-end code). Engine and APIs: Claude.
Started 2026-10-05 by Claude as a working scaffold that proves the
plumbing. The look is a placeholder for Muse to replace.*

One MIA component system, with surface-specific compositions (DEC-0012,
ChatGPT's refinement): the desktop, phone and glasses share these
components, data and actions, and each arranges them for its screen.

## How it runs

- MIA's own local server (`server/app.py`) serves this folder at
  **`/web/`**. Nothing loads from the internet: bundle fonts, images and
  any libraries in this folder.
- **Devices, in order (DEC-0015):** Zac's new computer, his phone, Meta
  Display glasses (soon), his own Pi devices (eventually).
- **Desktop (the new computer):** the "Home (preview)" app inside MIA
  shows this page in a built-in browser, already signed in as whoever
  is at the desktop (`modules/web_home/`).
- **Phone:** the same pages, at the phone address, once the phone
  version is designed (later step).
- **Phone and any browser:** `/web/` shows a sign-in (email and
  password, the same as the phone app), then the Home. `MIA.signIn()`.
- **Without MIA's data:** open `/web/?demo` to render the published
  placeholder example (`docs/schema/life_state.example.json`). Actions
  are off in the demo.

## The files

| File | What it is | Who |
|---|---|---|
| `mia.js` | **The engine client.** The only code that talks to MIA. Every screen uses it. | Claude (ask in `docs/QUESTIONS.md` for changes) |
| `tokens.css` | Design tokens: colors, type, spacing. `--scale` follows the person's text size; `[data-contrast="high"]` is high contrast. | Muse |
| `shell.js`, `shell.css` | **The shared frame (DEC-0017).** Sign-in, navigation (desktop module pages: the sidebar; phones and Home: one ⋯ menu button; the person's own apps, level and XP, from `MIA.shell()`), MIA's orb and Talk panel on every page, and `MIAShell.act(action)`: propose → confirm → approve → undo toast. New screens use `MIAShell.start(render)`; older ones get the frame with `<script src="shell.js" data-frame="<app id>">`. | Claude (function); Muse restyles freely |
| `concept.css` | **The mobile concept's look (DEC-0018)**, loaded last on every page: per-screen color and photo from `<body data-app>` (`img/<screen>.jpg`, `docs/design/IMAGE_REQUESTS.md`), photo heroes, icon badges, glowing cards, the status strip, needs-attention, segmented tabs, the phone's bottom bar and the menu drawer. | Claude (DEC-0018); Muse reviews |
| `index.html`, `welcome.js` | **Home, the concept's (DEC-0018):** greeting, date, Today's Focus (tick → its action), the day's saying, quick actions into MIA Assistant, level and XP. | Claude |
| `assistant.html`, `assistant.js` | **MIA Assistant:** the chat (typed via `MIA.talk`, spoken via the mic → WAV → `MIA.voice`, her spoken reply played back); `?ask=`, `?draft=`, `?voice=1`. | Claude |
| `dashboard.html`, `dashboard.js` | **Dashboard: the concept's dashboard** (DEC-0017): greeting, Today's Focus (tick → its action), quick actions, Upcoming, recent wins, at-a-glance cards, all from `MIA.dashboard()`. | Claude (function); Muse (look) |
| `money.html`, `money.js` | **Money (DEC-0017):** everything the PC's Budget screen does, from `MIA.money()`: Overview, Bills, Income, Expenses, Debts (payoff order and why), Budgets, Trends, Bank status. Every change is a money action (`core/money_actions.py`); forms come from the engine (`MIAShell.form`). `finances.html` now redirects here. | Claude (function); Muse (look) |
| `garage.html`, `property.html`, `greenhouse.html`, `maintenance.html`, `equipment.js` | **Equipment (DEC-0017):** one script, the page's `data-scope` picks the screen, from `MIA.equipment(scope)`: tracked / needs attention / next up, asset cards with their tasks, Done (asks the meter reading for hour-based tasks); Maintenance adds every task and a two-month calendar. | Claude (function); Muse (look) |
| `asset.html`, `asset.js` | **One asset (DEC-0017)**, Zac's mower concept: quick stats with Log, needs attention, Overview / Maintenance / Missions / Documents (upload, open, remove) / Costs / History / Parts, from `MIA.asset(id)`. | Claude (function); Muse (look) |
| `kitchen.html`, `kitchen.js` | **Kitchen (DEC-0017/0018):** from `MIA.kitchen()`: Recipes (cards with what's missing; a locked one names the mission that unlocks it; View opens the recipe with Log meal, Add missing, Favorite, Ingredients, Edit, Delete), Pantry and Grocery List side by side (check off, clear checked), Meal Log, Suggestions. Kitchen actions (`core/kitchen_actions.py`). | Claude (function); Muse (look) |
| `workout.html`, `workout.js` | **Workout (DEC-0017/0018):** from `MIA.workout()`: the concept's inline Log Session (one exercise, or a whole template; what's typed survives a live refresh), Latest Entry, Daily Mission with progress and streak, Exercises (PRs), Templates, History, Progress. Workout actions (`core/workout_actions.py`). | Claude (function); Muse (look) |
| `real-estate.html`, `real-estate.js` | **Real Estate (DEC-0017/0018):** from `MIA.realEstate()`: property cards (status, where, rent, balance, equity, cash flow, this month), Record rent and Add expense (into Money), Track upkeep (its own Maintenance asset), Maintenance and Missions tabs. Property actions (`core/estate_actions.py`); grown-ups only. | Claude (function); Muse (look) |
| `apps.html`, `apps.js` | **Apps (DEC-0017):** every app MIA has, by life area, from `MIA.apps()`: what it's for, open it (on the web) or ask MIA (its Assistant tools listed), find, show/hide per person (`app.visibility`). | Claude (function); Muse (look) |
| `presence.html`, `home.css`, `home.js` | **MIA's face** (reached from her badge on MIA Assistant and Home) (Zac, 2026-10-06: Home is MIA's face and a chat with her): the orb (celebrate / needs-you / quiet / thinking), the one due item, the briefing sheet, Talk. Navigation is the frame's ⋯ menu. | Muse (H-0009) |
| `components.css` | Shared component system: glass cards, status strips, XP bars, rarity badges, pill tabs, buttons, heroes, sidebar, empty/locked states. Concept-art material. | Muse |
| `missions.html`, `missions.js` | Missions: status strip, streaks, Active/Completed tabs over the engine's due items and recent wins, propose/approve on every action, ask-MIA-to-invent via talk. | Muse |
| `skills.html`, `skills.js` | Skills: evidence-backed portfolios from the engine's skill_evidence events under its growing/declining/dormant trends. No decorative XP. | Muse |

## The contract (what a screen may use)

```js
const state = await MIA.state();          // Life State v2: docs/schema/life_state.schema.json
const shell = await MIA.shell();          // the sidebar: the person's apps, level and XP
const dash = await MIA.dashboard();       // the Dashboard: greeting, Today's Focus, glance cards
const apps = await MIA.apps();            // every app, grouped, with what MIA can do in each
MIA.onChange(() => refresh());            // fires whenever MIA's data changes (any device)
const turn = await MIA.talk("what's on today?");  // one Assistant turn: turn.reply_text

// Changing anything: always Propose → Approve → Execute → Record → Undo.
const p = await MIA.propose(item.action.kind, item.action.params);  // nothing changes yet
// show p.summary to the person ("Mark Electric paid ($120.00)"), and on yes:
const done = await MIA.approve(p.proposal_id);   // the engine does it and records it
// done.result says what happened; if done.undoable, offer:
await MIA.undo(done.proposal_id);
```

- **Where actions come from:** each `due.items[]` entry carries an
  `action` (or `null`), e.g. `{kind: "bill.pay", label: "Mark paid",
  params: {bill_id}}`. Use its `label` for the button and pass it to
  `propose`. Don't build actions yourself.
- **Action kinds today:** `bill.pay`, `income.receive`,
  `maintenance.done`, `task.done`, `routine.log`, `app.visibility`, `app.favorite`, and the money kinds (`bill.add/edit/delete`, `income_source.*`, `income.*`, `expense.*`, `debt.*`, `debt.pay`, `budget_target.set/delete`) and the equipment kinds (`asset.add/edit/delete`, `maintenance_task.*`, `maintenance.reading`, `asset.reading`, `asset.document_remove`; `maintenance.done` takes `meter_value`), the kitchen kinds (`recipe.*`, `recipe.ingredients`, `recipe.favorite`, `pantry.*`, `grocery.add/delete/check/clear_checked/from_recipe`, `meal.log/delete`), the workout kinds (`exercise.*`, `workout_template.*`, `workout_template.exercise_add/exercise_remove`, `workout.log/delete`) and the real-estate kinds (`property.add/edit/delete/rent/expense/track_upkeep`)
  (`GET /api/actions/kinds`). Need another? Ask in
  `docs/QUESTIONS.md` and Claude adds it to the engine.
- **Proposal shape:** `docs/schema/action.schema.json`. Errors come back
  as `MiaError` with a plain message to show (e.g. a child account gets
  "That one's for grown-ups. Ask a parent if you need it.").

## Rules (from DECISIONS.md)

1. **No business logic in the front end** (DEC-0013): no totals, dates,
   "is it overdue", permissions or money math. If you need a number,
   it's in Life State; if it isn't, ask for it.
2. **Never act without approval** (DEC-0009): every change goes
   through `propose`, a visible confirmation, then `approve`.
3. **Statuses** (DEC-0007): show a section's `status` honestly. PLANNED
   means "coming", never faked.
4. **No real personal data** in the code, comments or examples
   (DEC-0002). Use the placeholder example.
5. **Offline:** no CDNs, web fonts or analytics from the internet.
6. **Accessible:** keyboard-usable, `prefers-reduced-motion` respected,
   text that scales with `--scale`, and high contrast.
7. **Children** see less (no money, no property). Life State already
   hides it, so design the empty states.

## What's next (DEC-0013)

1. **Prove the slice on the new computer and the phone:**
   `python -m tools.web_check` (Zac).
2. **Muse:** the real Home and presence look — done 2026-10-05
   (tokens, orb states, focus card, briefing, Talk dock, phone
   composition). Next: Talk polish, then glasses cards.
3. Glasses cards as soon as Q-0003 is answered.
4. Then the domain screens one at a time, each with its own handoff.
