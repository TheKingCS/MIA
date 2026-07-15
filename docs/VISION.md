# M.I.A. — Long-Term Vision & Multi-Project Architecture

This document captures the long-term mission behind M.I.A. and how it
relates to the near-term work in `docs/ROADMAP.md`. Read this for
*why* and *where this is all going*; read `ROADMAP.md` for *what we're
actually building next*. Keeping these separate is deliberate — see
"Why this is a separate document" below.

## Mission

M.I.A. is not a chatbot. It's meant to become a modular, offline-first,
privacy-focused engineering partner, survival assistant, research
platform, automation system, and lifelong knowledge base — one whose
value compounds over years, improving through every completed project
rather than staying static.

**2026-07-14 update, at the user's explicit request: the physical end
form is a wearable, modular backpack rig** — camera, speaker, and mic
mounted to a strap, Pi5 + AI HAT+2 + battery mounted to the pack itself,
plug-and-play modules for expansion. The test for "done" the user gave
directly: **if the user couldn't happily survive any situation with
this tool, it isn't complete.** M.I.A. Core is meant to be worn, not
carried in a bag and pulled out — this changes real assumptions (always
available vs. push-to-talk-when-needed, continuous vs. session-based
data capture) that ripple into `ROADMAP.md` and `HARDWARE.md`.

Guiding principles: offline-first, privacy-first, modular, expandable
hardware, long-term maintainability, security by design, user ownership
of all data, transparent reasoning, continuous learning through
documented experience, and built to assist human decision-making rather
than replace it.

**"Privacy-first" and "log as much data about the user as possible" are
not in tension, and it's worth being explicit about why.** Privacy-first
here has always meant *no data leaves this device without you* — no
cloud dependency, no telemetry, no third party ever in the loop. It was
never a constraint on how much M.I.A. can know about its own single
owner on a device that owner fully controls. Given that, the user's
explicit call is **maximalist local logging**: track everything the
hardware can capture (position, pace, elevation, catch/tally counts,
photos, voice) rather than an artificially limited category list. The
only real constraint is hardware capability, not self-imposed scope —
see the new "Modular Backpack" section in `HARDWARE.md` for what that
actually requires physically.

## Companion philosophy (2026-07-15 update)

At the user's explicit request, this section is the new interpretive
lens for every future feature decision, not just an added bullet list:
**M.I.A. should not feel like software.** She should feel like an
intelligent companion and personal operating system that naturally
assists the user throughout daily life — every module, memory,
tutorial, and interface contributing to one cohesive experience instead
of feeling like separate apps bolted together. The user's own litmus
test, to be applied to every future feature: *"Does this make M.I.A.
feel more like a knowledgeable companion?"*

Four structural principles fall out of that test, each with real
implications for how this codebase is built going forward, not just how
it's marketed:

