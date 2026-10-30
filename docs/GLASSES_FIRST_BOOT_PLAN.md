# First Boot, User Sync and the Presence System: wiring plan

*Claude, 2026-10-29. Status: PROPOSAL, waiting on Zac. Nothing here is built yet.*

The design lives on the canvas "MIA Glasses First Boot" (the first boot,
phases 1–9, the Hey MIA frames and the Presence System lab). Zac's brief
for it is "MIA — First-Time Initialization & Onboarding" (2026-10-29),
plus his notes from the same day:

- Immersive drops its side panels; Conversational is the main look.
- Ambient shows the whole conversation as a log you can scroll.
- Animations run slower; MIA talks the person through the introduction.
- **User Sync is where MIA gets to know the person**: phone permissions,
  plus a real conversation about their life, routines, hobbies, meals,
  workouts, work. Everything MIA needs to fill the system (missions,
  workouts, the recipe book, the calendar) comes from that conversation.
- While MIA is idle, a tip reminds the person of something she can do.

This plan says how each screen gets its words and buttons from the
engine, what already exists, what's missing, and the order to build it.
It follows the rules already in place: the surface holds no logic
(DEC-0013), every change goes Propose → Approve → Execute → Record →
Undo (`core/actions.py`), facts are put together in code and the model
only phrases them, and nothing is invented.

---

## 1. What already exists (REAL)

| Piece | Where | What the design uses it for |
|---|---|---|
| Glasses web app, 600×600, orb home, two-gesture approve | `web/glasses.html`, `web/glasses.js`, `web/glasses.css` | The frame every glasses screen sits in |
| App cards + quick menus, child-safe, favorites pinned | `core/glasses.py` → `/api/glasses`, `/api/glasses/{app}/{item}` | Phase 8 app menu, Home tiles |
| One line of status per app | `core/web_surfaces.py` `dashboard()["glance"]` | The line under each app |
| App names and taglines ("Know where it goes.") | `core/web_surfaces.py` `APPS` | The fixed half of an app's intro |
| Voice through the phone, answers shown on the glasses | `core/glasses_voice.py` → `/api/glasses/voice`; `core/glasses_feed.py` → `/api/glasses/feed` | Hey MIA, Listening, Speaking |
| One shared conversation across phone, web and glasses | `/api/talk/thread` (`server/app.py`) | The Ambient chat log |
| Actions with undo, run as the person who approved | `core/actions.py` → `/api/actions` | Every chip MIA proposes in User Sync |
| When to re-read | `core/live.py` → `/api/live` | Screens updating while the conversation runs |
| First account on the phone (name, email, country, what you want help with) | `core/first_account.py` | Phase 2 starts from here |
| A one-time, scripted first welcome (Qt desktop only) | `core/onboarding.py` | Replaced on the glasses by Phase 3 |
| Starter sets (chores, upkeep, fitness, student...) | `core/starter_templates.py` | Raw material User Sync can propose from |
| "Has this person ever opened X" | `core/usage_tracker.py` | Tours and which tips to show |
| Freedom fund, savings, builds, pace | `core/freedom.py` | Budget's "your trip fund lives here" line |
| How things relate (stated and derived links) | `core/links.py` | "...and it feeds your missions" |
| Memories about the person | `core/user_memory_manager.py` | Anything from User Sync that has no app yet |
| Missions, objectives, XP | `core/mission_manager.py`, `mission.add`, `objective.add`, `objective.tick` | The "Know your system" mission |

Action kinds that User Sync can already propose (they exist in
`core/actions.py` and its extensions): `event.add`, `mission.add`,
`objective.add`, `fitness.plan`, `fitness.habit`, `meal.plan`,
`grocery.add`, `place.add`, `freedom.plan`, `budget_target.set`,
`profile.edit`, `setting.set`.

## 2. What's missing

### A. First-boot progress (PLANNED → engine)

A personal store, `first_boot.json` in the profile folder (added to
`PERSONAL_STORES`), holding which phase each person reached, so
onboarding can be **resumed** on any device and skipped parts come back.

