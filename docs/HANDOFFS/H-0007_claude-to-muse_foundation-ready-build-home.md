# H-0007: The foundation is ready. Build MIA's Home on it.
- From: claude · To: muse (cc zac, chatgpt) · Date: 2026-10-05
- Related: DEC-0012, DEC-0013, DEC-0014, H-0005, H-0006 (your review),
  Q-0004 (your Home answer), Q-0007, Q-0009, `web/README.md`

## Context

DEC-0012 and DEC-0013 are approved, with ChatGPT's refinement: one
component system, surface-specific compositions; the action contract is
first-class; prove one vertical slice on the real devices first (Zac's
new computer and phone, DEC-0015; the Pi is a later device). Claude built
the foundation, and the slice runs end to end:

**engine → `/api/state` → web Home → real data → an action → updated
state, live.**

In a real browser against MIA's real server, with placeholder data:
- The page loads in about 110 ms.
- "Done" on the overdue item shows the engine's sentence ("Mark
  'Sharpen blades' done on Mower today?").
- On yes, the engine executes it, records it in the history and offers
  Undo.
- The page refreshes itself, and the orb celebrates the win.
- A change made from another device appeared on the open page in
  0.4 seconds.

Screenshots (placeholder data):
`assets/H-0007_scaffold_confirm.png`, `assets/H-0007_scaffold_briefing.png`.

Inside the desktop app, the new **"Home (preview)"** app shows the same
page in MIA's window, signed in automatically, with phone access off.

## Your H-0006 and Q-0007 asks, delivered

(They crossed in the repo: both were written at the same time.)

1. **A starter `web/` layout and the desktop shell wiring:** done.
   `web/` is served at `/web/`, and the desktop's "Home (preview)" shows
   it.
2. **A mock `/api/state` from the example:** `/web/?demo` renders
   `docs/schema/life_state.example.json` (served at
   `/schema/life_state.example.json`), with actions off. **The real
   endpoints exist now too**, so you can build against the real shape
   from day one.
3. **The `/api/actions` contract:** done, more than "mark paid" (five
   kinds), propose-then-approve with undo. See `web/README.md` and
   `docs/schema/action.schema.json`.
4. **Live updates documented:** `MIA.onChange()` in `web/mia.js`
   (`/api/live` underneath).
5. **The device check includes the frame rate:** `python -m tools.web_check`
   prints load time, memory and fps on the real device (now Zac's new
   computer first, DEC-0015).
6. **Your constraints hold:**
   - Home is presence, not a dashboard; the briefing is one tap away.
   - The scaffold's presence only celebrates earned progression, and
     the due item is a calm line (DEC-0014, pending Zac).
   - One token file, all offline.
   - The Qt screens stay until each web replacement is better.

## What exists for you (all in the repo)

| Piece | Where |
|---|---|
| The front end's home | `web/`, served by MIA at `/web/` (`/web/?demo` shows the placeholder example) |
| **Your guide** | `web/README.md`: how it runs, the files, the contract, the rules |
| The engine client (don't fork it; ask for changes) | `web/mia.js`: `MIA.state()`, `MIA.propose/approve/reject/undo`, `MIA.onChange()` |
| Design tokens (yours) | `web/tokens.css`: starting values are today's Dark Field theme; `--scale` and high contrast are wired to the person's settings |
| The Home scaffold (yours to replace) | `web/index.html`, `home.css`, `home.js`: presence (celebrate / needs-you / quiet), the one due item with its action, the briefing (wins → friction → questline → money gap), following your Q-0004 answer |
| The data | `docs/schema/life_state.schema.json`. Each `due` item now carries `action` (`{kind, label, params}` or `null`) |
| The action contract | `docs/schema/action.schema.json`. Kinds: `bill.pay`, `income.receive`, `maintenance.done`, `task.done`, `routine.log` |

## What's needed (Muse)

1. ~~Answer Q-0007 and Q-0009~~: done in H-0006, thank you.
2. **The real Home and presence**, replacing the scaffold's look and
   keeping its data flow:
   - `tokens.css`: MIA's visual language (the concept art's direction,
     with restraint).
   - The presence orb's states: quiet (default), celebrating a new win,
     needs-you (one due item), and, for Talk later, listening and
     thinking.
   - The focus card: the one due item, its action button, and the
     confirm step that shows the engine's `summary`.
   - The briefing, one tap away.
   - The undo toast after an action.
   - Empty and child states: a child gets no money or property, and
     only the `task.done` and `routine.log` actions.
3. **Compositions, in the order of DEC-0015:**
   - The desktop first: Zac's new computer, a normal window up to full
     screen, mouse and keyboard.
   - The phone right after: 390 px wide, touch. It replaces the phone
     app's Today tab and later Talk and Money.
   - The glasses next, as soon as Q-0003 is answered.
   - The Pi devices much later.
4. Send back a short handoff (template in `docs/HANDOFFS/README.md`)
   listing what each screen uses from Life State. If anything is
   missing, ask in `QUESTIONS.md`, and Claude adds it to the engine.

## Constraints

- **No business logic in `web/`:** no totals, no "is it overdue", no
  permissions. If it isn't in Life State, ask.
- **Every change goes through `propose`**, a visible confirmation, then
  `approve`. Never call `approve` without the person saying yes.
- **Offline:** bundle fonts and images in `web/`. No CDNs.
- **Placeholders only**, never real personal data.
- **Accessible:** keyboard, `prefers-reduced-motion`, `--scale`, high
  contrast.

## Acceptance criteria (the Phase 2 first milestone)

- Home (preview) on the desktop and `/web/` on the phone show Muse's
  Home, with real data, from the same code.
- Presence reacts: a new win celebrates, otherwise the one due item
  shows, otherwise it's quiet. It updates live when something changes on
  another device.
- One action works end to end with your confirm step and undo.
- The check passes on Zac's new computer (`python -m tools.web_check`;
  see `docs/NEXT_SESSION.md`), and the Home is usable on his phone.
- The Qt Home and all 37 screens still work.

## Response

*(muse: reply here or in a new handoff)*
