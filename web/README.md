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
| `index.html`, `home.css`, `home.js` | MIA's Home: presence orb (celebrate / needs-you / quiet / thinking), the one due item with its action, the briefing sheet (Q-0004 order), Talk dock on Home. | Muse (built 2026-10-05, H-0009); data flow kept |

## The contract (what a screen may use)

```js
const state = await MIA.state();          // Life State v2: docs/schema/life_state.schema.json
MIA.onChange(() => refresh());            // fires whenever MIA's data changes (any device)

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
  `maintenance.done`, `task.done`, `routine.log`
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
