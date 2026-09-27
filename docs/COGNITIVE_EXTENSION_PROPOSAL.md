# Cognitive Extension: Implementation Proposal (2026-09-27)

Answers section 20 of `docs/COGNITIVE_EXTENSION.md` (the owner's
"Cognitive Extension & Contextual Presence" direction), plus the
owner's addendum: *talk to MIA like a therapist or a living journal,
and have her keep the journal organized and use it to support me.*

Nothing here is built yet. This is the plan, split into slices the
owner picks from.

## The short version

Most of the foundation already exists. MIA already has a live "what's
going on in my life" layer, long-term goals, pattern detection that
refuses to nag, memories sorted by category, a journal, an evening
check-in, and push to the phone. What's missing falls into five pieces:

| Slice | What you get | Needs first |
|---|---|---|
| **A. Talk it out** | Journal by talking; "just listen", "no bullshit", "hype me up"; MIA files and organizes it; a safety floor for real distress | Nothing. Can start now |
| **B. Remember Why** | "Remind me why I'm doing this" answered from your real numbers and goals, and updated when your reasons change | Your goals entered as a chain of reasons (5 minutes, by talking) |
| **C. Know when to speak** | One gate that every proactive message passes through: quiet hours, a daily limit, no repeats, your mode | Nothing. Should land before D |
| **D. Contextual Presence** | Welcome Home, "you're at Lowe's, want the materials list?" | The native Android app (build queue #2) and slice C |
| **E. Life Runway** | "Your current chapter" progress view | Slice B's data |

**Recommendation: A, then B, then C, then D after the Android app,
then E.** A is what you asked for directly, and its safety floor
should exist before MIA leans harder into emotional conversations. B
reuses A's modes. C must exist before anything location-driven can
talk to you unprompted.

## Principles this plan keeps

- **Local-first.** Journal, reasons, patterns and location stay on the
  home machine in `data/`. The phone only talks to home MIA over your
  Tailscale link. Nothing goes to a cloud service.
- **The facts come from code, the words come from the model.** MIA
  runs a small local model (llama3.2:3b). It is good at phrasing and
  bad at arithmetic and at remembering to check five sources. So
  every "why", briefing and progress statement is assembled
  deterministically from your records first, and the model only turns
  that fact sheet into speech. That's also what makes it testable
  (see question 12) and what stops it from "manufacturing progress"
  (philosophy point 11).
- **You write the why, MIA keeps the evidence.** Your reasons are
  yours: MIA never invents a motivation for you. She stores the chain
  you tell her and attaches live evidence (debt balance, rentals,
  builds) to each link.
- **Explicit beats inferred.** Modes switch on what you say first. MIA
  may *ask* which kind of support you want; she doesn't silently
  diagnose you. Inferring a mode from tone comes later, only if the
  explicit version proves itself.
- **Silence is a valid answer.** Every proactive path can end in "say
  nothing," and that outcome is logged so you can see what MIA chose
  not to say.
- **Supportive, not a therapist.** MIA can listen, reflect, remember
  and organize. She is not a licensed therapist, and says so plainly if
  asked. When distress looks serious she points to real people, every
  time, without the model deciding (see the safety floor below).

## 1. What already supports these concepts

| Concept | Already built | Where |
|---|---|---|
| Life State / world model | Live snapshot of missions, streaks, skills, insights, overdue maintenance, projects | `core/context_assembler.py`, `get_life_state` tool |
| Long-term "why" | **Intents**: open-ended goals ("Homestead Independence"), one primary, Projects link to them | `core/intent_manager.py`, `core/project_manager.py` |
| Missions / objectives | Missions, recurring streaks, pathways | `core/mission_manager.py`, `core/recurring_mission_manager.py` |
| Financial progress | Debts with payoff plan, budget, net-worth snapshots, rentals | `core/budget_manager.py`, `core/finance_manager.py`, `core/real_estate_manager.py` |
| Pattern recognition | Repeated mission abandonment, skill momentum/decline | `core/mission_patterns.py`, `core/skill_patterns.py` |
| "Don't be naggy" | Insights are created only if new (idempotent); budget nudges merge into one message or stay silent; check-in waits for evening and skips if you already talked | `core/insight_manager.py`, `core/budget_nudges.py`, `core/daily_occasions.py` |
| Memory of you | Extracted memories with categories, reviewable and deletable | `core/user_memory_manager.py` |
| Journal | Dated, tagged, searchable entries | `core/journal_manager.py` (Notes module) |
| Conversation modes | Three paths already: action, info, teaching (phrase-triggered) | `core/assistant_chat.py` |
| Speaking to the phone | Web push relay of notifications; phone voice endpoints | `core/web_push.py`, `server/app.py` |
| Knowing capabilities | Online/offline self-knowledge | `core/connectivity.py` |
| Companion philosophy | Warm companion, proactive but restrained | `docs/VISION.md` |

## 2. Specifications that need amendments

- **`docs/VISION.md`**: add "cognitive extension, not replacement" and
  the human-agency principle as named principles, linking the source
  document. Add "know when to speak" next to "Proactive, not just
  reactive" so the two read as a pair.
- **`docs/ARCHITECTURE.md`**: document the communication gate (slice
  C) as the single path for proactive messages, the same way
  `MIAApplication._display()` is the single path for screen changes.
- **`docs/ASSISTANT_CAPABILITIES.md`**: conversation modes become a
  fourth path next to action/info/teaching; the safety floor sits in
  front of all of them.
- **`CLAUDE.md` "Known intentional simplifications"**: "No AI/assistant
  logic yet" is out of date and should be corrected when slice A lands.
- **`docs/user_help/assistant.md`**: what each mode does, how to
  journal, how to go off the record, what MIA does if you're in crisis.

## 3. New services, events and entities

New code, all following the existing dataclass + JSON + manager shape:

| New piece | Kind | Slice |
|---|---|---|
| `core/conversation_modes.py`: mode vocabulary, explicit-phrase detection, one short prompt line per mode | Pure logic | A |
| `core/safety_floor.py`: serious-distress detection and the fixed response | Pure logic | A |
| Journal sessions: `JournalEntry` gains optional `source="conversation"`, `conversation_id`, `mood` (your word, never scored), `themes` | Additive fields | A |
| Memory categories: add **Values**, **Goals & Reasons**, **Struggles & Patterns**, **Wins** | List change | A |
| `core/why_graph.py`: builds the chain + evidence on demand, never persisted (same stance as Life State) | Read-only service | B |
| `Intent.serves_intent_id` and `Intent.reason` (your words) | Additive fields | B |
| `core/communication_gate.py` + a small log of what was said, deferred, or dropped | Service + JSON | C |
| `core/presence_manager.py`: your Places (home, work, Lowe's…) and the current `PresenceState` | Service + JSON | D |

New event-bus events (existing naming style is `domain.verb`):
`presence.arrived`, `presence.left`, `presence.transition`,
`conversation.mode_changed`, `communication.decided` (act/defer/drop,
with the reason). The source document's `USER_REQUESTED_*` events
aren't needed as events: a request you make is already a turn in the
conversation.

## 4. Contextual Presence and Life State

`LifeStateSnapshot` gains an optional `presence` field filled from
`PresenceManager` when it exists, the same way it already pulls from
missions and maintenance. It stays a live read, never stored. Presence
does **not** get its own separate "brain": the gate (slice C) reads
Life State + presence to decide whether to speak, and the Why Graph
(slice B) reads Life State to know what's active.

## 5. How communication-worthiness works

One function, `decide(message_candidate, now, state) -> Act | Defer
| Drop`, and every proactive path goes through it (today's birthday,
calendar digest, check-in, budget nudge, smart suggestions and
insights, and later Welcome Home and location prompts). Pure logic,
so it's testable with a fake clock. The checks, in the source
document's order:

1. **Relevant?** The candidate names what it's about (a project, a
   bill, a person). Drop if that thing is closed or finished.
2. **Time-sensitive?** Each candidate carries an urgency: `urgent`
   (safety, money due today), `timely` (useful within hours),
   `ambient` (nice to know).
3. **Is the user available?** Your quiet hours, your current mode
   (Focus / Listening mute ambient messages), and presence when it
   exists (arriving home = decompression, see below).
4. **Spoken recently?** A daily budget for unprompted messages (start
   at 3), minimum spacing (say 90 minutes), and never the same topic
   twice in a week unless its facts changed.
5. **Real value?** A candidate with no fact that changed since last
   time is dropped. This reuses the Insight rule: new, or not at all.
6. **Mode** picks the tone line handed to the model.

`urgent` skips 3–5. `timely` can be deferred to the next open window;
`ambient` is dropped rather than queued, so there's never a backlog
dumped on you later. Everything is logged with the reason, and
"what did you decide not to tell me today?" becomes a question MIA can
answer. You can change the budget and quiet hours in Settings or by
saying so.

## 6. Location, projects and missions

- **Places are yours.** You name them on the desktop or by voice
  ("this is Lowe's", "this is work") with a radius. Each place can be
  linked to Projects ("Lowe's → wallipini, greenhouse, garage").
- **The phone detects, home decides.** The Android app (build queue
  #2) uses Android geofencing, which works in the background with low
  battery cost. It sends only *transitions* ("entered Lowe's") to home
  MIA, not a location trail. Web apps can't geofence in the
  background, which is one more reason for the native app.
- **Home decides whether to speak** via the gate. At a project place
  linked to an active project with an open materials list, MIA asks
  once ("Want the wallipini materials list?"). She never assumes what
  the trip was for. Coming home from one, she offers once to log what
  you bought, using the existing material/inventory tools.
- **Welcome Home** is a `decompression` candidate: after a delay you
  set (default 10 minutes after arriving), at most one short message.
  Only `urgent` items are named; everything else is "nothing needs you
  right now" or silence. No task lists.
- **Privacy:** transitions are kept 30 days by default, then deleted;
  a "pause location" switch in the app and in Settings.

## 7. How the Why Graph is represented

Two layers, kept separate on purpose:

1. **Your chain (stored, user-authored).** Intents already exist. Add
   `serves_intent_id` so an Intent can point to the bigger one it
   serves, and `reason` in your own words. Your example becomes:
   *Factory work → Pay down debt → Financial flexibility → Control
   over my time → Homestead, family, projects*. You set it up by
   talking ("the reason I'm paying off debt is so I can control my
   time"), and MIA reads it back to you for confirmation before
   saving.
2. **Evidence (computed, never stored).** `core/why_graph.py` walks
   the chain and attaches live facts to each link from the managers
   that own them: debt total and change since the last checkpoint,
   rentals owned and their income, active builds and their progress,
   finished missions, net-worth trend, recent wins from memory.

**"This used to be why"** falls out naturally: when a link's evidence
shows it's done (debt paid off) or you retire an Intent, the chain
marks it complete, and MIA can say "paying off debt used to be the
main reason; it's done. Here's what today is buying now." A monthly
checkpoint of the evidence (small, stored) is what makes "look at what
changed since spring" possible.

## 8. How "Remember Why" gets its facts

1. The mode detector sees a perspective request ("remind me why",
   "I'm dragged down at work", "what's the point").
2. MIA asks which kind of support you want if it isn't clear
   (perspective, momentum, progress, humor, hard truth, or just
   listen). One question, and it remembers your usual choice.
3. `why_graph.build(context)` returns a short fact sheet: the chain,
   3–5 evidence facts with real numbers, and one recent win.
4. The model gets: the identity line, the mode's single tone line,
   and the fact sheet, with the instruction to use only those facts.
   No tools are offered on this path, so it can't wander off into
   editing records.

Nothing is hard-coded, so the speech changes when your life does.

## 9. Telling the modes apart

The source lists 12 modes. For a 3B model, 12 subtly different
personalities is too many to hold apart reliably, and prompt length
has hurt this model before (`docs/ROADMAP.md` history). So:

- **Six modes the model is asked to hold:** **Listen** (reflect, no
  advice, no fixing), **Perspective** (the why chain), **Momentum /
  hype** (get through the next stretch), **Direct** ("no bullshit":
  plain, no padding, still kind), **Plan** ("help me figure out what
  to do": make it smaller, one next step), and the default
  **Companion** (today's warm behavior). Humor, Celebration and
  Decompression are tone flavors of these, not separate modes.
- **Explicit phrases switch modes** ("just listen", "no bullshit",
  "hype me up", "help me figure out what to do", "can I vent", "I
  want to journal"), exactly like teaching mode's trigger phrases do
  today. The mode stays for that conversation until you change it.
- **When it's ambiguous, MIA asks** instead of guessing. "I'm just
  tired of doing the same thing every day" gets Listen by default, not
  productivity advice (source section 4).
- **Crisis isn't a mode.** It's the safety floor below, which runs
  before any mode and can't be turned off by one.

### The safety floor

A small, deterministic check runs on every message before the model
sees it. On clear signs of danger (suicidal thoughts, self-harm,
someone in danger) MIA answers with fixed, human-written text: she
takes it seriously, stays with you, and gives real contacts (988
Suicide & Crisis Lifeline by call or text in the US, and 911 for
immediate danger), plus any trusted person you choose to list in
Settings. Then the conversation continues in Listen mode. This path
doesn't depend on the model's judgment, works fully offline, and gets
its own test corpus with both "must trigger" and "must not trigger"
sentences ("this traffic is killing me").

## 10. Preventing overload

- The gate's daily budget, spacing, quiet hours and no-repeat rule
  (question 5).
- **Consolidation**: several candidates in one window become one
  message, the way budget nudges already merge four checks into one.
- **Ambient is dropped, never queued.**
- **Learning from being ignored**: a message type dismissed or
  unanswered three times in a row lowers its own urgency. You can
  always see and undo that in the log.
- **Location prompts** are one per place-visit and never repeated
  that day.

## 11. Now versus later

**Now (slice A, "Talk it out"):**
- Conversation modes (six, explicit phrases, ask-when-unclear).
- Safety floor.
- Journal by talking: say "I want to journal" or just talk in Listen
  mode; when the conversation ends MIA writes one dated journal entry
  (a summary in your voice plus your key lines verbatim, your mood
  word, themes as tags) linked to the conversation. You see it in
  Notes and can edit or delete it.
- **Off the record**: "this is off the record" means nothing from the
  conversation is saved to the journal or to memories.
- New memory categories (Values, Goals & Reasons, Struggles &
  Patterns, Wins), so what you share builds MIA's understanding of
  what you value and what you're working through, all reviewable in
  Memories.
- Journal tools: "what have I been writing about lately?", "when did
  I last feel like this?", "what did I say about work last month?"
- A weekly reflection you opt into: MIA reads the week's entries and
  offers themes and one question, never a verdict.

**Next (B, then C):** Why Graph and Remember Why; the communication
gate, then moving today's daily checks behind it.

**After the Android app (D):** Places, geofenced transitions,
Welcome Home, project-place prompts.

**Later (E and beyond):** Life Runway view; inferring modes from tone;
using calendar/motion/Bluetooth as extra presence signals; noticing
patterns in the journal on its own ("you've mentioned wanting to quit
after long weeks three times this month"), which needs care and your
opt-in because it's the most personal inference MIA would make.

## 12. Testing without brittle wording tests

Generated sentences are never asserted word for word. Instead:

- **Deterministic layers get normal tests**: mode detection and the
  safety floor get sentence corpora (like `tests/assistant_routing_corpus.py`),
  the gate gets fake-clock tests for every rule, the Why Graph gets
  demo data in and exact facts out (debt dropped from $X to $Y).
- **Model output gets property checks** in `tests/live_model_check.py`
  on your machine:
  - **No invented numbers**: every number in the reply must appear in
    the fact sheet it was given.
  - **Grounded**: it names at least one real item from the fact sheet
    (a project, a debt, a win).
  - **Mode respected**: Listen replies contain no instructions or
    lists; Welcome Home names no tasks unless one was urgent; Direct
    is under a length limit.
  - **No tools on emotional paths.**
- **The gate log** is itself a test surface: replaying a scripted day
  (arrive at work, Lowe's at lunch, home at 5) must produce the
  expected act/defer/drop sequence.

## Journal privacy (needs your call)

Journal and memories are plain JSON in `data/` today, like every
other record. Your Plaid keys are in an encrypted vault. A journal you
talk to like a therapist is at least as sensitive. Options:

1. Keep plain JSON for now (the machine and backups are yours), and
   add encryption later.
2. Encrypt the journal with the same vault passphrase as Plaid, which
   means unlocking MIA once per boot before she can read or write it.

Recommendation: **2**, built as part of slice A, since moving existing
entries later is harder than starting encrypted.

## Open questions for the owner

1. Build order: A → B → C → D → E, or something else?
2. Journal encryption: option 1 or 2 above?
3. Safety floor: is there a trusted person you want listed alongside
   988 and 911?
4. Quiet hours and the default daily budget of 3 unprompted messages:
   right, too many, too few?
