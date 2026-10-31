# Active Training: Audit and Proposal

*Claude, 2026-10-30, from Zac's "MIA – Active Training System" spec. An
architectural analysis and implementation proposal; no production code
changed. Proposed as DEC-0055. Zac's direction for now: **reps are
counted by voice** (the person says each number as they go, or tells MIA
the total after), and **MIA counts along with them**.*

## 1. What already exists (the audit)

MIA already has most of the pieces. What's missing is the **live
session**: one workout in progress that every surface (PC, phone,
glasses, voice) shares, moving set by set.

| Spec component | What exists | Where |
|---|---|---|
| Workout Manager (routines, schedule) | The **fitness plan**: training days (owned by the Loop since DEC-0052), a **rotation** of training days, each with exercises `{name, sets, reps, hold_seconds}`; `today_training()` picks today's day; training reminders | `core/fitness_manager.py`, `core/the_loop.py`, `web/plan.js` |
| Exercise library | Exercises (name, muscle group...) | `core/workout_manager.py` |
| Workout History | **Sessions** with `sets_logged` (exercise, reps, weight per set), real elapsed time; **personal records** (heaviest weight, ties by reps) and per-exercise progress | `core/workout_manager.py`, `web/workout.js` (Log Session, History, Personal Bests) |
| Training Clock | A live session with a **stopwatch and rest timer**, but desktop-only and in memory (`modules/workout/module.py`); a **practice timer** for holds on the web Today tab (`web/workout.js`) | two partial clocks, neither shared |
| Steps of today's workout | `complete_step()`, `steps_done()`: each exercise of today's training ticked; "step one of today's workout complete" by voice | `core/fitness_manager.py`, `core/quick_commands.py` |
| Skill practice (holds, reps) | `log_skill()` with seconds or reps, best hold / best reps, the "new best" moment | `core/fitness_manager.py`, `web/workout.js` |
| Mission Integration | **Fitness missions from the plan**: "Training: <day>" with each exercise as an objective, "Workouts this week", skill practice. **"The logs are the truth"**: objectives are recomputed from the logs (`sync`), so logging lands everywhere at once; never punitive (DEC-0014) | `core/fitness_missions.py` |
| XP, skills, stats, rewards | `grant_xp()` with skill weights on every logged session; skills (Hero's Path); character stats (Strength from lifts and workouts, Stamina from workout minutes); rewards ladders (workout hours); buffs | `core/gamification.py`, `core/skill_manager.py`, `core/character_stats.py`, `core/rewards_manager.py` |
| Events | A synchronous **event bus** (`workout.logged` and others) and **life events** (the history: `workout_logged`, `training_done`, `training_step`...) | `core/event_bus.py`, `core/life_events.py` |
| Voice Coach | Talk on every surface; **quick commands** done by code with undo ("workout complete", "finished my pull-ups", "handstand 45 seconds"); **Kokoro** voice on the PC (DEC-0051); the phone speaks with Android's TTS; on the **glasses**, MIA hears through the phone (Bluetooth headset mic, Android's on-device recognizer) and answers through their speakers; the glasses' heads-up feed shows XP and wins | `core/quick_commands.py`, `core/voice_manager.py`, `core/glasses_voice.py`, `core/glasses_feed.py`, `android-phone/.../Voice.kt`, `ListenService.kt` |
| Glasses display | The glasses web app (DEC-0016): app cards, quick-action menus, a heads-up feed, her orb | `core/glasses.py`, `web/glasses.*` |
| Performance Analyzer | "Is it working?" (four weeks of training, the weight line, in one sentence); personal bests; skill momentum | `core/web_fitness.py`, `core/skill_patterns.py` |
| Exercise Recognition / Rep Counter | **Nothing.** No camera vision, no motion sensors, no rep detection | — |
| Wearables | **Nothing connected.** The game layer plans a watch (Vitality, Stamina, a run HUD) and stats say what a watch would add; nothing reads one | `docs/GAME_LAYER.md` #12 |
| Glasses camera | **Not available to web apps.** Photo capture only through Meta's Device Access Toolkit in the phone app, explicit capture (DEC-0029, DEC-0030 phase F) | — |

**Two things to fix while building, not around:**

1. **Two clocks, two live sessions.** The desktop Workout module keeps
   its own in-memory session; the web has a separate practice timer.
   The new live session replaces both as the one clock (the desktop and
   web screens show it), not a third.
