# MIA as one system, not a collection of apps: audit and plan

*Claude, 2026-10-21, on Zac's PC. The spec is Chat's handoff,
`docs/specs/UX_SYSTEM.md` ("From App Launcher to Personal System"). Audit
first; then the first increments (DEC-0044). Evidence is from the code
and from screenshots of the web screens with placeholder data.*

## 1. What it feels like today, and why

The web frame (`web/shell.js`) puts **every app in the sidebar** (45
apps in `core/web_surfaces.APPS`, about 35 on the web), and the phone's
bottom bar is **Home** and **Apps**. Home (`web/index.html`,
`web/home.js`) is a greeting and three lists: Today's Focus (overdue
upkeep), MIA Remembers, Upcoming. Each new feature (Freedom, Compliance,
Chickens) added one more sidebar entry and one more place to go. So MIA
reads as a launcher, even though underneath she is already one engine.

## 2. Gap analysis

| | Status | Evidence |
|---|---|---|
| One engine, every screen and device | ✅ working | Core runs on the phone and the PC; web screens, the desktop, the glasses (`core/glasses.py`) and voice all use the same stores and the action contract; no device has its own business logic |
| The loop: authorize → execute → record → undo | ✅ working | `core/actions.py` (propose, approve, execute, record, undo), child limits, crediting; Assistant tools with undo (`core/undo_log.py`) |
| Update state, emit events | ✅ working | life events (`core/life_events.py`), the event bus, `core/live.py` telling screens to re-read |
| Shared personal state | ✅ working, 🟡 poorly surfaced | Life State v2 (`core/context_assembler.py`, `/api/state`), links between things (`core/links.py`), the why chain (`core/why_graph.py`), memories ranked by relevance. Home shows little of it |
| Understand (context per request) | ✅ / 🟡 | Talk retrieves relevant memories ("What I Used"), the user-context block, tool routing in code; no shared "what is Zac working toward right now" block in every turn |
| Proactive, within limits | ✅ working | the communication gate (5 a day, merges, no repeats, why-did-you-tell-me), daily checks, insights (`core/smart_suggestions.py`, `core/*_insights.py`, patterns) |
| Self-knowledge | ✅ new | model registry, capability map, docs search (DEC-0039/0041) |
| Navigation by intent | ❌ | app list everywhere; no "World", "Hero's Path" or "System" destinations |
| Presence (what matters now, across everything) | 🟡 fragmented | `core/today.py` gathers overdue/today/waiting from bills, upkeep, tasks, calendar, birthdays, inbox; but not Compliance, Freedom, goods to sell first, eggs to carton, the open market day, the active mission's next step. No "why" on items, no fact/suggestion distinction |
| Hero's Path in one place | 🟡 fragmented | Missions, Skills, Character, Chronicle, Reward Shop, Party, World Map, Quests are separate screens |
| Goals → projects → missions | 🟡 partial, ⚠ three objects | Intents (goals, the why chain), Projects (builds with budgets), Missions (game objectives with XP). Links exist (`Project.intent_id`, links store) but no single "objective" the person sees across them |
| Plan a multi-step objective | ❌ | one tool call per turn (plus follow-ups); no planner that breaks "build the greenhouse" into steps across modules |
| Verify before reporting done | 🟡 | actions return what happened from the store's own result; Assistant tools report their handler's result; no separate re-read check |

## 3. What gets reused (nothing rebuilt)

Today (`core/today.py`) and every page builder as Presence's sources;
the Apps page's life-area groups and favorites (`core/focus_presets.py`)
for World and pins; the communication gate for proactive limits; the
action contract for every change; the capability map for "what can MIA
do here"; Life State and links for context; the existing Assistant page
as Conversation; the cyan Stark tokens (`web/tokens.css`).

## 4. Plan, in increments

1. ✅ **Navigation by intent** (built 2026-10-21): the sidebar becomes
   **Presence · Conversation · My Hero's Path · World · System**, then
   the person's pinned apps; the phone's bottom bar the same five.
   *World* lists every area with a live one-line status from the engine
   ("Freedom: about 770 days", "Compliance: 1 overdue", "Chickens: 9 eggs
   today"); *My Hero's Path* gathers level, active missions with their
   next step, skills and recent wins; *System* gathers the model (from
   the runtime), what MIA can do, links and connections, settings. Every
   app stays reachable.
2. ✅ **Presence** (built 2026-10-21): `core/presence.py` synthesizes what
   matters now across everything (Today's sources plus Compliance,
   Freedom, goods to sell first, eggs to carton, the open market day, the
   active mission's next step), ranked, each with **why** and whether
   it's a fact, a deadline or a suggestion, and its next useful action.
   Home leads with it.
3. ✅ **Context in every turn** (built 2026-10-21): a short "what Zac is working toward" block
   (the primary goal, the active mission, the top of Presence) in Talk's
   system message, so requests are understood in context.
4. **Objectives across modules**: one objective view joining an Intent,
   its Projects (builds) and Missions through the links store; "plan the
   greenhouse" proposes steps (a project, its budget, tasks, a mission,
   a compliance check) for approval, each executed through existing
   actions and verified by re-reading the store.
5. **Verify**: every Assistant change re-reads its record after running
   and reports only what's there.
6. **Devices**: the glasses' panels and the phone's bottom bar from the
   same Presence and World data.

## 5. Acceptance (from the spec), and how each will be shown

Objective without finding an app: Conversation and Presence first; context
without repeating: increment 3; multi-step across capabilities:
increment 4; home shows what matters: increment 2; detail on request:
World keeps every app; explains why: every Presence item has its reason;
proactive within limits: the gate stays the only way out; one engine:
no per-device logic; tests kept and extended; verified results:
increment 5.
