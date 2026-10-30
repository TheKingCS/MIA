# The Body and the Relationship: audit and plan

*Claude, 2026-10-27, from Zac's direction (with Chat): MIA has three
pillars. **The Brain** (intelligence, tools, memory, data) has had most of
the work. **The Body** (interface, navigation, layout, look) and **the
Relationship** (getting to know the person, adapting, growing with them)
now get the same care. This is the audit Zac asked for before major
changes, and the proposed order. Nothing here is built except section
2's first fixes; each step marked ⚖ needs Zac's approval first.*

## 1. The assessment (Zac's seven questions)

### What already works (keep it)
- **Accounts and isolation.** Each person signs in (email + password);
  personal stores live in their own folder (`core/personal_data.py`),
  household stores are shared only by approval, the phone runs each turn
  on the signed-in person's own view (`view_for()`). Child accounts see
  only child apps and never money. Account creation never happens
  through the network server. *This is the foundation User Sync needs,
  and it's already solid.*
- **Propose → Approve → Execute → Record → Undo** for every change
  (`core/actions.py`). User Sync's "confirm before it's kept" is exactly
  this.
- **Learned vs. yours.** The Loop already marks each value as learned or
  the person's own and never overwrites theirs. That's the pattern the
  user model needs everywhere.
- **The communication gate** (one door for everything unprompted: merge,
  daily limit, no repeats, pauses topics you dismiss, never mid-vent).
  Check-ins go through it.
- **Goals with reasons** (intents and the why chain), **memories** (16
  categories, "What I Used" under replies, fix/forget), **context in
  every turn**, **the Fix-It Log** (evidence for the audit).
- **The game systems**: missions, recurring missions, questlines,
  bosses, the Dungeon, the Loop, the Sunday check-in, XP and skills.
- **A design system already exists**: `web/tokens.css` (one cyan accent,
  graphite layers, DEC-0023), the shared frame (`web/shell.js`), line
  icons. The audit applies and extends it, it doesn't start over.

### What needs improving
- **She sometimes sounds like a program** (section 2).
- **Duplicate sources of truth** found:
  - pay: Freedom's own `freedom.hourly` / `shift_hours` and the
    Dungeon's pay and shift;
  - training days: the fitness plan's days and the Loop;
  - chores: recurring missions, the Loop, and a calendar event written
    every day for each one.
- **What MIA knows about a person is scattered**: profile (name,
  birthday), free-text memories, goals, person settings, focus presets,
  the Loop, the fitness plan, the Dungeon. There's no one place to see
  it, correct it, or know where a fact came from.
- **Onboarding is thin**: a three-question "getting to know you" dialog
  on the desktop only, and a scripted first message. The phone just
  makes the account.
- **Pages were built feature by feature.** 47 apps (34 on the web, 13
  PC-only), 51 pages, 17 of them sub-pages reached only from inside
  other pages (the check-in, Places, World Map, Party, Chronicle,
  Recipe, Plan, Profile...), one leftover (`presence.html`). Tab counts,
  strip cells and section patterns vary page to page.

### What's new from scratch
- A **structured user model** (facts with source, kind, confidence,
  review dates, permissions; section 4).
- **User Sync** itself (section 5).
- **Current / desired / capacity** for each recurring activity, and
  missions that ramp between them (section 6).
- **Check-in types A–D** with their controls (section 6).
- **A page-by-page audit** with a scorecard, an information architecture
  agreed with Zac and Muse (section 3).
- **A User Guide and an EULA** (section 7).

### Which existing systems carry the new work
| New work | Built on |
|---|---|
| User Sync | accounts, sign-in, the action contract, the Loop, goals, memories, Garage/Kitchen/Workout stores, starter templates |
| User model | person settings, the Loop's learned/yours pattern, memories' categories |
| Adaptive missions | recurring missions, the Loop, the Dungeon, Fix-It Log, the Sunday check-in |
| Check-ins | the communication gate, memory callbacks, support choice |
| The Body | tokens.css, shell.js, the screen pattern (data assembled in core, the web only formats) |

### Architecture changes needed (⚖)
1. A per-person **user model store** (`core/user_model.py`) that owns
   what has no home today (preferences, communication style, current /
   desired / capacity, interests) and *points to* what other stores own
   (pay → the Dungeon, schedule → the Loop, plan → Fitness), never
   copying it.
2. **Remove the duplicates**: Freedom reads pay from the Dungeon; the
   fitness plan's training days become a Loop rhythm; recurring chores
   stop writing a calendar event per day (the calendar derives them).
3. A **User Sync session** (state, chapters, pause/resume) and its
   screen.