- `core/first_boot.py`: `state(context)`, `advance(phase)`, `skip(phase)`.
- `/api/first-boot` (GET) for the screens; action kinds
  `firstboot.advance` and `firstboot.skip` so it records and undoes like
  everything else.
- A life event when the first boot finishes (`life_events.record`).
- Life State: a small `onboarding` section, status REAL.

### B. User Sync: the conversation (PLANNED → engine; the hard part)

`core/user_sync.py`. The questions are **written in code**, by topic, the
way `core/onboarding.py` scripts the first welcome: it's the
highest-stakes conversation MIA has, so it can't depend on the model
choosing what to ask. Topics, in order: You, Routines, Work, Meals,
Workouts, Hobbies, People, Money (each skippable, "let's finish later"
pauses it).

For each answer:

1. **The model extracts, the code decides.** The model (qwen2.5:14b on
   the PC) gets one topic's answer and returns JSON in a fixed shape per
   topic (Meals: `{"dishes": [...], "prep_day": "...", "avoid": [...]}`).
   The code checks it against the shape and throws away anything that
   doesn't fit, as `settle_on_named_tool` already does in
   `core/assistant_chat.py`.
2. **Each fact becomes a proposal**, using an existing action kind where
   there is one (`event.add` for a weekday routine, `fitness.plan` for
   push/pull/legs, `mission.add` for Sunday meal prep, `meal.plan`), and a
   memory for anything with no app yet. These are the chips on screen
   ("Recipe book · Chicken & rice bowls").
3. **The person approves.** "Looks right" approves the topic's chips in
   one go; "not that one" drops one. Nothing is written before a yes;
   everything written can be undone.
4. **Nothing invented.** If the model returns nothing usable, the answer
   is kept as a memory and MIA moves on. She never fills a gap with a
   guess.

Gaps found while writing this:

