# H-0016: Getting the front end on track: all of MIA, in the concept's look
- From: claude · To: muse, chatgpt (cc zac) · Date: 2026-10-06
- Related: DEC-0017 (PROPOSED), DEC-0012, DEC-0013, Q-0004, H-0013

## Context

Zac (in chat with claude, 2026-10-06):
- The web front end is "so lacking compared to the MIA we had built together".
- He wants it built from the original program, all of MIA's functionality, the repo and his concept pictures.
- The result should be a functional MIA tied to the back end that looks like the concepts.

## What went wrong (claude's read, and mostly claude's part)

- **The contract was too narrow.** I gave `web/` one summary (`/api/state`) and five action kinds. The rules said:
  - no business logic in the front end;
  - if something isn't in Life State, ask for it.

  Muse followed that exactly, so every screen can only show the summary. The Bills, Debts, Garage and Kitchen screens have nothing to read and nothing they're allowed to change. H-0013 was Muse hitting that wall.
- **Home was designed as one due item and "never a module list"** (Q-0004). Zac's concept is a full dashboard.
- **The working MIA (the Qt app) was never the spec for the web screens.** The 38 modules, ~175 Assistant tools and the 55 screenshots in `docs/design_handoff/screens/` describe what MIA does. The new screens were designed from the schema instead.

## The proposal (DEC-0017, waiting on Zac)

- **Parity checklist:** `docs/WEB_PARITY.md` lists every screen, tab and operation of today's MIA, with three checkboxes each: engine API, working web screen, matches the concept.
- **Claude:**
  - a full API per module (reads, plus every operation as an action kind with propose, approve and undo);
  - a working web screen per module, built on Muse's `tokens.css` and `components.css`.
- **Muse:**
  - the shell, from the concept: top bar, sidebar, search, level and XP, the orb;
  - the component system;
  - restyling each working screen to match the concepts, and checking it against them;
  - the desktop Home as the concept's dashboard, and the phone as the concept's mobile app.
- **ChatGPT:** the "is this still MIA?" check on each module as it lands.
- **The Qt app stays the working MIA on the PC** until a module reaches parity.

**Order:**
1. The shell and the Home dashboard.
2. Money.
3. Garage and Maintenance.
4. Missions, Skills and Character (this absorbs H-0013).
5. Calendar, Notes, Inbox, Talk.
6. Kitchen, Workout, Real estate.
7. The rest.

## What's needed

- **Zac:** approve DEC-0017, or change it.
- **Muse:** review DEC-0017 from the design side. In particular:
  - Home as the concept dashboard;
  - the split where Claude builds working screens and Muse styles and owns the shell.
- **ChatGPT:** review for vision fit.

## Acceptance criteria

- `docs/WEB_PARITY.md` exists and every module has a row.
- Each module, as it lands: everything its Qt screen can do works on the web against the real engine (tested), and it looks like the concepts (Muse's sign-off).
