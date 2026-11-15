# MIA OS: the feature ecosystem (Prompt 02)

*Claude, 2026-11-15. This builds on Prompt 01 (`MIA_OS_FEATURE_INVENTORY.md`),
whose statuses come from evidence. It uses Zac's answers of 2026-11-15
(DEC-0159 to DEC-0164).*

*Labels:*
- ***Exists**: in code, with the status shown in the inventory.*
- ***Committed**: Zac has asked for it (a decision or a handoff).*
- ***Documented plan**: in repo docs, not yet asked for again.*
- ***Proposed**: Claude's new recommendation, not committed.*

## 1. What MIA is, as an ecosystem

MIA has one intelligence, one identity per person, one set of stores and
one action contract. Around them sit many apps that are useful on their
own and become more useful together, because they share:
- the person (`core/profile_manager.py`);
- memory (stores, life events, links);
- context (`core/presence.py`);
- the gate on speaking up (`core/communication_gate.py`);
- the approval path (`core/actions.py`).

Prompt 02's goal of an ecosystem rather than a collection of apps is
mostly already true at the data layer. The gaps are listed in §6 and in
the other Prompt 02 reports.

## 2. The functional areas (the eight destinations, DEC-0153)

| Area | What lives there | Exists | Committed additions |
|---|---|---|---|
| Dashboard | Today, Your Week, weather, mission in play, Agent Activity | yes | an LEP "Explore Today" card |
| Home | Kitchen, Smart Devices, Homestead, Recreation, Personal Tools, Learning | yes | **Smart Closet** (Personal Tools), **LEP** (Recreation) |
| Garage | vehicles, tools, work on them | yes | — |
| Finances | budget, Plaid, snapshots, businesses | yes | LEP's affordability service, destination savings |
| Health and Fitness | workouts, plans; meals planned | yes / planned | — |
| AI Tools | look, browse, read, write, inspect | yes | **Send to MIA on any selection** (DEC-0164, proposed) |
| Missions | goals, projects, the Loop, the Dungeon, XP | yes | LEP achievements; Project Japan as a long-term objective |
| Settings | you, security, your data, system | yes | speaker voice enrolment (DEC-0163) |

Living Worlds and the Convergence go through the Nexus (DEC-0153): Recreation on the PC and phone, the third screen on the glasses.

## 3. New committed subsystems

### 3.1 The Life Enrichment Protocol (DEC-0161, `docs/specs/LIFE_ENRICHMENT_PROTOCOL.md`)

LEP is a planner and discovery system built **on existing services**, not
beside them:

| LEP needs | Reuses | Missing today |
|---|---|---|
| where the person is and how far to go | `core/places.py`, `core/maps_web.py`, `trip_route.py` | a home region and travel radii as person settings |
| weather | `core/weather.py` | — |
| calendar and free time | `core/calendar_manager.py`, the Loop (`core/the_loop.py` knows work and chore rhythms) | shared free time across two people |
| what's affordable | `core/finance_manager.py`, `budget_manager.py`, `finance_summary.py` | **a "discretionary money" calculation** (balance minus bills, goals and reserves), worked out in code |
| memories and photos | `core/memory_vault.py`, journal, `life_events` | an "experience" record type linked to photos |
| speaking up | `core/communication_gate.py` | LEP candidates (festival this Saturday, open Saturday) |
| trips and outings | `core/trip_manager.py`, `expedition_manager.py` | itineraries with several stops |
| achievements | missions and XP | LEP achievements (encouraging, never punishing: DEC-0014) |
| long-term objective | projects (DEC-0152) and learning paths (`core/paths.py`, for Japanese) | Project Japan as a project with phases and savings |
| event discovery | `core/online_lookup.py` (only when asked) | **source adapters and a background discovery job**: new, and it goes online, so it needs Zac's approval of what may be fetched |

**It's new in kind.** LEP is the first feature that would *routinely* go
online in the background (event discovery). That needs a policy decision
(Q-08).

