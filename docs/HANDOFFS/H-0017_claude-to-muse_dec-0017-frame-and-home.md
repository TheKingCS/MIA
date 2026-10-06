# H-0017: DEC-0017 is approved: the shared frame and the dashboard Home are in
- From: claude · To: muse (cc zac, chatgpt) · Date: 2026-10-06
- Related: DEC-0017 (APPROVED), H-0016, H-0015, H-0013, Q-0004

## Context

Zac approved DEC-0017. The web becomes all of MIA, function first, in his concept look.

How the work splits:
- **Claude:** the full engine API and a working screen for each module.
- **Muse:** the look, including the shell, and restyling each screen against Zac's concept pictures. You have them; they stay out of the public repo.

`docs/WEB_PARITY.md` lists all 59 screens of the working MIA.

## What landed (yours to restyle; please keep the data flow)

### The shared frame: `web/shell.js` and `web/shell.css`

- **Sidebar:** the person's own apps from `MIA.shell()` (`/api/shell`, `core/web_surfaces.py`):
  - a child sees only the child apps;
  - apps someone tucked away are hidden;
  - level and XP are at the bottom;
  - "N more apps in the PC app for now" counts what hasn't come to the web yet.
- **MIA on every page:** a floating orb opens a Talk panel (`MIA.talk`).
- **`MIAShell.act(action)`:** the one way a screen changes anything. It proposes, shows the engine's sentence in a confirm, approves, then shows an undo toast.
- **Your seven pages:** I added one line to each, `<script src="shell.js" data-frame="<app id>">`, plus `shell.css`. So their sidebar is now the person's real one, and MIA is on them. I changed nothing else in your files.

### Home is the concept dashboard: `index.html` and `dashboard.js`

The data comes from `MIA.home()` (`/api/home`):
- greeting and date;
- Today's Focus as a checklist (ticking an item runs its action through the confirm);
- the day's saying;
- the five quick actions (they open Talk, pre-filled);
- Upcoming;
- Recent wins;
- at-a-glance cards (Money, Equipment, Real Estate, Kitchen, Workout, Missions).

### Your orb Home is kept, as `presence.html`

It's untouched apart from the rename, and linked from Home. Where the orb lives in the concept dashboard is your call.

### Examples for the public preview

`docs/schema/shell.example.json` and `home.example.json` hold placeholder data, so the public preview renders the new Home.

## Engine fixes found while driving it (FYI)

- **Undo now takes back the XP an action gave.** Before, it didn't on the phone and web.
- **An undone action no longer shows as a recent win** (it stays in the history).

## What's next on my side

1. **Money:** the full API (bills, income, expenses, debts with payoff order, summary, trends, bank sync status, every add/edit/delete/pay as an action) and a working screen.
2. **Garage and Maintenance, with the asset page.**
3. **Missions, Skills and Character.** This includes H-0013: real missions with objectives and rewards, per-skill XP and levels, character level.

Each screen lands working, on `components.css`, for you to restyle.

## What's needed from you

- **The look of the frame and Home against the concept:**
  - the photo hero;
  - the sidebar's look;
  - the orb's place;
  - quick-action tiles;
  - mobile.
- **Visuals:** the concept uses photographs. If you want them, add bundled images (placeholder or licensed, no CDNs) under `web/`.
- **Weather:** the hero shows it in the concept. The engine reports it as PLANNED (MIA has no weather source yet), so leave the chip out or show it honestly.

## Acceptance criteria
- Home and the frame look like the concept, and keep working: tick → confirm → done → undo, Talk, the person's own sidebar.
