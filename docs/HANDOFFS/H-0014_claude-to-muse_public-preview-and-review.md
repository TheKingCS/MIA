# H-0014: The public preview is set up; a look at Home, Missions and Skills
- From: claude · To: muse (cc zac, chatgpt) · Date: 2026-10-05
- Related: DEC-0016 (APPROVED), Q-0011, Q-0012, H-0009, H-0012, H-0013

## Context

Zac decided, in chat with Claude:
- **DEC-0016 is APPROVED**: the glasses get a Web App first, then the Android app adds voice.
- **The GitHub Pages preview is approved.**
- **Q-0011 is answered:**
  - His phone is Android.
  - He has no glasses yet.
  - MIA isn't installed on the PC yet.

  So the Funnel link waits, and the preview comes first.
- **Q-0012 is parked:** "we will come back to this some other time".

Zac asked to see your front end. Claude ran it against the real engine with placeholder data and sent him phone and desktop screenshots of Home, the briefing, Missions and Skills. Nothing showed a page error.

## What's new on the engine side

- **The public preview:** `.github/workflows/pages.yml` publishes `web/` and the schemas on every push that touches them.
  - The address is **https://thekingcs.github.io/MIA/**.
  - It is live once Zac switches Pages on in the repo settings.
- **The preview is always the demo:** on `*.github.io`, `web/mia.js` always runs the demo.
  - It reads `../schema/life_state.example.json`.
  - Actions and Talk are off.
  - Nothing private can reach it.
- **Linking between pages:** links between your pages keep working there, because the demo no longer depends on `?demo` in the address.
- **The glasses composition:** `web/glasses/` (or whatever you name it) gets published the same way. Zac can load that URL on the glasses when he has them.

## Two things I noticed (yours to decide)

1. **Missions and Skills render in a serif font.**
   - `missions.html` and `skills.html` never set `font-family` on `body`; only Home does, in `home.css`.
   - So the browser falls back to its default serif.
   - A `body { font: … var(--font) }` in `components.css` would fix it, unless the serif is intended.
2. **Home has no way to reach Missions or Skills.** Missions and Skills have the sidebar, but Home has no nav. On the phone preview, Home is a dead end.

## H-0013

Received. Claude takes it next:
- Missions with campaigns, objectives and rewards.
- Per-skill XP, levels and thresholds.
- Character level.
- An honest answer on rarity: the engine doesn't tier anything today, so that one stays unapplied, as you planned.

The reply goes on H-0013.

## Acceptance criteria
- Zac can open the preview URL on his phone and see Home, Missions and Skills on placeholder data.
- Your call on the two notes above.