- **There is no action to add a recipe** (`recipe.delete`, `.rate`,
  `.favorite`, `.ingredients` exist; adding one doesn't). It needs a
  `recipe.add` kind on top of `core/kitchen_manager.py`.
- **There is no action to add a memory** (`memory.fix` and
  `memory.forget` exist). It needs `memory.add`, so "remember that" is
  approvable and undoable like the rest.
- Workouts: `fitness.plan` sets a plan. Checking whether it can hold a
  named split (push/pull/legs, four days) is the first job of that slice.

**Phone permissions** (Phase 4's first frame): only the phone can ask
the OS for calendar, health, location, notifications and photos. The
phone app reports what was granted to `/api/first-boot/permissions`; the
glasses show only what was reported (REAL), never a guessed percentage.

**Testing it:** a fixed set of sample answers per topic, each with the
proposals it must produce, run against the real model, the same way the
213-question set checks the Assistant. A topic doesn't ship until it
passes.

### C. Orb states (PLANNED → engine + glasses)

The six states from the lab need one signal: what the voice pipeline is
doing.

- `core/glasses_voice.py` and the phone's listening loop record the state
  (`listening`, `processing`, `speaking`, `idle`, `interrupted`) as each
  step starts; it's served with `/api/glasses/feed` and bumps
  `/api/live`.
- `unavailable` is decided on the glasses: no answer from the engine.
- `web/glasses.js` only switches a class on the orb (`st-listening`...),
  copied from the lab. No logic.

### D. Ambient chat log (glasses only)

`/api/talk/thread` already returns the whole conversation. Ambient
renders it as a log you can scroll (newest at the bottom), with the
small orb in the corner. Nothing new in the engine.

### E. Idle tips (PLANNED → engine)

`core/tips.py`: a list of tips, each naming the tool or action kind it
relies on, so a test fails if a tip promises something MIA can't do.
Picked for the person: features they've never used first
(`core/usage_tracker.py`), nothing a child can't use (`CHILD_APPS`),
none repeated in the same day. Served with the glasses' home. A tip is
something shown on screen while idle, not a message sent to the person,
so it doesn't go through the communication gate. If Zac wants tips read
aloud or sent to the phone, they would go through the gate.

### F. App intros ("Spending, bills and savings goals. Your trip fund...") (PLANNED → engine)

This is the example Zac asked about. It's two halves:

1. **What the app is**: fixed text, a longer version of the tagline that
   already lives in `APPS`. STATIC.
2. **What's already here for you**: lines put together in code from the
   person's own data, and only when the data exists. For Money:
   - the Freedom fund's name and balance, from `core/freedom.py`;
   - "it feeds your missions" only if `core/links.py` holds a link from
     a mission to that fund (stated, or derived from the mission's
     objective). With no link, the sentence isn't said.
   - anything set up during User Sync, read back from the life events
     it recorded ("from earlier" means it came from User Sync).

   `core/app_intro.py`: `app_intro(context, module_id) -> {"what": ...,
   "yours": [lines], "status": "DERIVED"}`, served as an `intro` item
   of the existing `/api/glasses/{app}/{item}` (a new route beside it
   would collide with that pattern). The model may smooth the wording but gets
   only these facts, as everywhere else. One builder per app, written
   when that app's tour is written. Money, Kitchen, Workouts and Missions
   come first, because User Sync fills those.

### G. Tours (PLANNED → engine)

Per-app tour progress (never started, step N paused, done) in a personal
store next to first-boot progress, `/api/tours`, and actions
`tour.start`, `tour.step`, `tour.skip`. The steps are real screen
elements (the app's own menu items in `core/glasses.py`), highlighted in
place, not pictures of them.

### H. The first mission, "Know your system" (REAL pieces, new content)

Created with `mission.add` at the end of Phase 5, with objectives Meet
MIA, Tour your Home, Explore the app menu, Say "Hey MIA" on your own.
Each objective ticks itself (`objective.tick`) from an event that
already exists or is added in A, C or G (first boot finished, tour done,
a voice turn started by the wake word). XP from the existing game layer.

## 3. Build order

Each slice ends with something Zac can try on the glasses.

1. **Orb states + Ambient log** (C, D). Small, no new stores; the lab
   becomes real.
2. **First-boot progress + the cinematic Phases 1–3** (A). Resumable,
   with Skip, Pause and captions.
3. **User Sync, one topic end to end: Meals** (B): `recipe.add`,
   `memory.add`, the extract → propose → approve loop, its test set.
4. **The rest of User Sync**: Routines, Workouts, Work, Hobbies, People,
   Money; phone permissions.
5. **App intros + tours + the first mission** (F, G, H).
6. **Idle tips** (E).

## 4. The guardrail (`docs/ENGINE_PHASE1_PLAN.md` section 9)

| | First boot | User Sync | Orb states | Tips | App intros | Tours |
|---|---|---|---|---|---|---|
| Exists? | No (Qt welcome only) | No | No | No | Half (tagline) | Half (usage) |
| Engine or UI? | Engine | Engine | Engine signal, UI look | Engine | Engine | Engine |
| Duplicates something? | Replaces `core/onboarding.py` on glasses | Reuses action kinds and stores | Reuses feed + live | Reuses usage tracker | Reuses freedom, links | Reuses glasses menus |
| Life State? | Yes, small section | No (its results are) | No | No | No | No |
| Life event? | Finished | One per approved proposal | No | No | No | Tour done |
| Links? | No | Yes, stated, when an answer relates two things | No | No | Reads them | No |
| `/api/state`? | Yes | No | No | No | No | No |
| Status | PLANNED | PLANNED | PLANNED | PLANNED | PLANNED (then DERIVED) | PLANNED |

## 5. Zac's answers (2026-10-29)

1. **Where User Sync happens: both**, and **the glasses must work on
   their own: the phone app doesn't have to be open** to answer by
   voice. The phone shows the same conversation and lets the person type
   instead.
2. **Approving: per topic.** One "looks right" saves a topic's chips;
   "not that one" drops one.
3. **Length: 10–15 minutes**, about 2–3 questions per topic, then MIA
   offers to keep going or finish later.
4. **Tips: glasses and the phone's home, slowly**: a new tip every few
   minutes while idle, none repeated the same day.

### What answer 1 changes

Today the glasses hear through the phone app: the glasses are a
Bluetooth headset and the app runs Android's speech recognizer
(`core/glasses_voice.py`). If that only works while the app is on
screen, talking on the glasses alone breaks. So before slice 1:

**Slice 0: glasses voice with the phone app closed.**
- Check what happens today with the app in the background and the phone
  screen off (on Zac's phone with the glasses).
- If it stops: run the listening in an Android foreground service (the
  persistent "MIA is listening" notification), started by the app and
  kept alive without the app open. Wake word on the phone side, so
  "Hey MIA" works hands-free.
- Later, when the Meta toolkit's own microphone access is available
  (DEC-0016), it can replace the Bluetooth route without changing the
  engine side.
- One thing that stays on the phone: Android only lets the person grant
  permissions (calendar, health, location...) on the phone's screen, so
  during Phase 4 MIA says "tap Allow on your phone" for each one. That's
  the only time the phone needs to be picked up.

Build order becomes: 0 (voice without the app open), then 1–6 as above.

### Slice 1: built 2026-10-30, checked in a browser at 600×600

- `core/glasses_feed.py`: `set_orb()` / `orb()`, in memory, per person; a
  state nobody ended runs out, so she never stays stuck. Served as
  `/api/glasses/orb` (GET for the screen, POST for the phone), with no
  turn lock so "thinking" still answers during a turn. A phone linked to
  the home computer passes the state on. The state names are listening,
  thinking, speaking, interrupted, idle (the brief's "Processing" is
  "thinking", the word `web/glasses.js` already used).
- `Voice.kt` reports each step. `web/glasses.js` polls every 1.2 s and
  the orb follows. Three missed answers in a row: the grey offline orb
  and "I can't reach your system right now." It recovers by itself.
- **Ambient:** the Conversation card, one move back from the orb, opens
  the log (the shared thread, up to 200 messages, `/api/talk/thread?limit=`)
  with the small orb in the corner. Move scrolls; select talks; back
  returns to the orb. New turns appear in it.
- Not covered by that check: the phone sending real states, since that
  needs the app on a phone (a headset works; the glasses arrive
  2026-11-04), and the real thread's look at full length.

### Slice 0: written 2026-10-29, compiled and started on the emulator; not yet tested on a phone

In `android-phone/` (the MIA phone app):

- `Engine.kt`: starting MIA's engine moved out of the screen, so it can be
  started without the screen.
- `ListenService.kt` (new): a microphone foreground service with a quiet
  **"MIA · Ready"** notification (Talk, Stop). It starts the first time
  you talk to MIA from the app (Android only allows that while MIA is on
  screen) and then stays until Stop. A **tap on the glasses** (or any
  headset's play/pause) reaches it through a media session, screen off
  included, and MIA listens once. If Android closed MIA's engine in the
  meantime, it starts her again first. Same pattern as the companion
  app's `VoiceService` (`android/`).
- `Voice.kt`: now owned by the service, not the screen; a tap while she's
  talking interrupts her; reports listening / thinking / speaking / ready
  to the notification (slice 1 sends the same states to the orb).
- `ListenTile.kt`: with MIA ready, the Quick Settings tile listens on the
  spot, lock screen included, instead of opening the app.
- Known trade-off: while MIA is ready, the glasses' or headset's
  play/pause goes to MIA, not your music. Stop in the notification gives
  it back.

**Test on Zac's phone with the glasses** (after the "MIA on the phone"
build publishes the new APK):

1. Install the new APK over the old one. Open MIA, use the tile or a
   screen's mic once, allow the microphone and notifications. "MIA ·
   Ready" appears.
2. Ask something. Then close MIA (swipe it away from recents) and lock
   the phone.
3. Tap the glasses' touchpad (or press play/pause). Expected: a beep, MIA
   listens through the glasses, answers through their speakers, and the
   notification goes Listening → Thinking → Speaking → Ready.
4. Leave it 30 minutes locked, then tap again (checks Samsung didn't put
   MIA to sleep; if it did: Settings → Apps → MIA → Battery →
   Unrestricted).
5. Tap while she's answering: she stops and listens.
6. Press Stop in the notification: the tap goes back to your music.

What could still fail, to watch for: whether the glasses' tap is sent as
a play/pause button at all (if not, the tile and the notification's Talk
still work, and slice 0 needs the Meta toolkit's own input); whether
Android's speech recognizer accepts being started from a service on the
A54 (if not, the companion app's own recorder is the fallback).