### 3.2 Smart Closet (DEC-0162, `docs/specs/SMART_CLOSET.md`)

It is a personal store of clothes and outfits, with suggestions worked out
in code from:
- the weather;
- the day's calendar (work, gym, a date, an event);
- formality;
- what hasn't been worn lately;
- the person's ratings.

It reuses `core/weather.py`, the calendar, the Loop (work days),
`memory_vault` (photos) and the action contract. **The minimum version is
being built now** (Zac asked for it to be implemented); later stages are
in the spec.

### 3.3 Shared conversation and speaker identification (DEC-0163)

Two people talk to MIA together, and MIA knows who is speaking. It needs:
- voice enrolment per person, kept on the device;
- a speaker-identification stage between speech-to-text and the turn;
- each turn running as that person (`view_for()` already exists);
- "who's this?" when unsure.

Today there is no speaker identification and no wake word. Detailed
requirements are in `MIA_OS_MULTI_USER_REQUIREMENTS.md`, and the
technology is chosen in Prompt 07.

### 3.4 Send to MIA on any selection (DEC-0164, proposed)

This is an OS-wide action on selected text, files or images:
- research it;
- make a skill or learning path from it;
- convert it;
- draft an email (a draft only: DEC rule);
- remember it;
- make a mission from it.

**It is buildable today without MIA OS:**
- On Android, as a text-selection menu entry (`PROCESS_TEXT`) and a share target. `Share.kt` already exists for sharing.
- On Windows, as a global hotkey or a context-menu entry.

On MIA OS it becomes a system service. Each choice turns into an action
proposal; the selection is untrusted text.

## 4. How MIA and the apps relate (Prompt 02 §7)

Every feature already supports the first two patterns:
- **On its own:** each app is a screen, and works with the model off (the screens don't need the LLM).
- **By voice or chat:** each action has a tool twin (parity, DEC-0125; `core/parity.py` measures it).

The third pattern is partial:
- **Across apps:** today it means missions linking to everything, upkeep missions, and the Loop pulling in work, chores and the Dungeon. **There is no general planner** that composes several apps' actions into one approved plan ("prepare everything for this weekend's greenhouse expansion"). That is Prompt 08's job, but Prompt 02 records the requirement (FR-X1 in the acceptance requirements).

## 5. Existing versus future, in one view

- **Exists, used daily:**
  - conversation and tools;
  - dashboard;
  - missions, projects, the Loop and the Dungeon;
  - finances;
  - kitchen;
  - calendar;
  - phone sync;
  - glasses cards;
  - Memory Vault;
  - workouts;
  - homestead (simulation).
- **Committed, not built:**
  - LEP;
  - Smart Closet (now in progress);
  - speaker identification;
  - Health meals;
  - wake word;
  - the Convergence.
- **Documented plans:**
  - phone-call conversation mode;
  - the device fabric (DEC-0128);
  - taught procedures (DEC-0123);
  - Living Worlds phases 2–4.
- **Proposed by Claude here:**
  - a discretionary-money service;
  - an "experience" record;
  - workspaces built from projects (`MIA_OS_WORKSPACE_AND_CONTEXT_MODEL.md`);
  - a cross-app planner (with Prompt 08);
  - the "Send to MIA" service (Zac's idea, worked up).

## 6. Where the ecosystem is weakest

1. **One owner per fact** is missing in a few places (R-10). LEP and Smart Closet must not add more: they read the money, weather and calendar services, never copy them.
2. **Background work that goes online** has no policy. LEP is the first to need one (Q-08).
3. **Two people at once** has no identity layer (DEC-0163).
4. **Cross-app plans** have no planner (Prompt 08).
5. **Discovery:** with ~378 tools and 102 pages, finding a capability depends on search and asking MIA. See `MIA_OS_NAVIGATION_AND_DISCOVERY.md`.
