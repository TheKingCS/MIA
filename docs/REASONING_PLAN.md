# MIA's Reasoning: one owner per fact, answers that combine, findings, continuity

*Claude, 2026-10-30, at Zac's request ("the Brain is developing faster
than the reasoning layer"). Proposed as DEC-0052; nothing here is built
until Zac approves it. Builds on `docs/INTELLIGENCE_AUDIT.md` (DEC-0043's
multi-step turns), `docs/BODY_AND_RELATIONSHIP_PLAN.md` (the duplicates
and the user model) and `docs/ENGINE_PHASE1_PLAN.md` (life events, links,
Life State v2).*

## 1. Where MIA is

**Strong:** about 210 tools across 42 apps, a history of what happened
(`core/life_events.py`), how things relate (`core/links.py`), a derived
picture of the person's life (`assemble_life_state_v2()`), Presence
ranking what matters now, memories with "What I Used", and questions
that clearly ask for one lookup answered by code in an instant.

**Weak, and what this plan is about:**

1. **Some facts have more than one home**, so two screens or two answers
   can disagree (section 2).
2. **A turn is one round.** The model picks tools; MIA runs them and
   says each result as it is (`core/assistant_turn.py`). The results never
   go back to the model to be combined, and there's no second round to
   look up what the first one revealed. "Can I afford the coop this
   month?" needs the budget, the bills before payday, this week's pay and
   the build's cost: today she can answer one of those, not the question.
3. **Tools are offered by the words in the question** (each tool's
   `trigger_phrases`). A detailed question often names none of the tools
   it needs, so they aren't offered at all.
4. **Nothing reads across apps on its own.** Presence ranks items, but
   each item comes from one app. Nothing notices that a bill lands before
   payday, or that the truck's oil change is overdue the week of a trip.
5. **A conversation has no state beyond its messages.** "Move it to
   Saturday" depends on the model guessing what "it" was from the history
   that fits in its window.

The principle stays the one MIA is built on: **facts and arithmetic in
code, the model only phrases and chooses.** The 14b on the PC is good at
choosing and phrasing; it isn't trustworthy at adding up money or
remembering which record "it" was. Every step below keeps that split.

## 2. Step 1: one owner per fact ⚖

A fact gets **one owner**. Every other place *reads* it from the owner,
never keeps its own copy.

| Fact | Owner | Duplicates today | Change |
|---|---|---|---|
| Pay (rate, shift, overtime, take-home) | the Dungeon (`core/work_dungeon.py`: `hourly`, `shift_hours`, `overtime_multiplier`, `take_home_pct`) | Freedom's `freedom.hourly` and `freedom.shift_hours` (`core/freedom.py`) | Freedom reads take-home an hour and the shift from the Dungeon; its own two settings are retired (moved once, then removed) |
| When things happen in the week (work, training, chores) | the Loop (`core/the_loop.py`) | the fitness plan's `training.days` (`core/fitness_manager.py`) | training days become a Loop rhythm; the fitness plan keeps *what* to train, the Loop *when* |
| Chores that repeat | recurring missions (`core/recurring_mission_manager.py`) | a calendar event written every day for each one | the calendar shows them derived from the missions, not written |
| Money in and out | Money (`core/budget_manager.py`, the bank sync) | none known | stays; Freedom, Dungeon loot "banked" and Insurance read it |

**How it stays fixed:** `core/ownership.py` holds this table (fact →
owner store → the field), and a test fails when a second store starts
writing a fact that has an owner, the same way `LIMITS` in
`core/capabilities.py` fails when an app has no entry.

**Data:** the move runs once on each profile (Freedom's rate goes into
the Dungeon if the Dungeon has none), is undoable, and keeps the old
values in the life events history.

## 3. Step 2: answers that combine (multi-step turns) ⚖