2. **"Done" is written twice.** A finished exercise is today both a
   `training_step` tick (fitness) and, if logged, a session's sets
   (workout). Under DEC-0052's one-owner rule: **what was performed is
   the session's** (sets, actual reps, weight); a training step is done
   when the session shows that exercise's prescribed sets done, and a
   tick without a session (today's quick "finished my pull-ups") still
   works by writing a one-exercise session. Prescribed stays the plan's.

## 2. Technical limits

- **Meta glasses camera:** not reachable from the glasses' web app; the
  Device Access Toolkit gives the phone app photo capture, not a live
  video stream to analyze. Camera rep counting on the glasses is not
  possible today; it waits on Meta.
- **Phone camera vision:** possible later (on-device pose estimation,
  e.g. MediaPipe Pose, in the phone app), but the phone must be propped
  facing you, it costs battery and heat, and accuracy varies by exercise
  (squats and push-ups well; curls, planks and pull-ups less so). Not
  phase 1.
- **Apple Watch:** it only pairs with an iPhone, and Zac's phone is
  Android, so it can't be the wearable here. Wear OS or a Galaxy Watch
  through **Health Connect** is the realistic path (heart rate, workout
  sessions); live rep counting from a watch needs a companion watch app,
  a project of its own.
- **Voice in a gym:** Android's speech recognizer listens one utterance
  at a time; counting aloud through a set means listening continuously,
  restarted between utterances, which drains battery and must be clearly
  on only during a session. Noise and breathing make single numbers
  ("six", "sex", "fix") easy to mishear: the counting rules (section 4)
  are built for that.
- **Latency:** MIA counting along must be instant. A count spoken by the
  engine on the PC and sent to the phone would lag; the cadence count
  is spoken **on the phone** (it's where the voice comes out, glasses
  included), and only the set's result goes to the engine.

## 3. Architecture (following MIA's conventions)

One new core piece, the **live session**, and everything else reused.

```
plan (fitness_manager, the Loop)  ──►  core/training_session.py  ──►  workout_manager.add_session()
   prescribed: exercises, sets,        the live session: where you      what was performed (the truth)
   reps, holds, rest                   are, the clock, each set's            │
                                       actual reps and how they were         ├─► fitness missions sync (logs are truth)
voice ("start my workout",             counted                               ├─► grant_xp, skills, stats, rewards, PRs
"next set", "I got 12") ──────────►    (one session, shared by every         └─► life events, event bus, glasses feed
quick commands / action kinds          surface through /api/state + /api/live)
```

- **`core/training_session.py`** (new): the one live session per
  person. State: the day's exercises (copied from the plan at start:
  name, prescribed sets/reps/hold, rest), the current exercise and set,
  each set's **actual** reps (or seconds), **how they were counted**
  (`said` each number aloud, `told` the total after, `cadence` MIA
  counted and they confirmed, `tapped`), the clock (started, paused,
  rest until). Persisted through `atomic_write_text` while it runs (a
  phone restart or a PC sleep doesn't lose a workout) in the person's
  folder (a personal store), and undoable. Pure functions for the
  transitions (start, set done, rest over, next, skip, pause, resume,
  finish) so the rules are testable without a clock.
- **Changes are action kinds** (`core/actions.py`): `training.start`,
  `training.set` (reps, weight, how counted), `training.next`,
  `training.skip`, `training.pause`, `training.resume`, `training.finish`,
  `training.correct` ("make that 10"). The web, the glasses and voice
  all go through them (DEC-0013): no logic in `web/`.
- **Voice is quick commands** (`core/quick_commands.py`), done by code,
  instantly, no model: "start my workout", "pause", "resume", "next
  set", "skip this exercise", "I'm done", "repeat that", "I got 12",
  "make that 10", "how am I doing?" (answered from the session). A
  workout already uses this path ("workout complete").
- **On finish**, the session becomes one `workout_manager` session
  (sets, actual reps, weights, real elapsed time), and that existing
  path does the rest: XP and skills, personal records, character stats,
  rewards, life events, `workout.logged` on the bus, the fitness
  missions' sync. **No new event system**: the spec's events map onto
  what's there (ExerciseSetCompleted and RestPeriod* are life events of
  the session; WorkoutCompleted is `workout_logged`). The event bus and
  life events are already how other modules (walking, gardening,
  woodworking quests) can listen later.
- **What it shows**: assembled in core (`core/web_fitness.py` gains the
  live session), drawn by the Workout screen's Today tab (phone, PC
  through `web_home`) and a glasses card: exercise, set *n* of *m*,
  reps *x* / target, the rest countdown, next up, session time. The
  desktop's old in-memory session is retired in favour of it.
- **The phone app's part**: while a session runs, a "workout listening"
  mode (continuous on-device recognition, numbers only, a visible
  indicator, off when the session ends or pauses), the cadence count
  spoken locally, and the set's result sent as `training.set`.

## 4. Counting reps by voice (phase 1, Zac's direction)

Three ways a set gets its count, all honest about which one it was:

