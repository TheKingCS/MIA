# Natural Momentum: proposal (DEC-0148, proposed)

From Zac's handoff "Natural Momentum & Flow State Optimization" (2026-11-08): a morning where, after waking
naturally, coffee led to the dishes, laundry, the kitchen, the development list, delegated groceries and getting
ready for work, all quickly and without forcing it. The direction: help those conditions happen again, stay out
of the way while they do, and never turn them into a schedule. Section 10 of the handoff asks to find what exists
before building, and not to duplicate it. That's this document. Nothing is built yet.

## 1. What MIA already has (most of it)

| The handoff asks for | Already in MIA |
|---|---|
| Natural rhythms, workdays vs days off | **The Loop** (`core/the_loop.py`, DEC-0047): learns *when* recurring things happen (the work dungeon's shifts, routines) and when to start each part. **Work Dungeon** (`core/work_dungeon.py`): the job's shifts and hours. |
| Sleep and waking | **Health** (`core/health_manager.py`, DEC-0129): nights of sleep, sealed. |
| Morning routines, household tasks | **Household routines** (`core/household_routines.py`): laundry, dishes, the trash as recurring missions with today's occurrence. |
| How he means to operate vs how he does | **The Operating Journal** (`core/operating_journal.py`, DEC-0097). |
| What got done, in order, when | **The history** (`core/life_events.py`): every logged change with its time. |
| One easy start, "you could go do X" | **Capability reminders** (`core/capability_reminders.py`, DEC-0143), **whimsy seeds** (`core/whimsy.py`), **My Directions** (`core/direction.py`, DEC-0141). |
| What matters now, without a wall of tasks | **Presence** (`core/presence.py`, DEC-0044): one ranked list, each item saying why. |
| Minimal interruptions, no nagging | **The communication gate** (`core/communication_gate.py`): every unprompted message merged, limited to 5 a day, repeats dropped, held while he's in a personal conversation. |
| Learning which suggestions help | The gate's **dismissed** loop (`core/loops.py`, `checks.dismissed`) and "don't bring that up" (DEC-0146). |
| Delegating development | **Missions and the runner** (`core/work_runner.py`, DEC-0076/0079) and **the council** (`core/council.py`): Claude, Codex and the local models. |
| Groceries | **The Kitchen** (`core/kitchen_manager.py`): grocery list and pantry. **Her browser** (DEC-0117) can build a cart; buying waits for a person's OK. |

## 2. What's genuinely missing

1. **Momentum windows.** Nothing notices that several things got done close together, what started it, and under
   which conditions (woke naturally, a day off, coffee first).
2. **Task chaining.** Nothing knows that one thing tends to lead to another ("laundry started, then the kitchen
   while it runs").
3. **Recognizing flow.** The gate only holds back during a personal conversation. It doesn't know he's in the
   middle of getting things done.
4. **Preparing for tomorrow.** Nothing offers the small thing tonight that makes tomorrow easier (coffee ready,
   clothes out), from what tomorrow holds.

## 3. Proposed first slice (core only, from records MIA already keeps)

All of it reads what's already logged. No new tracking, no location, no phone sensors.

- **`core/momentum.py`: momentum windows from the history.** A window is three or more things done within about
  90 minutes. For each one, it records what came first, the hour, workday or day off (the work dungeon), and
  whether the night before was a full one (health). Each finding is kept as a count, never a rule: "6 of your 9
  quickest mornings began with a small household task." Nothing is turned into a checklist.
- **Chains, as counts.** "B followed A within 45 minutes, 5 times out of 7." A chain is offered at most once, one
  line, right after A is logged, through the gate. It is never offered while he's in flow (next point).
- **Flow guard in the gate.** Two or more things done in the last 30 minutes means he's moving: non-urgent offers
  are *held* (not dropped) until things go quiet. Alarms and replies stay direct, as now.
- **One easy start.** When he's free during one of his usual momentum hours and nothing has happened yet, the
  existing capability reminder may offer the smallest thing that usually starts a run. Never a list, never
  urgent, through the gate's five-a-day limit.
- **Tomorrow's prep.** In the evening, one line from tomorrow's known schedule (a shift, an event) and only prep
  he has done himself before (from the history): "You're on at 7 tomorrow. Coffee ready tonight?" Only when he
  has done that prep before.
- **Feedback.** "Not now" and "thanks" on these count per kind (the gate's dismissed loop already measures this).
  A kind he keeps waving off goes quiet by itself.
- **Momentum on Life State, not a score.** A plain line ("Your mornings off move fastest") on the existing
  pages. Never a streak, a leaderboard or a number to beat.

Loops (DEC-0094): `momentum.offers_taken` (the share of offers he acts on) and `momentum.flow_held` (holds that
were still right when released). Both go in `core/loops.py`, as every process does.

## 4. What it would need from Zac

Things only count if they're logged: a routine checked off, "done with the dishes" said to MIA, a workout
logged. Coffee and putting dishes away aren't in any record today. Section 5 asks how that should work.

## 5. Questions for Zac

1. **Approve the direction and the first slice** (section 3)? Recommended: yes, core first, the design session
   builds any screen.
2. **Faith and delegation.** DEC-0119 says MIA is for you alone and new work doesn't design for other people in
   the house. Delegating to Faith would change that. Options: (a) leave Faith out: MIA only coordinates your
   agents and you; (b) the household's shared grocery list and a drafted message you send her, with no account
   or tracking for her; (c) a real household role for her (reopens DEC-0119). Recommended: (b).
3. **How MIA learns what you did.** (a) only what's already logged; (b) also "I did X" by voice, quickly, any
   time; (c) once a day she asks "anything else get done this morning?". Recommended: (a) plus (b). (c) risks
   becoming the checklist the handoff warns against.
4. **The flow guard.** Hold her non-urgent messages while you're clearly getting things done? Recommended: yes.

## 6. Risks

- **Turning rhythm into rules.** Every finding is a count, said as "often", never "you should". No chain becomes
  a checklist, and nothing is scheduled from it.
- **Interruptions.** Everything goes through the existing gate (five a day, held during flow, repeats dropped).
- **Privacy.** Only his own records, read in his own view; the findings live in his own folder, sealed (DEC-0126).
- **Thin data.** Until a pattern has happened several times, MIA says nothing about it.