1. **Voice-first design.** Voice should eventually become the primary
   interface — the user speaks naturally ("Add a mission," "Start my
   next workout," "Teach me how finances work") and M.I.A. understands
   intent rather than requiring rigid commands or menu-hunting. Today's
   Assistant (v0.5+) already does tool-calling intent recognition over
   text/voice input; this principle means every *future* module's
   primary interaction path should be designed voice-first, with the
   GUI as a supporting visual, not the other way around.
2. **Intelligent UI navigation.** The GUI should react to the
   conversation, not require it. When the user asks M.I.A. to do
   something, the interface should navigate to the right module and
   visually perform the action *while the conversation continues* — "Add
   a mission" should open Missions, show the New Mission form, and fill
   it in live as M.I.A. asks for the title and objectives, not just
   silently call `add_mission` in the background the way tool calls work
   today. This is a genuinely new capability, not a bigger version of an
   existing one — see the architecture note below.
3. **Proactive, not just reactive.** Startup should greet the user with
   an intelligent summary ("Good evening Zac, let's review today's
   information") instead of a static dashboard, and M.I.A. should
   continuously analyze recent activity to make unprompted, *actually
   useful* suggestions (recovery after intense workouts, a grocery trip
   when supplies run low, a birthday gift reminder before the date) —
   calibrated to feel helpful, never naggy.
4. **Multi-platform, one companion.** The same assistant, memory, and
   modules should eventually be reachable from desktop, web browser,
   mobile, the Pi5 wearable, voice-only, and future AR/XR (Meta Quest
   browser named explicitly) — moving between devices should never feel
   like switching apps. This is the largest architectural fork in this
   update; see "Critical evaluation" below before assuming it's additive
   work.

**New subsystems named in this update**, each real enough to eventually
warrant its own `core/*_manager.py` + module, roughly in the same shape
as Missions/Expedition Mode/Field Kit before them: a **Memory Palace**
(categorized, interconnected memory — Family/Programming/Fitness/
Fishing/Projects/Travel/Cooking/Finance/Pets/Education/Work — replacing
today's flat `UserMemory` list, not just extending it), **Relationship
Profiles** (people M.I.A. knows — birthdays, favorite things, gift
ideas, shared memories, optionally tied to visual recognition when
hardware supports it) and **Pet Profiles** (names, photos, medical
history, vet visits) as structured extensions of the same idea, a
**Workout Module** (personal-trainer-style guided sessions: sets, reps,
weight, rest timers, calorie estimates, PRs, progress charts), a
**Kitchen Module** (recipes, inventory, grocery lists, nutrition,
meal-frequency tracking, suggestions from what's on hand), **Finance**
(budgets, savings, mortgage/loan payoff, rental/real-estate, crypto,
stocks, net worth, cash flow, with projections), an expanded **Smart
Home & Homestead** domain (lighting/cameras/doors/sensors/garden
automation/solar/weather stations — overlaps and merges with the
already-planned Agriculture/Smart Home sections below), a **Smart
Suggestions** engine (the proactive-recommendation half of principle 3
above), a **Startup Dashboard Briefing** (the proactive half of the
existing Home Dashboard), an **interactive first-time onboarding**
(M.I.A. teaches herself through real conversation and real tasks, not
docs/slides) and an always-available **modular tutorial system** ("Teach
me how quests work," organized by category and skill level, with M.I.A.
proactively suggesting a walkthrough for never-used features), and
**self-knowledge** (M.I.A. should be able to explain any of her own
modules/features/workflows conversationally — the user should never need
to read documentation). Motivation & celebration already exists in
scoped form (Mission completions, per `core/mission_manager.py`) and
this update generalizes it to *every* meaningful milestone (birthdays,
workout PRs, coding milestones, savings milestones, learning streaks).

## The four-project architecture

| Project | Role | Status |
|---|---|---|
| **1. M.I.A.** | "The Brain" — the portable field device and its core intelligence | **In progress.** This is "M.I.A. Core," the Pi5 kiosk device documented in `ROADMAP.md`, currently at v0.2. |
| **2. Personal Home Cloud Infrastructure** | "The Nervous System" — a stationary, more powerful compute extension the Pi5 docks to or syncs with | Not started. This is where compute-heavy reasoning belongs (see below). |
| **3. Smart Environment** | "The Senses" — sensor networks, environmental monitoring, smart home integration | Not started. Overlaps with the Agriculture/Smart Home/Power sections already planned in `ROADMAP.md`. |
| **4. Robotics and Physical Systems** | "The Hands" — robotic arms, drones, mobile robots, prosthetic research | Not started. Overlaps with the Fleet section already planned in `ROADMAP.md`. |

**Every future project should expand M.I.A.'s capabilities, and every
improvement to M.I.A. should make future projects easier.** That
compounding relationship is the actual long-term goal — not any single
feature.

## Why this is a separate document from ROADMAP.md

This vision includes ideas (a multi-agent "Expert Council," genetic
algorithms, particle swarm optimization, a full simulation layer) that
are individually large enough to be their own multi-year efforts. If
they lived in the same document as the concrete, testable v0.2/v0.3
milestones, it would become impossible to tell "what we're building
this month" from "what we might build in year three" — and that
confusion is the single biggest risk to this project actually shipping
a working device. This document is the North Star. `ROADMAP.md` is the
map of the next several steps. Neither should be edited to look like
the other.

## Critical evaluation (honest assessment, not just enthusiasm)

- **Scope is the primary risk.** An Expert Council of debating
  specialized AI agents, genetic/PSO optimization, and a full
  simulation-before-recommending layer are each substantial research
  efforts on their own. Treat everything in this document beyond
  "Project 1, current phase" as aspirational and revisit-when-ready,
  not as a backlog to start executing now.
- **Hardware mismatch is real, but the document already contains its
  own answer.** None of the compute-heavy reasoning (Expert Council,
  GA/PSO, simulation) belongs on the Pi5 — it belongs on Project 2 (the
  Home Cloud "Nervous System"). The Pi5's job is to stay light,
  reliable, and always-available; the home system's job is to do heavy
  reasoning and sync results back down. This is also the real
  justification for the "dock to a computer" goal from the original
  brief — it's not just file transfer, it's compute offload.
- **"Continuous learning from every project" should start boring, not
  clever.** The realistic v1 of this is structured logging (already
  designed into the event bus / Activity Log) plus good search over
  your own project history — not machine learning. "I found two
  previous robotic arm projects, Project B used stronger servos" is
  achievable with a well-indexed database and an LLM summarizing
  retrieved records, long before anything resembling true learning is
  needed.
- **Security architecture is correctly flagged as mandatory, but is
  currently a gap.** v0.2 only has Backup/Restore. Encrypted backups
  and encrypted credential storage (wifi passwords, radio configs, any
  future API keys) should be pulled forward into the roadmap; full
  role-based permissions and audit logging are reasonable to defer
  until multiple profiles or networked access make them necessary.
- **Missing principle, worth adding explicitly: graceful degradation.**
  A device this dependent on sensors, radios, and an AI assistant needs
  a defined "safe mode" — if the Assistant or any single module fails,
  the base device (reference library, calculator, comms, navigation)
  must keep working. `ModuleManager`'s per-module failure isolation
  already supports this by accident; it should be treated as a first
  principle going forward, not an implementation detail.
- **Camera + on-device species/plant identification is the single
  biggest new scope item introduced by the wearable-companion vision.**
  It's a real image-classification workload, meaningfully harder than
  the text tool-calling this project has built so far — there's no
  camera in `HARDWARE.md` yet, and the AI HAT+2's Hailo-10H is a
  plausible fit for lightweight on-device classification (Hailo's own
  docs mention smart search/captioning), but "identify this plant with
  no connectivity" may realistically need to be "capture now, identify
  when docked to Project 2's Home compute" for v1, consistent with the
  Expert Council compute-offload reasoning already established below.
- **Live position/pace tracking just became load-bearing, not
  optional.** "Hiked 11 miles at an average pace of 5 mph" requires
  continuous position data, not the existing manual-waypoint-based
  distance calculator. GPS moves from "defer until Navigation's later
  phase" (its status through 2026-07-13) to something the Memories
  vision genuinely depends on — see `HARDWARE.md`'s updated GPS note.
- **Multi-platform architecture is the single largest new fork this
  update introduces, and it is genuinely a fork, not additive work.**
  Today's `core`/`modules`/`gui` layering (see `CLAUDE.md`) is a
  single-process desktop app — `gui/` calls straight into `core/`
  services in-process. Real web/mobile/XR frontends need those same
  services reachable as a real API boundary (a backend M.I.A. process
  exposing itself over HTTP/WebSocket, with `gui/`'s PySide6 code
  becoming *one client among several* rather than the only one) — a
  genuine rearchitecture of the boundary this project has enforced
  since v0.1, not a new module. It is **not yet decided** whether that
  backend lives on the Pi5 itself (a phone/browser on the same network
  talks to Core directly) or is a Project 2 (Home Cloud) capability
  the Pi5 docks/syncs to, matching this document's existing "Pi5 stays
  light, Home does heavy lifting" principle for Expert Council/GA/PSO
  above — resolve this deliberately, with a real design pass, before
  writing any client/server code; don't let it get implicitly decided
  by whichever frontend happens to get built first.
- **Intelligent UI navigation needs a genuinely new tool category, not
  a bigger version of the existing one.** Today's Assistant tool-calling
  (domain-scoped, 2026-07-14) executes a data action
  (`add_mission`, `set_theme`, ...) silently in the background — the
  user sees the reply, not the mechanism. "Open Missions, show the form,
  fill it in live while asking follow-up questions" is a *UI-driving*
  tool, not a data tool: it needs the conversation and the on-screen
  form to stay in sync turn-by-turn (open → populate field → ask next
  question → populate next field → confirm), which is a new
  interaction pattern this codebase doesn't have yet, closer to a
  guided wizard driven by conversation state than a single tool call.
  Design it as its own scoped effort rather than assuming it falls out
  of the existing action-registry pattern for free.
- **Memory Palace is a real data-model migration, not an additive
  feature.** `core/user_memory_manager.py`'s `UserMemory` is currently a
  flat list with case-insensitive dedup (built 2026-07-14, part 5).
  Reorganizing into categories with cross-references ("intelligent
  memory trees") needs a schema change and a migration path for
  whatever memories already exist in a user's real `data/*.json` before
  this ships — don't design it as a pure addition on top of the current
  shape.
- **This update's own scope is, by a wide margin, the largest single
  addition to this document since the 2026-07-14 wearable-companion
  pass** — voice-first primacy, intelligent UI navigation, proactive
  suggestions, a startup briefing, five-plus new content modules
  (Workout, Kitchen, Finance, Relationship Profiles, Pet Profiles),
  Memory Palace, onboarding, a tutorial system, self-knowledge, and
  multi-platform/browser/XR support. Per this document's own
  established discipline ("Scope is the primary risk," above): treat
  everything here as the new North Star, not a backlog to start
  executing all at once — pick one lowest-risk, self-contained slice at
  a time (the same discipline that took Memories/Missions/Home Dock
  from vision to shipped code one at a time in 2026-07-14), sequenced
  deliberately rather than guessed at.

## Where the new concepts map into existing plans

| Vision concept | Where it lives |
|---|---|
| Artificial Expert Council (multi-agent debate) | Project 2 (Home Cloud). Not feasible on Pi5 hardware; the Assistant module (v0.5) stays a single capable model on-device, with an optional "consult the Council" action that hands off to Project 2 when connected. |
| Genetic Algorithms / Particle Swarm Optimization | Project 2. A future "Optimization Engine" service, invoked by Workshop & Electronics / The Lab modules when docked to Project 2's compute. |
| Simulation Layer | Project 2, same reasoning as above. |
| Continuous Learning Framework / Personal Engineering Database | Extends the already-planned Data Logger, Notes/Journal Engine, and Activity Log (see `ROADMAP.md`'s shared core services) — implemented as structured storage + search, not ML, for the foreseeable future. Directly answers the "what did I do on Project Rocket Boots" goal from earlier. |
| Security Architecture (encryption, RBAC, audit log) | Pulled forward into v0.2's Backup/Restore milestone (encrypted backups, encrypted credential storage) with RBAC/audit logging deferred to whenever multi-profile or networked access makes them load-bearing. |
| Character/avatar, personality, transparency about uncertainty | Already planned — v0.6 Character/companion system, event-bus driven. |
| Smart Environment (sensors, GPS, LoRa, SDR, cameras) | Already covered by Project 1's Communications, Navigation, Agriculture, and Smart Home sections; Project 3 is the larger-scale version of the same idea once dedicated sensor infrastructure exists beyond the Pi5 itself. |
| Robotics / Drones / prosthetics research | Already covered by Project 1's Fleet section for what connects directly to the Pi5; Project 4 is the larger standalone robotics effort. |
| **Missions/Gamification** (2026-07-14 addition: turn hobbies/goals into objectives with tracked progress, e.g. "Master Baiter" — fish for N hours, catch N fish) | Project 1, new core service (`core/mission_manager.py`), a consumer of the event bus / Activity Log rather than its own data-capture mechanism — objectives derive progress from Trip timings, a new lightweight per-trip tally primitive (catch counts, species identified, etc.), and existing manager events wherever possible instead of duplicating data capture. |
| **Memories** (2026-07-14 addition: auto-generated trip recaps — distance/pace/duration/catches/species/photos — plus location-tagged logs surfaced on the offline maps) | Project 1. Already had a placeholder as an "ambient" section in `ROADMAP.md`'s module list; promoted to a real top-level module per the user's explicit ask for a visitable "Memories section." Mostly an aggregation/read layer over Expedition/Trip/Waypoint/Journal data that already exists, plus a photo gallery over `trip_photos/` — the lowest-new-design-risk piece of this whole addition, and the first one being built. |
| **Home Dock auto-launch Dashboard** (2026-07-14 addition: docking Core to the Home desktop opens M.I.A. automatically to a dashboard of recent events/objectives/photos/music/projects and upcoming items) | Project 1/2 boundary. Extends v0.13's Core/Home device-profile split and v0.15's Expedition-sync docking detection (Field Kit already detects a docked Core) — mostly orchestration (launch-on-dock, a new Dashboard view) rather than new architecture. |
| **Vitals/Stats logging** (2026-07-14 addition: maximalist local logging of user activity/position/pace/biometrics as hardware allows) | Project 1, new core service. Deliberately maximalist rather than category-limited, per the Mission section's reconciliation with "privacy-first" above — the only real ceiling is hardware capability (GPS, IMU, camera, mic), not self-imposed scope. |
| **Modular wearable backpack form factor** (2026-07-14 addition: camera/speaker/mic on the strap, Pi5+HAT+battery on the pack, plug-and-play expansion modules) | Physical/industrial design work, not software — tracked in `HARDWARE.md`'s new "Modular Backpack" section as its own parallel track, same way Fleet/Communications hardware choices are deferred until acquired. |
| **Memory Palace** (2026-07-15 addition: categorized, cross-referenced memory trees instead of a flat fact list) | Project 1. A schema/migration on `core/user_memory_manager.py`, not a new service — see the critical-evaluation note above on why this isn't purely additive. |
| **Intelligent UI Navigation** (2026-07-15 addition: the GUI opens the right module and fills in a form live while the conversation continues) | Project 1. A new tool category alongside the existing domain-scoped data tools (2026-07-14) — see the critical-evaluation note above; needed before voice-first can feel seamless rather than "chat, then go check the screen." |
| **Voice-first primacy** (2026-07-15 addition: voice becomes the primary interface, GUI a supporting visual) | Project 1. UX-sequencing principle applied to every future module's design, not a new service — today's push-to-talk Assistant voice path (v0.5+) is the existing foundation. |
| **Startup Dashboard Briefing** (2026-07-15 addition: an intelligent spoken/written summary at launch instead of a static dashboard) | Project 1. Extends `gui/home_dashboard.py` (2026-07-14) and the Assistant's info-question path (2026-07-14 part 5) — an aggregation + summarization layer over data that mostly already exists (quests/Missions, Calendar, Memories, Projects, notifications), plus whatever new domains (weather, workout, finance, smart home) ship first. |
| **Smart Suggestions** (2026-07-15 addition: proactive, unprompted recommendations from recent activity) | Project 1, new core service. Same "structured logging + retrieval, not ML" realism principle already established for Continuous Learning above — the existing `core/daily_occasions.py` (2026-07-14, birthday/calendar/check-in) is the direct precedent and likely extension point, not a new mechanism from scratch. |
| **Workout Module** (2026-07-15 addition: personal-trainer-style guided sessions, PRs, progress charts) | Project 1, new module + `core/workout_manager.py`, same CRUD-plus-Assistant-hooks shape as Missions/Expedition Mode. Live guided-session timers/rest-tracking are the genuinely new UI pattern here (closest existing precedent: Expedition Mode's speed/splits tracking). |
| **Kitchen Module** (2026-07-15 addition: recipes, inventory, grocery lists, nutrition, meal suggestions) | Project 1, new module. Overlaps in spirit with the already-planned Agriculture section (garden → kitchen supply chain is a natural future link, not built yet). |
| **Finance** (2026-07-15 addition: budgets, savings, mortgage/loan payoff, real estate, crypto, stocks, net worth, cash flow, projections) | Project 1 for read/tracking + local projections; anything requiring live market data crosses this project's offline-first principle and needs its own explicit online/offline scoping decision before building, same discipline as every other network-dependent feature here. |
| **Smart Home & Homestead** (2026-07-15 addition: lighting, cameras, doors, sensors, garden automation, solar, weather stations) | Project 1/3 boundary — merges into the already-planned Smart Home/Agriculture sections in `ROADMAP.md`'s v1.0+ bucket and Project 3 ("The Senses") above; all genuinely hardware-gated, same treatment as Fleet/Communications. |
| **Relationship Profiles** (2026-07-15 addition: people M.I.A. knows — birthdays, gift ideas, shared memories, optional visual recognition) | Project 1, new core service, a structured extension of Memory Palace scoped to people specifically. Visual recognition ("who am I looking at") needs the camera hardware/on-device classification already flagged as this vision's biggest open hardware question above — text-only profiles (no recognition) are buildable now; recognition is not. |
| **Pet Profiles** (2026-07-15 addition: names, photos, medical history, vet visits) | Project 1, same shape as Relationship Profiles, camera-independent (no recognition implied) so fully buildable now. |
| **Interactive onboarding + modular tutorial system** (2026-07-15 addition: M.I.A. teaches herself through real conversation and real tasks, always available via "teach me how X works") | Project 1. Builds on the existing Assistant conversation/personality pipeline (2026-07-14 part 5) plus `looks_like_action_request()`-style intent classification — a new "teaching mode" conversation path, not a new backend. |
| **Self-knowledge** (2026-07-15 addition: M.I.A. can explain any of her own modules/features/workflows conversationally) | Project 1. Directly extends `core/device_help_manager.py`'s existing end-user-docs grounding (2026-07-14 part 4) — that system already answers "how do I use X"; this generalizes its coverage and hooks it into the tutorial system above rather than replacing it. |
| **Multi-platform architecture + browser/XR support** (2026-07-15 addition: the same assistant/memory/modules reachable from desktop, web, mobile, wearable, voice-only, and future AR/XR) | Project 1/2 boundary, genuinely undecided which — see the dedicated critical-evaluation note above. The largest architectural fork in this update; do not start client/server code before that design pass happens. |

## Realistic phased horizon (coarse-grained, not a commitment)

| Horizon | Focus |
|---|---|
| **Now** | Project 1, M.I.A. Core v0.2–v1.0 per `ROADMAP.md` — a working, reliable, offline field device |
| **Next** | Project 1 continues to v1.0+ (Fleet, Communications, Navigation, Agriculture, Medical, etc., as real hardware is acquired) |
| **Later** | Project 2 (Home Cloud) begins — this is where Expert Council, GA/PSO, and simulation become realistic to attempt, once Project 1 is stable and there's a genuine compute-offload target to build against |
| **Eventually** | Projects 3 and 4 — likely absorbed largely into Project 1's existing section structure rather than needing wholly separate builds, revisited once real hardware for each exists |

The goal is not to build every capability in this document. The goal
is a device that is genuinely useful today, architected so that none of
these future directions are foreclosed.