1. **You count aloud** ("one, two, three..."): MIA listens and follows.
   Rules against mishearing: the count is the highest number heard *in
   sequence* (a number one more than the last, or two more when one was
   missed); a repeat of a number already heard is ignored (no double
   counting); an out-of-sequence number ("six" after "two") is ignored.
   Saved as `said`, with the numbers heard.
2. **MIA counts with you** (her cadence): she says the numbers at a
   steady pace you set per exercise ("two seconds a rep"), so you move
   to her count, like a coach. When you stop or say "done", she says
   where she was ("that was twelve") and asks you to confirm or correct
   ("make that ten"). Saved as `cadence`, confirmed. Her count is a
   pace, not proof: it's never recorded as reps you did until you
   confirm them.
3. **You tell her after**: "I got twelve", "eight and eight", "all
   fifteen". Saved as `told`.

**Prescribed vs actual, always**: the set holds both (target 15, did 12);
missions and XP credit what was done; a short set is a set, not a fail
(DEC-0014). "Never claim a repetition was verified": none of these is
verification, and the record says how each count was made.

## 5. Mission integration

The fitness missions already recompute from the logs, so the session
only has to write the log, and "Training: <day>" fills in itself: an
exercise objective is done when its prescribed sets are logged (actual
reps recorded alongside). "Workouts this week" counts the session.
**Project: Iron Foundation**-style missions are ordinary missions whose
objectives point at the same logs (sets done, reps done, rest kept),
which `fitness_missions` can generate from a plan block. XP: the
existing per-session grant and mission rewards, based on **actual**
work. Rest intervals kept: recorded per set (rest taken vs prescribed)
so a "keep your rest" objective is real, never estimated.

## 6. Adaptive coaching (phase 5)

All derived from the session history (`workout_manager`), worded by the
existing personality rules, never punitive:
- **Progressive overload**: when an exercise hit its target on every set
  for its last N sessions (N = 2 to start), MIA proposes a new target
  (+1 to +2 reps, or +5 lb where weight is logged) as a plan change
  (Propose → Approve), never by herself.
- **Struggling**: two sessions in a row well under target, she proposes
  easing it, or a rest week; long overtime weeks already show in the
  findings (`overtime_and_training`).
- "How am I doing?" mid-session: this set vs last session's same set.

## 7. Privacy and security

- Listening only during a session, visibly, on-device recognition
  (`EXTRA_PREFER_OFFLINE`, already set); no audio recorded or sent; only
  the words that matter ("twelve", "next") reach the engine.
- The session is the person's own (a personal store); children get it
  without weights or body measures (as fitness does now).
- Future camera counting: on-device only, no video stored or sent, an
  explicit start every time; the glasses camera only through Meta's
  toolkit with its own consent.
- No new network access; nothing leaves the home computer and phone.

## 8. Roadmap and tests

| Phase | What | Tests |
|---|---|---|
| 1 | `core/training_session.py` (state, pure transitions, persisted), the `training.*` action kinds, finish → one `workout_manager` session, the training-step ownership fix, the live session on the Workout screen's Today tab | transitions (start, set, rest, next, skip, pause/resume, finish), prescribed vs actual, a short set, finish writes one session and the missions sync, undo, a restart mid-session |
| 2 | Voice: quick commands for every spoken control and "I got 12" / "make that 10"; "how am I doing?"; rest announcements | `parse()` for each phrase (and things that aren't commands), live on the PC's model for the ones that reach it |
| 2b | Counting by voice: the counting rules in core (pure, so the phone and the PC share them), the phone's workout-listening mode and local cadence count, the glasses card | the sequence rules against misheard numbers (repeats, skips, out of order), cadence count confirmed or corrected; on-device with the glasses |
| 3 | Mission blocks (Iron Foundation-style), rest kept as an objective | missions credit actual work only |
| 4 | Adaptive coaching (proposals for new targets, easing when struggling) | proposals only after N sessions on target; nothing changes without approval |
| 5 | Wearables: Health Connect (heart rate, sessions) on Android | — |
| 6 | Camera counting on the phone (on-device pose), when phases 1 to 4 are in use | per-exercise accuracy measured before it's offered |

## 9. Questions for Zac

1. Approve phase 1 and 2 as above (the live session replacing the
   desktop's in-memory one and the web's separate timer)?
2. Cadence: MIA counts at a pace you set per exercise, and you confirm
   the total at the end. Is that the "counting with you" you mean, or
   should she echo your own numbers back as you say them?
3. Rest: start automatically when a set is logged (as the spec says),
   with "skip rest" to move on early?
4. A watch later: Galaxy Watch / Wear OS through Health Connect (an
   Apple Watch can't pair with an Android phone).