4. Gate controls: **quiet hours**, per-type check-in switches, interaction
   times (the gate has a daily limit and topic pauses, no quiet hours).

### Dependencies and risks
- The user model comes before User Sync (Sync needs somewhere to put
  answers) and before adaptive missions (they read it).
- The information architecture comes before redesigning screens, and
  User Sync's screens are designed in it, not after.
- **Risk: the small-model brain.** The conversation fix and User Sync's
  questions must be checked on the real 14b on the PC (the bench), not
  just tests here.
- **Risk: breaking what works.** Every move keeps its tests; the
  Fix-It Log shows regressions.
- **Risk: privacy.** "Switch to Faith" by voice must never open her
  account (section 5).

### The smallest useful first step
The **conversation fix** (section 2) plus an **"About Me" page**: one
place showing everything MIA knows about you, pulled from the stores
that already exist, each with where it came from and Fix / Forget. It's
the user model's face before its new store, it answers Chat's "inspect,
correct, delete" requirement on day one, and it shows the audit exactly
what's scattered.

## 2. Sounding like a person (Zac: "avoid her saying I don't know what to do")

**Root cause.** Any question that isn't an action or a talk-it-out
moment goes down the "information question" path, whose instruction is
*"Answer using ONLY the reference material below. If the answer isn't
contained in it, say you don't know."* That rule was written for "how
does X work in MIA" questions on the old 3B model, but it catches
ordinary conversation too: "what should I make for dinner?", "any ideas
for my weekend?" get "I don't know".

**Fixed now:** the canned replies: an unknown tool ("I got that mixed
up on my end. Could you say it another way?"), a tool that broke
("Something on my side broke… I've logged it so it gets fixed"), the
model unreachable (says why and what still works). Both errors go to the
Fix-It Log; no internal names are shown.

**Proposed (⚖, then verified on the 14b at the PC):**
- Only real how-to / teach-me questions about MIA use the reference
  material. Everything else is answered as a person: the person's
  context, MIA's own knowledge, and tools for their data.
- One rule for uncertainty: **never "I don't know what to do"**. Ask one
  short clarifying question, or offer the two closest things she can do
  ("Do you mean log it as a shift, or put it on the calendar?").
- Facts about the person's data still come only from their data (never
  invented), as now.
- A bench of "sound like a person" cases on the PC, and the Fix-It Log's
  `no_tool` / `said_wrong` issues as the measure.

## 3. The UI/UX audit (the Body)

**Phase 1, inventory** (no code changes): every page and sub-page, its
purpose, data, actions, how you reach it, which device it's for, its
tests. Screenshots at phone and desktop width. Output:
`docs/UI_AUDIT.md`.

**Phase 2, information architecture** (⚖ Zac, with Muse): what lives on
Home, what gets its own page, what's best by talking to MIA. Candidate
consolidations to evaluate (not decided): Missions + Skills + Character
+ Reward Shop + Chronicle as one "You" area; Money + Freedom + the
Dungeon + Compliance + Insurance as one money area; Garage + Workshop +
projects; Kitchen + Workout + My plan. The apps stay the layout
(DEC-0045); consolidating is grouping inside that layout, Zac's call.

**Phase 3, design system**: extend `tokens.css` into written standards
(type scale, spacing, density, cards, tabs, strips, dialogs, status
colors, motion, AR/glasses rules, contrast). Muse owns the look;
Claude builds it.

**Phase 4, page by page**: Chat's ten questions as a scorecard for each
page, plus the Fix-It Log's evidence for that page. Findings first,
proposals second, approval before big changes.

**Phase 5, build**: the highest-impact journeys first: User Sync, Home,
Missions, Profile / About Me. Then page by page, tests kept green.

## 4. The unified user model (⚖)

One store per person, `core/user_model.py`. Each entry:

| Field | Meaning |
|---|---|
| area, key, value | "fitness", "workouts_per_week", 1 |
| kind | fact · estimate · preference · goal · capacity |
| dimension | current · desired · capacity (for recurring things) |
| source | said · integration (Plaid…) · inferred (and from what) |
| first / confirmed | when recorded, when last confirmed |
| confidence | for inferred values only |
| review_after | when it's worth checking again (Type A check-ins) |
| shared_with | which features may read it |
| owned_by | for values another store owns: a pointer, not a copy |

Rules: an inference is never stored as a fact; a person's own value
always wins (the Loop's rule, everywhere); changing one thing (the work
schedule) flows through events to what depends on it (the Loop, the
Dungeon's planned runs, missions) instead of being edited in five
places.

## 5. User Sync (the Relationship, part one) (⚖)

- **Starting it:** "Hey MIA, I'm about to introduce you to Faith…".
  MIA prepares, then the device shows Faith's **sign-in** (or account
  creation, on the device itself, never through the network server). A
  spoken name never unlocks anything. Then MIA explains what User Sync
  is, what it may ask, that everything can be skipped, and waits for
  "I'm ready".
