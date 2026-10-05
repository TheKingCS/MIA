# H-0005: Where MIA is, what she needs, and a proposal for Phase 2
- From: claude · To: zac, muse, chatgpt · Date: 2026-10-05
- Related: DEC-0005, DEC-0012, DEC-0013, Q-0007, Q-0008, Q-0009,
  `docs/vision_assets/user_os_concept.png`, `docs/design_handoff/`

## Context: an honest picture

Zac's read is right: **the back end is far ahead of the front end.**

| | Where it is |
|---|---|
| **Engine** | Strong. 37 apps' worth of real data and logic, ~185 Assistant tools, voice, households and accounts, history, links, Life State v2, `/api/state`, 4,160 tests. |
| **Desktop UI** (PySide6) | Works, but it looks like a utility, not the concept art (`docs/vision_assets/user_os_concept.png`). Home is a clock, a greeting and an "Open Apps" button (`docs/design_handoff/screens/00_main_window_home.png`). There's no presence orb, no quest feel, and the 37 apps are separate pages with uneven styling. |
| **Phone** | A small web app (Talk, Today, Money) and an Android app. They work, but they're plain. |
| **Glasses** | Not started (waiting on Q-0003). |
| **Muse's designs** | Good, but they live only in design artifacts. **Nothing Muse designs reaches the real app, because the real UI is Qt code that only Claude can write.** |

That last row is the real bottleneck. With two designers' output going
through one engineer's hand-translation into Qt stylesheets, the front
end will always lag, and Qt can only approximate the glowing, layered
HUD in the concept art.

## The proposal (DEC-0012): MIA's interface becomes a web front end that Muse builds

MIA already runs a local web server (`server/app.py`, FastAPI) that
serves the phone. Make that the home of **one front end for every
screen**:

```
MIA ENGINE (Python, Claude)  ──  /api/state (read) · /api/actions (write) · /api/live (updates)
                                        │
                  web/  (HTML · CSS · JS, Muse)  ← one front end, in the repo
                 ┌──────────────┬───────────────┬───────────────┐
              Desktop        Phone          Glasses        any browser
     (PySide6 window showing   (same pages,   (cards from the  on the home
      the local web UI: kiosk   phone layout)  same components) network
      and fullscreen unchanged)
```

- **Muse writes the front end directly**, in its native medium (HTML,
  CSS, JS), committed to `web/` in the repo. No translation step.
- **Claude provides the APIs** each screen needs and keeps them
  tested. The engine never knows about the UI (DEC-0005).
- **The desktop stays a desktop app.** The PySide6 shell keeps boot,
  kiosk mode, fullscreen, voice and the Pi integration. It shows the web
  UI in a built-in browser view (QtWebEngine, already in our PySide6).
  Everything is offline: all files are local, nothing loads from the
  internet.
- **Nothing is thrown away.** The 37 Qt screens keep working, and the
  web UI links to the ones not yet redone. Screens move over one at a
  time, highest value first.
- **One design system:** Muse's tokens (colors, type, spacing) live in
  one file used by every surface.

**Trade-offs, honestly:**

- **Performance:** a web view uses more memory than Qt widgets. Fine
  on a Pi 5 (8 GB), but it needs checking there early. Step 1 below
  includes that check, and a fallback (the Pi's own Chromium in kiosk
  mode) if the built-in view isn't available on the Pi.
- **Quality across two languages:** the front end becomes JavaScript as
  well as Python. Claude will add tests for the APIs, and smoke tests
  that load each web screen.
- **The other path (DEC-0012 option B):** keep Qt. Muse designs and
  Claude implements every screen in Qt. Less change, but the bottleneck
  stays, and the concept-art look stays out of reach.

## What MIA needs: Phase 2, "Experience" (DEC-0013)

In order. Each step is small, shippable and visible to Zac:

1. **Decide DEC-0012** (Zac, with Muse's and ChatGPT's input: Q-0007,
   Q-0008).
2. **Foundation (Claude):**
   - `web/` served by MIA, plus the desktop window showing it.
   - **The action API:** surfaces can *do* things (mark a bill paid,
     check off a chore, log a workout), always as propose-then-approve,
     recorded in the history and undoable (DEC-0009).
   - **Live updates:** a screen refreshes the moment something changes.
   - The Pi check.
3. **First slice: Home and MIA's presence (Muse, on Claude's
   foundation).** Muse's own Q-0004 design: the presence orb (idle,
   listening, thinking, celebrating, needs-you), the single due item, and
   the briefing (wins, friction, questline, money). Real data from
   `/api/state`, on the desktop and the phone. **This is the "she feels
   like MIA" moment.**
4. **Talk:** voice and chat inside the new Home. The engine and voice
   already exist; this is the UI around them.
5. **Then the domain screens, one at a time,** each with its own
   handoff: Quests (Missions and Skills, the RPG feel), Money, Garage
   (`assets`), Kitchen, Workout, then the rest. Each moves when its web
   version is better than the Qt one.
6. **Glasses cards** from the same components, once Q-0003 is answered.
7. **Alongside (Claude and ChatGPT):** Phase 2 reasoning, so
   "opportunities" stops being PLANNED. MIA proposes missions from Life
   State, through the communication gate.

**Meanwhile, Zac:** entering real data through MIA is what makes all of
this feel alive (NEXT_SESSION). An empty MIA looks empty in any design.

## What's needed from each of us

- **Zac:** read this, then approve, change or reject DEC-0012 and
  DEC-0013 (just say which).
- **Muse:** answer Q-0007 (can you write and commit production HTML,
  CSS and JS into `web/`?) and Q-0009 (the "Witness Principle"). If
  DEC-0012 is approved, start the design tokens and the Home/presence
  components against `docs/schema/life_state.example.json`.
- **ChatGPT:** answer Q-0008, a vision review of this direction.
- **Claude:** nothing new is built until Zac decides. Then the
  foundation (step 2) first, so Muse has a real server and APIs to build
  on.

## Acceptance criteria for Phase 2's first milestone

- MIA boots into the new Home on the desktop (kiosk and fullscreen
  unchanged) and on the phone, from the same `web/` code.
- Home shows the presence and the one due item from `/api/state`, and
  updates live when a bill is paid elsewhere.
- One action works end to end from the new UI (for example "mark paid"):
  proposed, approved, recorded in the history, undoable.
- It runs offline on a Pi 5 at a smooth frame rate.
- Every old screen is still reachable.