DEC-0043 approved multi-step turns in principle ("up to N tool steps,
reads freely, changes only as proposals; the evaluation decides N").
This is the design.

### 3a. Question plans, in code (the fast, reliable path)

The detailed questions people ask most get a **question plan**: the
lookups it needs, run by code at once, their results put into one fact
sheet, and the model phrases one answer from it. No guessing which tools
to call, and it works on the phone's small model too. The first ones:

| Question | Lookups combined |
|---|---|
| "Can I afford X?" / "Should I buy X?" | budget this month, bills due before next pay, next pay (Dungeon), what X costs (build, recipe, shop item), the freedom fund's pace if it's on |
| "How was my week?" | workouts and personal bests, shifts and loot, missions moved or finished, money spent against the plan, eggs or goods sold |
| "Am I ready for my trip?" | the trip's gear (packed or not), vehicle upkeep due before it, weather, calendar clashes |
| "What should I do today?" / "What's my day look like?" | Presence's now, today's Loop rhythms, calendar, due chores and upkeep |
| "Where is my money going?" | spending by category against last month, subscriptions, untagged charges |
| "How am I doing on X?" (a goal) | the goal's why, its missions and objectives, the life events behind its progress |

A plan names its lookups by tool name; the arithmetic between them
("bills before payday" minus "left this month") is code, never the
model. Plans live in `core/question_plans.py`, matched like quick
commands, and each one has a test with the answer's facts checked.

### 3b. The tool loop (for everything a plan doesn't cover)

When no plan matches, the turn becomes a short loop:

1. **Offer by domain, not just by words.** The question's matched
   domains plus the domains linked to them (money ↔ the Dungeon ↔
   Freedom; Garage ↔ Expeditions ↔ calendar; Kitchen ↔ meal plan ↔
   Workout), capped at about 12 tools: the 14b gets worse past that
   (`docs/ROADMAP.md`'s tool-count history).
2. **Results go back to the model** as tool messages, and it may call
   **up to N more lookups** (N = 3 to start on the PC, 1 on the phone;
   the bench in 3c decides). Lookups only: a change asked for mid-loop
   becomes a proposal shown with the answer (Propose → Approve), never
   run inside the loop.
3. **One answer at the end**, written from the results, with "What I
   Used" listing the lookups (the same chip memories use today).
4. **A number check.** Every amount, date and count in the answer must
   appear in a tool result or the question. If one doesn't, the answer
   is rewritten once from the fact sheet alone; if that fails too, MIA
   gives the plain results instead. She never says a number she didn't
   look up.
5. **A time budget** (about 30 s on the PC), with what she's looking at
   shown while she works ("Checking your bills and your pay…"); past it,
   she answers with what she has and says what she couldn't check.

Built in `core/assistant_turn.py` (the loop) and `core/assistant_chat.py`
(offering by domain); `split_safe_tool_calls()` keeps its rule (a
destructive call bundled with others is skipped).

### 3c. How it's measured

- **Unit tests** with a scripted fake model: the loop's step limit,
  proposals instead of changes, the number check, the time budget.
- **A multi-step bench** on the PC's real 14b: `MULTI_CASES` in
  `tests/live_model_check.py`, each with the lookups that must be used,
  the facts the answer must contain, and no invented numbers. N is
  chosen from it. The Fix-It Log records multi-step turns that ran out
  of steps or failed the number check.

## 4. Step 3: findings across apps ⚖

**Findings** are what MIA notices by combining apps, worked out in code
over Life State v2, links and life events, and only phrased by the model.
Each one has:

- **the claim** ("Your electric bill is due the 3rd; your next pay lands
  the 5th"),
- **the evidence**: a `kind:id` ref for every record used, so each one
  is tappable,
- **why it matters** and **one suggested action** (an action kind from
  `core/actions.py`, through Propose → Approve → Execute → Record → Undo),
- **how sure**: REAL (from records), DERIVED (computed), or estimated,
  the same labels Life State uses.

**The first ten** (each one a small rule, with its own test):

1. A bill is due before the next pay, and this month's money left won't
   cover it.
2. Upkeep is due on a vehicle that a planned trip uses.
3. A planned meal needs something the pantry is out of, and it isn't on
   the grocery list.
4. Eggs or goods on hand will pass their best-by before the next market
   day.
5. Overtime this week, and training days missed this week (rest counts:
   said without guilt, DEC-0014).
6. A deadline (Compliance) falls in a week the calendar is already full.
7. A subscription charge with no use of what it pays for in 60 days.
8. A goal with no step in two weeks, and the mission it depends on is
   stuck on one objective.
9. A build's budget is used up but the build isn't done.
10. An insurance renewal is near and the quotes collected beat the
    current price.

**Where they show:** when asked ("what should I know?", "anything I'm
missing?", "why?"); on Home, as Presence items of their own kind; and
unprompted only through the communication gate (merged, rate-limited,
repeats dropped). Built in `core/findings.py`; served in `/api/state`
(the schema updated with it).

**Later, not now:** the model proposing new connections from the Fix-It
Log and the life events, each one checked against the data before she
says it, and added as a rule only when Zac approves.

## 5. Step 4: conversations that hold together ⚖

Each conversation keeps a small **conversation state** beside its
messages (`core/conversation_state.py`):

- **What it's about:** the records it's been about (`kind:id` refs from
  the lookups and changes so far), so "move it to Saturday" or "how much
  was that?" resolves in code to the record, not to the model's guess.
- **What's still open:** a question MIA asked and is waiting on, a
  proposal not yet approved, a choice the person hasn't made.
- **A short running summary**, written after a few turns, so continuity
  doesn't depend on how much history fits in the model's window.
- **One good follow-up question** when an answer leaves a decision open
  (DEC-0050 already allows one short question instead of "I don't
  know").

It's measured the same way as step 2: unit tests for resolving "it",
"that" and "the other one", and conversation cases on the PC's 14b
(three to five turns each, checked turn by turn).

## 6. Step 5: the companion layer

Voice first, the glasses, getting around by asking ("show me what's
due"), and proactive help are the goal, and they stand on steps 2 to 4:
proactive help without findings is just more notifications, and voice
without conversation state falls apart after one exchange. The custom
voice (DEC-0051's later step) fits the voice layer already built. Each
gets its own plan when steps 2 to 4 are in.

## 7. Order

| # | Step | Needs | Approval |
|---|---|---|---|
| 1 | One owner per fact (section 2) | nothing | ⚖ the data move |
| 2a | Question plans, the first six (3a) | step 1 (pay has one owner) | — |
| 2b | The tool loop, N from the bench (3b, 3c) | the PC for the bench | ⚖ N and the time budget |
| 3 | Findings, the first ten (section 4) | step 1 | ⚖ which go through the gate unprompted |
| 4 | Conversation state (section 5) | step 2 | — |
| 5 | The companion layer (section 6) | 2 to 4 | per piece |

Every step keeps its tests, is checked on the PC's model before it's
trusted, and shows up in the Fix-It Log when it stumbles.

## 8. Questions for Zac

1. Approve the order above, and step 1's data move (Freedom's hourly
   rate becomes the Dungeon's)?
2. Which of the first ten findings may reach you **unprompted** (through
   the gate), and which only when you ask?
3. A detailed answer may take a few seconds longer while she checks
   several things: is about 30 seconds on the PC acceptable as the most
   she spends before answering with what she has?
4. Any question you ask her that should be on the first list of
   question plans (section 3a)?