- **Chapters**, each optional and resumable: Basics (name, how to talk
  to her, how often MIA speaks up) · Routine (work, breaks, chores,
  sleep if shared) · Goals (and why) · Food · Fitness · Assets &
  projects · Money (only if wanted, never for a child).
- **How it talks:** the questions are written in code (a small model
  can't safely improvise an interview); the model phrases them warmly
  and reads answers into **proposed** records, shown to confirm at the
  end of each chapter.
- **What it fills:** the Loop (rhythms with current / desired /
  capacity), first missions, Garage, Kitchen, Workout, goals, the user
  model, the Dungeon if they work.
- **Existing users** (Zac) can run any chapter to fill in what MIA
  doesn't know yet.

## 6. Adaptive missions and check-ins (the Relationship, part two)

- **Current / desired / capacity** on every recurring activity (the
  Loop's rhythms gain them). Missions start at capacity and ramp toward
  desired when the person keeps clearing them ("reads once a week, wants
  daily" starts at twice).
- **A missed mission asks why** (after two misses, once): life happened
  · not enough time or energy · wrong time · don't care anymore · badly
  designed. Each answer changes the system (move it, shrink it, drop
  it), never a penalty.
- **Check-ins**: A verify ("still working nights?") when a value's
  review date comes; B curiosity ("woodworking: what first?"); C
  calibration (in the Sunday check-in: "a crowded week: fewer
  missions?"); D feature survey (now and then). All through the gate.
- **Controls** in Settings: how often, preferred times, **quiet hours**
  (new), the daily maximum (exists), topics (exist), each type on/off,
  and whether an answer updates data directly or asks first.

## 7. The User Guide and the EULA

- **User Guide:** MIA already has 27 help topics (`docs/user_help/`)
  that she answers "how do I…" from. After the information architecture
  is settled, they become one User Guide, in the app (a Guide page) and
  in her answers, kept in step with each screen.
- **EULA:** a draft needs a few facts first (section 9), and it should
  be reviewed by a lawyer before anyone outside the household relies on
  it. MIA's design already supports the right promises (local-first,
  your data is yours, export and delete, MIA drafts but never sends,
  crisis numbers by region, not professional advice).

## 8. Recommended order

| # | Step | Needs | Approval |
|---|---|---|---|
| 0 | Sound like a person (section 2) | the PC for the 14b check | ⚖ the routing change |
| 1 | About Me page (read-only + Fix/Forget) | nothing new | — |
| 2 | UI inventory and scorecards (`docs/UI_AUDIT.md`) | the Fix-It Log's first weeks | — |
| 3 | Information architecture + design standards | step 2, Muse | ⚖ |
| 4 | User model store + duplicate fixes | step 1 | ⚖ |
| 5 | User Sync v1: Basics + Routine + Goals | steps 3 (its screens), 4 | ⚖ the flow |
| 6 | Adaptive rhythms and missions, missed-mission "why" | step 4 | — |
| 7 | Check-ins A–D + controls (quiet hours) | step 4 | ⚖ defaults |
| 8 | Redesign the top journeys (Sync, Home, Missions, Profile) | step 3 | ⚖ each layout |
| 9 | User Sync's other chapters; the rest of the pages | 5, 8 | per page |
| 10 | User Guide in the app; EULA reviewed | 3 | ⚖ EULA |

## 9. Questions for Zac (answered 2026-10-27, DEC-0050)

Answers: 1 yes (built; verify on the PC); 2 MIA will eventually be
offered to others, business structure undecided (placeholders, lawyer
review before release); 3 yes to all three defaults; 4 quiet hours off
until each person sets them.

The questions were:

1. **Step 0:** go ahead with the routing change (only how-to questions
   use the reference material; otherwise she answers as a person and
   asks when unsure)? It's verified on the PC before it ships.
2. **The EULA:** who is offering MIA (you personally, or a business
   name)? Which state or country's law? Will MIA stay with your
   household for now, or be given or sold to others (that changes how
   much it has to cover)?
3. **User Sync:** voice, typing or both (default: both)? One sitting or
   chapters over a few days (default: chapters)? Should you run it too
   (default: yes, to fill in what MIA doesn't know)?
4. **Quiet hours:** a default (say 10 PM–7 AM, adjusted for night
   shifts from the Loop), or off until each person sets them?
