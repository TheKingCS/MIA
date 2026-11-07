# Workout: design brief

*Claude, 2026-11-07, for H-0087 (pilot one). A **brief**: what the design must cover, grounded in what exists. Muse
turns it into the spec once the identity's round one is approved. Template: `TEMPLATE.md`.*

**Status:** brief · **Maturity now:** 3 (Integrated) · **Target:** 5 (Trusted: used in real workouts)

## 1. Purpose and intended experience

A training partner that knows the plan, runs the workout with you, counts with you, rests you, notices progress and
tells the truth about it. You should be able to train **without touching the screen**: start by voice, count by
voice, rest by itself, finish by voice, and look at the screen only because it's good to look at.

## 2. Existing functionality (preserve all of it)

- **Engine:** `core/fitness_manager.py` (the plan: training rotation, skills with steps, meals, milestones, weigh-ins,
  bests); `core/training_session.py` (the live session, shared by every surface: prescribed vs performed, set by set,
  rest starts by itself, pause, corrections, how each count was made); `core/training_actions.py` (`training.*`);
  `core/workout_manager.py` (sessions, exercises, PRs); `core/fitness_missions.py` (daily and weekly missions from the
  plan, progress from the logs); `core/web_fitness.py`, `core/web_screens.workout_page`; `core/plan_import.py`.
- **Screens:** `web/workout.html` (Today with the live session, Count With Me, rest countdown; Progress; Log Session;
  Exercises; History; Personal Bests), `web/plan.html` (the plan), the glasses' Workout card with Active Training.
- **Voice:** "start my workout", numbers as counts, "next set", "pause", "make that ten", "how am I doing?", "I'm done".

## 3. Navigation (proposed)

Home view **Today** (what's on, Start) → **Active** (full screen, the live session) → **Done** (the summary, PRs, XP)
· **Progress** · **Plan** (`plan.html`) · **History** and **Exercises** inside Progress.

## 4–8. Screens to design

1. **Today**: the day's training (or rest day, which counts), the missions, a single big Start; last session; the
   week's dots.
2. **Active workout** (the flagship moment, the "focus" surface): the exercise large; set *n* of *m*; target reps or
   hold; **the count in progress** with how it's being counted (said, MIA's pace, told, tapped); weight; big targets
   for set done, skip, pause; the orb small and listening.
3. **Rest**: a ring draining (`rest_left`), the next exercise previewed, skip rest; a sound at the end.
4. **Done**: what was performed against what was prescribed, PRs (gold), XP and skills earned, missions moved.
5. **Progress**: is it working (the sentence that exists today), volume and frequency over weeks (charts, design
   system §8), the weight line, bests, milestones.

## 9. States

Rest day · no plan yet (import or build one) · plan without today's training · session active / paused / resting /
finished · offline (the phone keeps the session: `TrainingStore` is in the person's folder) · child account (no
weights) · demo.

## 10. Voice

Everything above works by voice (it does in the engine today). The design adds the caption (what she heard, what she
says) on the Active screen, and the orb's listening state while a count is followed.

## 11–12. Memory and missions

Today's and this week's missions from the plan (`core/fitness_missions.py`); XP to the plan's skills; PRs feed
achievements; "how am I doing?" reads the same numbers as Progress.

## 13. Dependencies and engineering work

- **Phone (Android build needed):** the native voice for the count (`window.MIAPhoneVoice.say`, which the page already
  calls) and the continuous "workout listening" mode (`follow_count` is ready in the engine). Then real-device testing.
- **Retire** the desktop Qt Workout module's own in-memory session (one source of truth).
- Charts helper (design system §8) for Progress.

## 14–16. Devices

Phone first (it's in your hand or on the floor), desktop second (a big screen across the room: the Active screen
readable at 3 m), glasses (Active Training already: the exercise, the set, the rest; keep it to one panel).

## 17. Accessibility

56 px targets in Active (sweaty hands); readable at arm's length and across the room; everything by voice;
reduced motion keeps the rest ring as a number.

## 18. Acceptance criteria

- A whole workout (start to done) can be done by voice alone, on the phone, with the screen off or on.
- A count is always labelled with how it was made; **no unverified count is shown as verified performance**.
- Rest starts by itself, its end is heard, and skip works by voice and by touch.
- Nothing from today's Workout is lost (each tab's function has a home in the new navigation).
- Zac does **two weeks of real workouts** with it; what he changes is the refinement list; then level 5.
