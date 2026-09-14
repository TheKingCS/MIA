# MIA — Long-Term Vision & Multi-Project Architecture

This document captures the long-term mission behind MIA and how it
relates to the near-term work in `docs/ROADMAP.md`. Read this for
*why* and *where this is all going*; read `ROADMAP.md` for *what we're
actually building next*. Keeping these separate is deliberate — see
"Why this is a separate document" below.

## Mission

MIA is not a chatbot. It's meant to become a modular, offline-first,
privacy-focused engineering partner, survival assistant, research
platform, automation system, and lifelong knowledge base — one whose
value compounds over years, improving through every completed project
rather than staying static.

**2026-07-14 update, at the user's explicit request: the physical end
form is a wearable, modular backpack rig** — **2026-07-15: refined into
two concrete physical units**, a Compute Block (Pi5 + AI HAT+2 +
battery/UPS + storage, one enclosure, side-of-backpack) and a separate
Receiver (camera + speaker + mic bundled together, worn on the strap or
chest-mounted, connected back to the Compute Block by cable) — full
detail, connector recommendation, and solar-charging requirement in
`docs/HARDWARE.md`'s "Modular Backpack" section; read that fresh rather
than trusting this summary as it evolves. The test for "done" the user gave
directly: **if the user couldn't happily survive any situation with
this tool, it isn't complete.** MIA Core is meant to be worn, not
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
never a constraint on how much MIA can know about its own single
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
**MIA should not feel like software.** She should feel like an
intelligent companion and personal operating system that naturally
assists the user throughout daily life — every module, memory,
tutorial, and interface contributing to one cohesive experience instead
of feeling like separate apps bolted together. The user's own litmus
test, to be applied to every future feature: *"Does this make MIA
feel more like a knowledgeable companion?"*

Four structural principles fall out of that test, each with real
implications for how this codebase is built going forward, not just how
it's marketed:

1. **Voice-first design.** Voice should eventually become the primary
   interface — the user speaks naturally ("Add a mission," "Start my
   next workout," "Teach me how finances work") and MIA understands
   intent rather than requiring rigid commands or menu-hunting. Today's
   Assistant (v0.5+) already does tool-calling intent recognition over
   text/voice input; this principle means every *future* module's
   primary interaction path should be designed voice-first, with the
   GUI as a supporting visual, not the other way around.
2. **Intelligent UI navigation.** The GUI should react to the
   conversation, not require it. When the user asks MIA to do
   something, the interface should navigate to the right module and
   visually perform the action *while the conversation continues* — "Add
   a mission" should open Missions, show the New Mission form, and fill
   it in live as MIA asks for the title and objectives, not just
   silently call `add_mission` in the background the way tool calls work
   today. This is a genuinely new capability, not a bigger version of an
   existing one — see the architecture note below.
3. **Proactive, not just reactive.** Startup should greet the user with
   an intelligent summary ("Good evening Zac, let's review today's
   information") instead of a static dashboard, and MIA should
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

### The voice-only operability test (2026-07-15 sharpening)

Principles 1 and 2 above were written somewhat abstractly; the user
gave a much sharper, concrete standard for what they actually mean in
practice, prompted by a real complaint that the startup briefing felt
like "reading a script" rather than genuinely understanding the
dashboard: **the test for whether MIA's voice/companion layer is
good enough is whether a user could operate the entire application
using voice alone** — not "voice as one more input method alongside
touch," but voice as a fully sufficient control surface on its own.
The user's own framing, worth preserving close to verbatim since it's
the clearest statement of this principle so far: *"Think about how the
user would interact with a device system like this in real life. It
should work like a game guide with a tutorial for use over voice."*

That "game guide" framing is doing real work and shouldn't be
flattened into generic "voice commands":

- **Deep, current understanding of every module's data and
  capabilities, not just the Assistant's own tool registry.** Today's
  self-knowledge work (`docs/ASSISTANT_CAPABILITIES.md`) covers tool
  *actions* — this goes further: MIA should be able to describe
  what's currently *displayed* in any widget or module (not just that
  a `list_missions` tool exists), have a conversation about that live
  data, and act on it — including a widget's own interaction menu
  (`gui/dashboard_customize_dialog.py`'s "⋯" actions), not just its
  headline tool calls.
- **A guide, not just a command executor.** A game guide doesn't wait
  to be asked the exact right question — it teaches capabilities
  proactively, in context, the way a good tutorial reveals mechanics as
  a player needs them. This is the through-line connecting several
  previously-separate items in this document: self-knowledge (knowing
  the answer), the modular tutorial system (teaching it), and
  intelligent UI navigation (demonstrating it live on screen while
  explaining it) are really one capability — "MIA as tutor," not
  three unrelated features.
- **The dashboard/widget disconnect that prompted this is a concrete
  instance of a general problem, not a one-off bug.** The startup
  briefing checked a fixed, hardcoded list of data sources instead of
  reflecting whatever's actually on the dashboard — worth fixing on its
  own, but the deeper point is that *any* place MIA talks about
  "what's going on" needs to stay live-synced to real app state as that
  state grows (more widgets, more modules), not re-hardcoded by hand
  each time a new one ships.

**Not scoped or sequenced yet** — this is a real north-star sharpening,
not a build plan. `docs/ROADMAP.md` should carry the concrete first
slice picked from this (see its own entry for what actually got built
first) rather than this document trying to plan the whole thing.

**New subsystems named in this update**, each real enough to eventually
warrant its own `core/*_manager.py` + module, roughly in the same shape
as Missions/Expedition Mode/Field Kit before them: a **Memory Palace**
(categorized, interconnected memory — Family/Programming/Fitness/
Fishing/Projects/Travel/Cooking/Finance/Pets/Education/Work — replacing
today's flat `UserMemory` list, not just extending it — categorization
half built 2026-09-10 as a real `category` field + LLM-based
extraction-time tagging on the existing `core/user_memory_manager.py`,
deliberately not a rename, see the critical-evaluation note below;
cross-linking also built 2026-09-10 — `related_memories()`, a pure
keyword-overlap computation, surfaced as a "Related:" line per memory;
deliberately unpersisted, see the table row below for why. A fuller
graph/tree visualization is still unbuilt), **Relationship
Profiles** (people MIA knows — birthdays, favorite things, gift
ideas, shared memories, optionally tied to visual recognition when
hardware supports it — text-only profiles built 2026-09-10,
`core/relationships_manager.py` + `modules/relationships/module.py`;
visual recognition still needs the camera hardware this vision already
flags as its biggest open question) and **Pet Profiles** (names,
photos, medical history, vet visits — medical-history/notes built
2026-09-10 alongside Relationship Profiles; photos deliberately
deferred, real file-import scope beyond that pass) as structured
extensions of the same idea, a
**Workout Module** (personal-trainer-style guided sessions: sets, reps,
weight, rest timers, calorie estimates, PRs, progress charts — built
2026-09-10, `modules/workout/module.py`), a
**Kitchen Module** (recipes, inventory, grocery lists, nutrition,
meal-frequency tracking, suggestions from what's on hand — built
2026-09-10, `modules/kitchen/module.py`), **Finance**
(budgets, savings, mortgage/loan payoff, rental/real-estate, crypto,
stocks, net worth, cash flow, with projections), an expanded **Smart
Home & Homestead** domain (lighting/cameras/doors/sensors/garden
automation/solar/weather stations — overlaps and merges with the
already-planned Agriculture/Smart Home sections below), a **Smart
Suggestions** engine (the proactive-recommendation half of principle 3
above — built 2026-09-10, `core/smart_suggestions.py`, covering the
recovery/grocery-trip examples; the birthday-gift-reminder example
closed the same day once Relationship Profiles shipped, all 3 of
VISION's own named examples now built), a **Startup
Dashboard Briefing** (the proactive half of the
existing Home Dashboard — built 2026-07-15, extended 2026-09-10 with
highlight providers for the newer Budget/Maintenance/Kitchen/Workout/
Relationships widgets), an **interactive first-time onboarding**
(MIA teaches herself through real conversation and real tasks, not
docs/slides — a one-time welcome message built 2026-09-10) and an
always-available **modular tutorial system** ("Teach me how quests
work" — the teaching-mode conversation path built 2026-09-10;
proactively suggesting a walkthrough for never-used features built
2026-09-14, `core/usage_tracker.py` + `core/smart_suggestions.py`'s
`build_walkthrough_suggestion()`, see `ROADMAP.md`'s matching entry;
category/skill-level organization of the tutorial content itself is
still unbuilt), and
**self-knowledge** (MIA should be able to explain any of her own
modules/features/workflows conversationally — the user should never need
to read documentation). Motivation & celebration already exists in
scoped form (Mission completions, per `core/mission_manager.py`) and
this update generalizes it to *every* meaningful milestone (birthdays,
workout PRs, coding milestones, savings milestones, learning streaks).

## The four-project architecture

| Project | Role | Status |
|---|---|---|
| **1. MIA** | "The Brain" — the portable field device and its core intelligence | **In progress.** This is "MIA Core," the Pi5 kiosk device documented in `ROADMAP.md`, currently at v0.2. |
| **2. Personal Home Cloud Infrastructure** | "The Nervous System" — a stationary, more powerful compute extension the Pi5 docks to or syncs with | **Hardware being built as of 2026-07-15** (AMD Ryzen 9800X3D + Radeon 7900 XTX, see `HARDWARE.md`'s new Project 2 section) — software (the hand-off mechanism, the streaming access mode) not started. This is where compute-heavy reasoning belongs (see below and the new "Core/Home split" section). |
| **3. Smart Environment** | "The Senses" — sensor networks, environmental monitoring, smart home integration | Not started. Overlaps with the Agriculture/Smart Home/Power sections already planned in `ROADMAP.md`. |
| **4. Robotics and Physical Systems** | "The Hands" — robotic arms, drones, mobile robots, prosthetic research | Not started. Overlaps with the Fleet section already planned in `ROADMAP.md`. |

**Every future project should expand MIA's capabilities, and every
improvement to MIA should make future projects easier.** That
compounding relationship is the actual long-term goal — not any single
feature.

## Core/Home split — the resolved architecture (2026-07-15)

Resolves the "multi-platform architecture" fork flagged earlier in this
document. Prompted by a direct question: could the wearable Core device
be both small-form-factor *and* capable of deep, open-ended reasoning
fully offline? Answered honestly rather than optimistically — no, and
it's worth being precise about why, since it's a hardware/market
reality, not a gap in this project's engineering.

### What Core (Pi5 + AI HAT+2) can actually be expected to handle offline

Grounded in what this project has already measured, plus `HARDWARE.md`'s
already-documented Hailo-10H ceiling (40 TOPS INT4, 8GB dedicated RAM,
**realistic model size 1–7B parameters**) — not aspiration:

**Reliable, fully offline, no change of scope needed:**
- Tool-calling/action execution — the entire 54-action registry (see
  `docs/ASSISTANT_CAPABILITIES.md`) and its natural growth, *as long as
  per-request tool count stays bounded* via domain-scoped attachment.
  This is a software discipline, not a hardware ceiling — the existing
  architecture already gets this right.
- Short-to-medium conversational replies, personality/warmth, proactive
  daily behaviors (birthday/calendar/check-in), persistent memory
  (extraction + storage) — all lightweight generation tasks, well
  within a small model's actual strengths.
- Retrieval-grounded "how do I use X" answers
  (`core/device_help_manager.py`) — cheap by design (a few relevant
  chunks, not an open-ended reasoning task).
- Voice in/out (Vosk/Piper) — CPU-only, lightweight relative to LLM
  inference, doesn't need the NPU at all.
- Lightweight on-device image classification (species/plant ID) — this
  is arguably the Hailo chip's actual home turf; Hailo NPUs originate
  from vision-inference acceleration, and Hailo's own docs name smart
  search/captioning explicitly. More likely to work well than deep text
  reasoning on the same chip, though still unverified on real hardware
  (`HARDWARE.md`'s Camera section).

**Not reliably achievable on this hardware, confirmed by this
project's own evidence, not just a spec-sheet inference:** deep,
open-ended, multi-step reasoning, or robustly handling a long/rich
system prompt with many simultaneous instructions. The 2026-07-14
model-upgrade experiment already tested the top of the HAT's realistic
range head-to-head — `qwen2.5:7b` against the current `llama3.2:3b` —
and the 7B model was *worse*, not better: lower accuracy (58/60 vs.
60/60) and ~5x slower. That was on CPU, not the Hailo NPU specifically,
but it's real evidence that "bigger model, same size class" doesn't
reliably buy more prompt robustness — so there's no reason to expect
simply reaching the HAT's 7B ceiling solves the fragility this project
has already documented (longer-preamble regressions, tool-count
hallucination). A model genuinely capable of that needs to be a
different size class entirely (13B+, realistically 30B+ for real
headroom) — which needs discrete-GPU-class power/cooling no wearable
form factor accommodates today. **This is a physics/market constraint,
not a parts-selection problem** — no HAT swap fixes it.

### The decision: hybrid, not pure streaming, not a bigger Core

Three options were on the table; two were rejected explicitly:

- **Rejected — make Core itself bigger/more capable.** Fights the
  wearable design goal (light, low-power, always-available) for a
  reasoning ceiling it structurally can't reach anyway. Keep Core's
  hardware plan exactly as `HARDWARE.md` already specifies.
- **Rejected — pure streaming (Core becomes a thin client to Home,
  reasoning happens remotely by default).** Would quietly discard this
  project's foundational offline-first principle. A *survival*
  companion that requires a live connection to Home to function
  defeats the actual point of the wearable — the scenarios this
  project cares about most (no signal, off-grid, Home unreachable) are
  exactly when a thin client stops working.
- **Chosen — hybrid.** Core stays fully offline-capable for everything
  in the "reliable" list above, unconditionally, forever — Home is
  never required. When Home *is* reachable (docked, or eventually over
  the user's own network — never the open internet, matching this
  project's existing privacy-first stance of no data leaving the
  user's own devices), the Assistant gets an explicit, optional
  "consult deeper reasoning" hand-off for requests that genuinely need
  it, and relays the answer back into the same conversation. This was
  already sketched conceptually for the Expert Council concept earlier
  in this document — this decision formalizes it as the general
  Core→Home reasoning hand-off mechanism, not a debate-specific
  feature.

### New: streaming/remote access as its own access mode, not a Core fallback

Separately from the hand-off above — a browser/app interface to reach
MIA's **full Home-side capability** directly, for the times the user
isn't wearing Core at all (at a desk, on a phone at home). This is the
first concrete piece of the "Multi-platform, one companion" companion-
philosophy principle to get a real design decision: it's explicitly
**additive to Core, not a replacement for it or a dependency of it**.
Neither Core's offline operation nor this streaming mode blocks the
other from being built independently.

### What this leaves unbuilt (flagged, not started)

- The Core→Home hand-off mechanism itself (a new Assistant action type,
  network-reachability detection, response relay back into the active
  conversation).
- The browser/app streaming interface to Home — needs the same "real
  API boundary" rearchitecture flagged in the critical-evaluation
  section above (`gui/` can no longer be the only client), now with a
  concrete reason to build it rather than a hypothetical one.
- Project 2's software stack entirely — the hardware is being built
  (see `HARDWARE.md`); nothing runs on it yet.

### 2026-07-15 sharpening: Core drops its GUI entirely — voice-first, no screen

A direct follow-on decision, made explicit while scoping a visual
redesign: **Home is the only place the rich visual companion interface
lives. Core becomes voice-first with no traditional dashboard UI at
all** — its only visual output is the small e-paper status display on
the Receiver (`HARDWARE.md`'s Modular Backpack section), not a
touchscreen kiosk. This is a real, significant reframing of what
"MIA Core" has meant for most of this project's history so far —
worth being explicit about the practical consequence rather than
letting it stay implicit:

**Everything built in `gui/` and every module's `get_widget()` so far
should now be understood as "the Home app," not "the Core app."** The
Pi5 kiosk-mode framing that's driven `docs/HARDWARE.md`'s "Boot &
kiosk" section and this whole project's early milestones (v0.1–v0.2)
was written before this split existed — none of that work is wasted,
it just has a new home (literally), and Home's hardware (a real
desktop-class machine, `HARDWARE.md`'s Project 2 section) is a
strictly better fit for a PySide6 desktop app than a Pi5 ever was
anyway.

**Why this pivot is architecturally clean rather than a rewrite**: this
project's own layering discipline (`docs/ARCHITECTURE.md`) already
enforces `core/` never importing `gui/` or `modules/` — every manager,
the Assistant, voice, and all persisted data already work with zero GUI
dependency. Core's new software shape is *just* the `core/` layer plus
a new lightweight voice-loop entry point (push-to-talk → transcribe →
Assistant → speak), no `gui/`/`modules/` construction at all. Home runs
the existing full `gui/` + `modules/` stack over the same `core/`
services, unchanged. The strict layering that's been maintained since
v0.1 — sometimes at the cost of extra ceremony, per `ARCHITECTURE.md`'s
own stated tradeoff — is exactly what makes this split cheap now
instead of a painful retrofit.

**Not built yet, and genuinely substantial when it is**: the actual
headless/voice-first Core runtime itself — a new entry point separate
from `main.py` (which boots the full GUI app), a voice-loop controller
running without Qt's event loop driving it, and real hardware
integration for the Receiver's push-to-talk button/e-paper display/
recording LED/vibration motor outside of any GUI framework. Flagged
here as real, unstarted work — same "don't build blind, scope it
properly first" discipline as everything else in this document.

## Home's visual identity — a sci-fi companion interface (2026-07-15)

Now that Home is confirmed as the only place MIA's visual interface
lives (previous section), the user gave a detailed, real design brief
for what that interface should feel like — worth preserving close to
the original framing since it's a genuine creative direction, not a
vague mood board:

**The core standard: this should feel like a living companion system,
not a traditional desktop application.** Named inspirations: VR spatial
interfaces, futuristic game HUDs, holographic assistant systems, sci-fi
operating systems, RPG-style menus/quest systems — "a spaceship command
interface... a VR home environment... a futuristic RPG menu... a
personal AI companion from a sci-fi game."

**Boot sequence**: not a static splash screen — MIA should feel like
she's *waking up*. System initializing, modules coming online, sensors
activating, personality loading — powering on a futuristic device or
entering a game world, not watching a progress bar. `gui/boot_core_widget.py`'s
`PulsingCoreWidget` (a cheap, timer-driven breathing glow-orb, already
built for milestone 2.9's boot animation) is the right *technique* to
build this out from — layered translucent rings for bloom without a
real blur pass, already proven cheap enough to run continuously — not
a starting-from-scratch effort.

**Main interface**: floating panels instead of flat windows; UI
elements that feel like they exist in 3D space; smooth transitions and
subtle animation; layered depth, parallax, glowing elements,
holographic-style panels; modules as interactive objects to select and
open, not menu items; the dashboard as a command center, not an app
screen.

**Presence, not just menus** — the specific thing that makes sci-fi
interfaces feel alive, in the user's own words: *"MIA should have an
avatar/core presence that reacts during interactions. When listening,
thinking, loading modules, or completing tasks, the visual system
should communicate her state through motion, lighting, and animation."*
This is a real, distinct design requirement from the boot sequence
above — it needs to persist across the whole app, not just play once at
launch. `gui/character_panel.py` already has the right integration
point (`_apply_reaction()`, currently swapping a static emoji + text
line on module-open/notification/idle events) but the wrong visual
language for this ask — the fix is replacing the static icon with a
state-driven descendant of `PulsingCoreWidget` (distinct color/pulse-
rate/motion per state: idle, listening, thinking, module-loading,
task-complete, notification) rather than inventing a new reaction
mechanism from scratch. This presence widget is genuinely reusable
infrastructure — the boot sequence and any future floating-panel work
are both natural *consumers* of it, not separate animation systems.

**Practical constraints the user gave alongside the ambition** (written
before the Core-drops-its-GUI decision above, so read "must run on
Pi 5" as historical context for *why* these constraints exist, not as
still applying to Home specifically — Home has real GPU-class hardware,
per `HARDWARE.md`'s Project 2 section, and doesn't need the same
restraint Core would have): smooth performance, optimized animations,
avoid heavy 3D rendering unless it earns its cost, prioritize
responsiveness over spectacle. Worth keeping as *taste*, not just a
hardware limit — restraint tends to age better than maximalism even
when the hardware could technically support more.

**Not scoped into concrete milestones yet** — this is the design brief;
`docs/ROADMAP.md` carries whatever gets built first. The presence
widget is the natural first slice (foundational, reusable, directly
requested, builds on existing code) — see its entry there for what
actually shipped versus what's still just this brief.

## MIA Home's expanded scope: the Jarvis workshop/office vision (2026-07-16)

**Naming resolution, since this had genuinely drifted:** "MIA Home" and
"MIA Core" had been getting mixed together across separate planning
conversations (the user's own framing) — some of that planning assumed
a brand-new, separate project, when in fact the "Core/Home split"
section above already settled this. **MIA Home is not a new project —
it *is* this repo's existing `gui/` + `modules/` application** (already
established above as "the Home app"), continuing to grow, eventually
running on Project 2's hardware (`HARDWARE.md`'s Ryzen 9800X3D + Radeon
7900 XTX Home Cloud node) instead of a dev laptop. MIA Core stays the
separate, not-yet-built, voice-only Pi5+HAT runtime. Everything below
is new *scope for Home*, not a fifth project.

This scope was synthesized from a consolidated handoff doc
(`MIA_HOME_CLAUDE_CODE_HANDOFF.md`, brought in 2026-07-16) covering
three separate claude.ai planning conversations — dashboard
architecture, a crypto trading agent, and real estate portfolio
tracking — none of which had been reconciled against this repo before.
**Confirmed via direct audit: none of it exists in this repo yet** — no
`mia_module_contract.py`, no `mia_home_schema.sql`, no trading-agent
code, no real-estate ingestion, nothing Kraken/Robinhood/Fidelity-
related anywhere in `core/`/`modules/`/`gui/`. This section exists so
that fact-finding doesn't need to happen again next session.

### Two foundational pieces referenced but not yet built here

- **`mia_module_contract.py`** — **resolved and built 2026-07-16, see
  `core/workshop_machine.py`.** The proposed `MIAModule` interface
  (`get_status()`/`send_job()`/`pause()`/`stop()`, plus `StatusReport`/
  `JobHandle`/`ModuleError`) is a *sibling* concept to this repo's own
  `ModuleBase`, not a specialization or replacement — renamed to
  `WorkshopMachine`/`MachineStatusReport`/`MachineJobHandle`/
  `WorkshopMachineError` specifically to remove the naming collision.
  `ModuleBase` answers "what discoverable app screens exist"; a
  workshop machine answers "what physical fabrication device can I send
  a job to and poll status on" — structurally much closer to
  `core/calculator_engine.py`'s `CalculatorPlugin` (many pluggable
  things, registered by id, one shared control surface) than to
  `ModuleBase`, so it's modeled directly on that precedent (an `ABC` +
  a `WorkshopMachineRegistry`) rather than invented from scratch. A
  `LaserEngraverMachine` stub (registered by default, `AppContext
  .workshop_machines`) demonstrates the pattern end-to-end without
  pretending to control real hardware. **No GUI wired yet** —
  `modules/workshop/module.py`'s own docstring already flagged "3D
  printer/CNC/laser... waits for that hardware/tooling to exist," and
  this core-level scaffolding is exactly what that was waiting on, not
  a reason to build the control screen blind.
- **`mia_home_schema.sql`** — a proposed shared data layer (`materials`,
  `material_consumption`, `cost_rates`, `labor_rate`, `jobs`, `products`,
  `product_listings`, `revenue`, `expenses`, a `materials_needing_restock`
  view) meant to be the single source of truth every fab module, a
  future web store, and an eventual request-to-fulfillment engine read/
  write against. **Resolved 2026-07-16: adapted to this project's
  persisted-JSON-manager convention, not adopted as SQLite** — three
  real options were weighed (SQLite as-is; JSON, matching every other
  manager; a hybrid scoping SQL to just this join-heavy domain); the
  user picked JSON for consistency with the 40+ managers that already
  exist, none of which have ever needed a database despite plenty of
  their own cross-references (Missions→Trips, Journal→Trips, etc., all
  resolved by ID in Python already). **Scoped down to just the
  foundational piece first** — `core/material_manager.py` (`Material`
  dataclass + `MaterialManager`, same exact shape as
  `core/component_manager.py`) covers only the `materials` table plus
  `materials_needing_restock()` as a plain Python function (same
  "compute on demand" precedent as `core/memory_manager.py`, replacing
  the proposed SQL view). Deliberately a third separate inventory-style
  manager, not a reuse of the general Inventory tool or the electronics
  Component DB — same "mixing unrelated domains serves neither well"
  reasoning `component_manager.py`'s own docstring already gives.
  **`jobs` built next, 2026-07-16 — see `core/job_manager.py`.**
  `material_consumption` nests as a plain list on each `Job` rather than
  being a fourth separate manager — same "a record owns a list of its
  own sub-items" shape as `Mission.objectives`/Trip's gear list.
  `cost_rates`/`labor_rate` resolved as predicted: a single
  `workshop.labor_rate_per_hour` config key (defaults to `0.0` — an
  unset rate shouldn't silently inflate every job's cost with a made-up
  number), not their own managers. `job_material_cost()`/
  `job_labor_cost()`/`job_total_cost()` are plain functions over
  already-loaded `Job`/`Material` records, same "compute on demand"
  precedent as `materials_needing_restock()` — a job's cost is always
  read live against current material prices/labor rate, never a
  snapshot that could drift. `JobManager.consume_material()` is the
  one real integration point — it reaches into
  `core/material_manager.py` to actually deduct the consumed quantity
  from `quantity_on_hand`, clamped at zero rather than going negative
  (same stance `MaterialManager.update_material()` already takes) —
  this is what makes Materials + Jobs a genuinely connected system
  rather than two independent lists.
  **`products` built next, 2026-07-16 — see `core/product_manager.py`.**
  `product_listings` nests as a plain list on each `Product`, same
  reasoning as `material_consumption` nesting on `Job` — a listing
  without a product doesn't mean anything. `JobManager.produce_product()`
  is `consume_material()`'s other half — a job now genuinely credits a
  product's `quantity_in_stock` too, closing the full loop: a job
  consumes raw materials and produces finished goods, both real
  inventory movements across all three managers.
  **`revenue`/`expenses` built next, 2026-07-16 — see
  `core/ledger_manager.py`. This completes the entire originally
  proposed `mia_home_schema.sql`, fully adapted to JSON.** Named
  `ledger_manager`, deliberately not `finance_manager` —
  `core/finance_manager.py` already exists and is a different concept
  entirely (watched-folder ingestion of *externally*-generated Kraken/
  real-estate snapshots; this is MIA Home's own bookkeeping for its own
  workshop sales). Revenue/expenses are two peer lists in one manager,
  not a parent/child nesting the way `material_consumption`/
  `product_listings` are. `LedgerManager.record_sale()` is this slice's
  integration point, same shape as `consume_material()`/
  `produce_product()` — records the revenue entry *and* deducts the
  sold quantity from the product's `quantity_in_stock`, so a sale is a
  real inventory movement too, not just a dollar figure sitting next to
  an unrelated stock count. `net_profit()`/`total_revenue()`/
  `total_expenses()` are computed on demand, same "never a snapshot
  that could drift" precedent as every other cost/reporting function
  in this pipeline.

### Three financial widget sources, meant to converge into one Net Worth view

The most fragmented piece across the source conversations — flagged
explicitly so it isn't rebuilt three separate times:

- **Brokerage (Fidelity + Robinhood)** — not built. Likely a read-only
  holdings view (most retail brokers don't expose full trading APIs).
  Robinhood has an official Trading MCP
  (`https://agent.robinhood.com/mcp/trading`, a custom connector) that
  may also serve read-only portfolio data, not just execution — worth
  checking before assuming a scrape/manual-export path is needed.
  Fidelity's actual data-access options are still unconfirmed.
- **Kraken trading agent (crypto)** — the most substantial of the three,
  already built as a **separate, live-executing** Python project (not
  part of this repo): a paper-trading engine (synthetic OHLCV, MA-
  crossover signal scoring, a 3-gate filter — trend MA, ADX chop,
  volume confirmation), an ATR-adaptive risk manager with trailing
  stops, a ticker screener/ranker with a correlation guard, a
  filesystem-flag kill switch, idempotent order submission with
  reconciliation, a hard-enforced 40% cash / 30% equities / 30% crypto
  allocation rule, a 5-entries/day budget (exits exempt, reserve slots
  tighten signal strength as budget depletes), and a Kraken REST broker
  using HMAC-SHA512 signing. **Explicit gaps, not yet done**: no real
  backtest against historical data, no state persistence across process
  restarts, live broker wiring into the main execution loop is
  incomplete, a market-hours classifier exists but isn't wired into the
  live loop, and it isn't yet running 24/7 or connected to Home — the
  goal is the Ubuntu/Project-2 desktop, once migrated. **A dashboard
  export module already exists** on that side, producing the JSON shape
  below.
- **Real Estate portfolio** — built as a separate, sandboxed browser
  React dashboard (not part of this repo): per-property income/expense
  tracking, amortization-based payoff projections with extra-payment
  support, cap rate/cash-on-cash return/blended DTI, a CSV bank-
  statement import wizard (flexible column mapping, keyword auto-
  categorization), a statement-balance override (real imported balance
  over a computed estimate when available), and actuals-vs-estimate
  comparison per property. **A JSON export function already exists**
  there too, matching the same shape, plus manual placeholder fields for
  brokerage/crypto totals to approximate a combined net worth figure in
  the interim. No live bank API (the sandboxed tool can't do it) —
  export is manual/user-downloaded.

**Shared JSON export shape** (both the Kraken agent and the real estate
dashboard already produce this, so one parser handles either source):

```json
{
  "source": "real_estate_portfolio",
  "generated_at": "2026-07-16T14:32:00.000Z",
  "summary": {
    "total_invested": 480000, "total_value": 540000,
    "total_equity": 210000, "total_loan_balance": 330000,
    "gain_loss": 60000, "gain_loss_pct": 12.5,
    "monthly_cash_flow": 875.50, "blended_dti_pct": 31.4
  },
  "external_assets": {
    "brokerage_value": 42000, "crypto_value": 8500, "as_of": "2026-07-15"
  },
  "combined_net_worth": 260500,
  "allocation": [
    { "label": "123 Maple St Duplex", "value": 130000, "pct": 61.9 },
    { "label": "Crypto (Kraken)", "value": 8500, "pct": null }
  ],
  "properties": [ { "name": "123 Maple St Duplex", "current_value": 300000,
    "loan_balance": 170000, "equity": 130000, "monthly_cash_flow": 425.00,
    "cap_rate_pct": 6.2, "payoff_date": "2051-03-01",
    "loan_balance_source": "statement" } ]
}
```
`source` differs per origin; both share the `summary`/`allocation` shape.

**Recommended widget split** (from the source planning, still just a
recommendation, not built): three separate small widgets — Brokerage,
Kraken Agent, Real Estate — feeding one combined Net Worth rollup,
*not* one blob, since Kraken is a live-acting agent and the other two
are read-only/manually-updated; conflating them risks hiding which one
actually trades with real money.

**Open decision, still unresolved**: where Home reads these exported
snapshot files from — a watched folder vs. manual drag-and-drop upload
vs. something else. Deliberately left undecided pending an actual
architecture call in this codebase, not guessed at here.

### Immediate follow-up (tracked as real work, not vision-only)

1. ~~Decide the snapshot ingestion mechanism~~ — **done 2026-07-16**:
   watched folder, `core/finance_manager.py`.
2. ~~Build the real estate + Kraken ingestion widgets~~ — **done
   2026-07-16**, `gui/home_dashboard.py`'s Real Estate/Kraken Agent/Net
   Worth cards.
3. ~~Confirm what Fidelity actually exposes before committing to a
   brokerage widget approach~~ — **done 2026-09-09**: Fidelity IS
   supported via Plaid's Investments product, but on Plaid's free/
   Pay-as-you-go tier it needs a manual support-ticket request for
   Investments access first. Built as `core/plaid_manager.py`'s
   holdings sync + `modules/budget/module.py`'s Holdings list, see
   `docs/ROADMAP.md`.
4. ~~Decide how `mia_module_contract.py`'s workshop-hardware `MIAModule`
   concept relates to this repo's existing `ModuleBase`~~ — **done
   2026-07-16**: a sibling concept, not a specialization — see
   `core/workshop_machine.py`.
5. ~~Decide whether `mia_home_schema.sql` (a real SQL layer) gets
   adopted as-is, adapted to this project's existing persisted-JSON-
   manager convention, or something in between~~ — **done 2026-07-16**:
   adapted to JSON (`core/material_manager.py` + the rest of the
   production pipeline), see `docs/ROADMAP.md`.

## MIA as a Personal "User OS" — AR/XR as a future interface target (2026-09-11)

Extends, rather than replaces, the "Multi-platform architecture +
browser/XR support" concept already resolved above (2026-07-15: Core
stays offline-capable, Home gets a deep-reasoning hand-off plus a
streaming access mode). This section names the destination more
concretely: MIA eventually becomes a persistent personal capability
layer — a "User OS" — that the user can reach from anywhere, with an
AR/XR HUD (loosely inspired by *Free Guy*'s overlay feel and *My
Vampire System*'s "Inspect" ability, neither literally copied) as one
future interface among several, never the only one.

**Concept mockup (2026-09-12)**: `docs/vision_assets/user_os_concept.png`
— a mood-board illustration the user put together of what this could
eventually look like (AR HUD overlay, a desktop dashboard, mobile app,
Skills/Progression screen, and a "System Architecture" diagram showing
Desktop/Mobile/Voice/AR-XR/Displays as equal interfaces over one
"M.I.A. Core"). Reference material for the destination, same as this
whole section — not a spec, and none of it is being built from
directly; concrete work still gets scoped and planned piece by piece
like everything else in this document.

**The architectural constraint this section exists to state, explicitly
not a build request**: the intelligence/data layer this session's
"Hero's Path" work has been building all along — Skills, Missions,
Pathways, Projects, Intent, and now Discovery's proposal loop
(`core/skill_manager.py`, `core/mission_manager.py`,
`core/pathway_manager.py`, `core/project_manager.py`,
`core/intent_manager.py`, `core/discovery_manager.py`, all `docs/
ROADMAP.md` 2026-09-11) — must stay interface-agnostic. None of it may
assume the desktop GUI is its only or final consumer:

```
MIA Core / User Model
    -> Context + Knowledge + Skills + Projects + Activities + Insights + Recommendations
    -> Interfaces: Desktop, Mobile, Voice, Wearable, AR/XR HUD, eventually other devices/robots
```

This is already largely true by construction, not by new design effort:
every manager built this session takes an `AppContext` and returns
plain dataclasses — nothing in `core/` imports `gui/` or `PySide6`
(the existing layering rule, `CLAUDE.md`), and Core's own headless
voice-loop entry point (`core/core_runtime.py`) already proves the same
manager stack runs with zero GUI at all. A future AR/XR HUD is, in
architectural terms, just another thin client alongside `gui/` and
`core/core_runtime.py`'s voice loop — not a rewrite of anything below
that line. The discipline going forward is negative, not additive: keep
resisting the temptation to let a new manager reach into `gui/` for
convenience, the same discipline already enforced everywhere else in
this codebase.

### "Inspect" — a future query capability, not started

The user wants an eventual `"Inspect me"` / `"Inspect [object]"`
capability: a structured self-report (Knowledge / Capabilities / Active
/ Potential, mapped directly onto Skills + demonstrated capabilities +
current Intent/Projects/Missions + Discovery's "what's next" reasoning)
and, later, a contextual version (AR glasses looking at a real object —
what it is, what project/mission it belongs to, safety info, relevant
skills, next actions). This is explicitly **not** scoped for
implementation now — it depends on capability-status tracking
(Locked/Learning/Practiced/Demonstrated, itself already flagged as
deferred in `docs/ROADMAP.md`'s Mission Pathways/Discovery entries) and,
for the contextual/object-recognition version, camera hardware and
on-device classification this document already flags as the single
biggest open hardware question (see the "Camera + on-device species/
plant identification" critical-evaluation bullet above — the identical
capability, different subject). Recorded here so the eventual
`"Inspect"` command has an obvious home once those prerequisites exist,
not designed further.

### Classroom as the future knowledge/education layer

The user wants an existing "Classroom module" (K-12 homeschooling +
trades education) to become the knowledge layer of this loop —
recognizing "I want to accomplish X but lack knowledge Y" and connecting
Missions/Pathways/Discovery proposals to real lessons, tutorials,
reference material, and practice exercises.

**Confirmed via direct search, not assumed: no Classroom module existed
anywhere in this repository** — zero matches for "classroom" across
`core/`, `modules/`, or any doc in this repo. Same "confirm before
building on top of it" discipline as the MIA Home handoff-doc audit
above. **Resolved directly with the user (2026-09-11): it was never
actually built** — genuinely new scope, not a separate project to bring
in.

**v1 shipped 2026-09-11, same day** — `core/classroom_manager.py` +
`modules/classroom/module.py`: Subjects → Courses → Lessons, marking
lessons complete, derived completion rollups. Scoped directly with the
user first: for the user's own self-education (not a homeschooling-
the-kids tracker), and deliberately just the content/lesson structure
— **no Skills/Missions/Discovery connection yet**. The loop below is
still the destination, not built.

The envisioned full loop, for when Classroom is actually connected to
the rest of the system (capability status tiers — Locked/Learning/
Practiced/Demonstrated — already shipped separately, same day, see
`docs/ROADMAP.md`'s dated entry):

```
Intent (what do I ultimately want?)
  -> Path/Skill Tree (what capabilities do I need?)
  -> Classroom/Knowledge (what do I need to learn?)
  -> Mission (what should I actually do?)
  -> Activity (what did I actually do?)
  -> Assessment/Evidence (can I demonstrate it?)
  -> Skill/Capability (what have I become capable of?)
  -> Insight (what did MIA notice about my development?)
  -> Recommendation (what's next?)
  -> New Mission (repeat)
```

This is a real extension of the loop `docs/ROADMAP.md`'s Discovery entry
already implements a first slice of (state -> proposal -> validation ->
accept -> completion -> new state -> next proposal) — Classroom would
sit between "Path/Skill Tree" and "Mission" as a new knowledge-gap-
detection step, not a parallel system. Not designed further here; same
"prove the smaller loop first" discipline as every other pass this
session — Classroom's own content model should get real use before
wiring it into Missions/Discovery.

## Master vision & product philosophy re-statement (2026-09-14)

The user handed off a full 25-section "Master Vision & Product
Philosophy" document. Most of it restates or sharpens ground this file
already covers in detail (AR/XR HUD and "Inspect" → the "User OS"
section above; workshop/maker/greenhouse/aquaponics → the "Jarvis
workshop/office vision" section above; the four-project structure,
offline-first, companion philosophy → the Mission/Companion sections
above). Recorded in full in the `project_mia_master_vision` memory.
What's genuinely new or newly crystallized enough to record here:

**The unifying mission statement, stated more sharply than before**:
*"MIA should help turn real life into an interactive, measurable,
intelligent world."* Not artificial tasks invented to gamify
productivity — MIA recognizes what the user is *already* doing (mowing,
cooking, building, hiking, saving money, growing food) and turns it
into tracked, meaningful progression. This is the same principle that
already governed every real system built this session (Rewards derives
stats live from real Maintenance/Workout/Kitchen/Project data rather
than a separate fabricated point system) — worth stating as the
explicit test for every future feature, not just an emergent pattern.

**Multi-user "living world" as an explicit top-level pillar, not an
afterthought.** *"Each person is a player. The household is a shared
world."* This is a real, separate design document now
(`project_mia_multiuser_vision`) with its own first real slice already
shipped (Recipes as shared object + personal stats, 2026-09-14, see
`ROADMAP.md`) — this master document confirms it as core identity, not
a one-off feature.

**"Universal engine vs. individual module experiences" — a real
architectural principle worth naming, even though it's mostly already
true by construction.** The user's framing: a core engine provides
Users/Identity/Memory/Events/Objects/Missions/XP/Skills/Achievements/
Statistics/Notifications/Shared-data, and a new module (e.g. a future
Gardening module) should automatically get all of that for free rather
than reinventing it. This already holds for every module built this
session — Kitchen/Workout/Maintenance/Missions/Projects all plug into
the one shared `RewardsManager`/skill-XP/notification pipeline rather
than each inventing its own — but hadn't been named as a deliberate
rule until now. Treat it as a real constraint on future module design:
a new domain module reaching for its own bespoke XP/achievement/
notification mechanism instead of the shared ones is a smell, not a
style choice.

**Physical objects as first-class entities** (mower, truck, 3D
printer, etc. — spec sheet, maintenance schedule, usage stats,
documents/manuals/photos, costs, associated missions/achievements).
**Built.** `core.maintenance_manager.MaintenanceAsset` carries
manufacturer/model/serial/purchase-date fields and a full
documents (receipts/warranties/manuals) list, with a real UI in
`gui/add_edit_asset_dialog.py` (Add/Open/Remove, launches the OS's own
viewer) — shipped 2026-09-07, ahead of and independent from the later
2026-09-14 per-owner-attribution/reward-baseline work. The only piece
of this item still unbuilt is the AR "look at the mower, see its
stats" interface — the existing "Inspect" section above's contextual
form, unchanged, still gated on camera/on-device-classification
hardware.

**Built**: a real onboarding interview at profile creation — MIA asks
about the new user's real life, hobbies, goals, responsibilities, and
interests, and uses those answers to seed which modules/missions/
skills feel relevant to *them* specifically (directly serves "Faith
may not have the same missions I have" from the multi-user handoff).
Shipped 2026-09-14 — `gui/widgets/interview_form.py`, wired into both
first-run setup and "Add Profile"; see `ROADMAP.md`'s
"Profile-creation interview" entry.

**Explicitly long-term, not scoped**: real-world multi-player events
across households (section 25's closing line) — the user's own
framing is "eventually," secondary to the solo/home-life focus. Same
treatment as this file's existing "Realistic phased horizon" table
below — don't let it pull near-term scope toward it.

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
- **Multi-platform architecture — RESOLVED 2026-07-15, see the
  dedicated "Core/Home split" section below.** Was flagged here as the
  single largest fork in this update, genuinely undecided at the time.
  Resolved to a hybrid: Core (Pi5+HAT) stays fully offline-capable and
  is never required to reach Home to function; Home gets both a deep-
  reasoning hand-off *and* a separate browser/app streaming access mode
  for reaching MIA's full capability when not wearing Core. Pure
  "stream everything from Home" was explicitly rejected — it would
  quietly give up the offline-first survival-tool premise this whole
  project is built on.
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
  shape. **Categorization half built 2026-09-10**: a real `category`
  field + backward-compatible default landed on the existing
  `UserMemory`/`add_memory()` shape (an in-place schema addition, not a
  rewrite — every existing un-categorized record still loads, just
  defaulted to "Other"), and `core/assistant_chat.py`'s extraction
  prompt now asks the LLM to tag each fact by category at capture time.
  Deliberately did NOT rename `UserMemoryManager`/
  `core/user_memory_manager.py` despite this note's own framing and the
  bullet above calling it a "replacing" — measured the real blast
  radius (10 files reference the system, 4 are live call sites touching
  both the GUI and headless Core conversation pipelines) and judged a
  full rename as pure ceremony/risk for zero functional gain once the
  real categorization existed. **Cross-referencing memories to each
  other built 2026-09-10** — `related_memories()`, a pure keyword-
  overlap function (weighted toward shared proper nouns, e.g. two facts
  both naming the same person), surfaced as a "Related:" line in
  `gui/user_memory_dialog.py`. Deliberately does NOT add the "related
  to" concept this note originally said the data model was missing —
  no new persisted field, no linking UI, no LLM call at write time; the
  relation is computed fresh each time the dialog opens, same "don't
  build a heavier retrieval stack than a small corpus needs" reasoning
  `core/device_help_manager.py`'s own docstring already applies to doc
  retrieval. A fuller graph/tree *visualization* is real, separate UI
  scope, still unbuilt.
- **The Classroom module the "User OS" vision wants to eventually
  connect everything to shipped a v1 the same day (2026-09-11)** —
  confirmed first that it never existed (direct search + resolved with
  the user), then built the content/lesson structure only. Still not
  connected to Skills/Missions/Discovery — see the dedicated section
  above for the envisioned full loop, not yet wired.
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
| **Missions/Gamification** (2026-07-14 addition: turn hobbies/goals into objectives with tracked progress, e.g. "Master Angler" — fish for N hours, catch N fish) | Project 1, new core service (`core/mission_manager.py`), a consumer of the event bus / Activity Log rather than its own data-capture mechanism — objectives derive progress from Trip timings, a new lightweight per-trip tally primitive (catch counts, species identified, etc.), and existing manager events wherever possible instead of duplicating data capture. |
| **Memories** (2026-07-14 addition: auto-generated trip recaps — distance/pace/duration/catches/species/photos — plus location-tagged logs surfaced on the offline maps) | Project 1. Already had a placeholder as an "ambient" section in `ROADMAP.md`'s module list; promoted to a real top-level module per the user's explicit ask for a visitable "Memories section." Mostly an aggregation/read layer over Expedition/Trip/Waypoint/Journal data that already exists, plus a photo gallery over `trip_photos/` — the lowest-new-design-risk piece of this whole addition, and the first one being built. |
| **Home Dock auto-launch Dashboard** (2026-07-14 addition: docking Core to the Home desktop opens MIA automatically to a dashboard of recent events/objectives/photos/music/projects and upcoming items) | Project 1/2 boundary. Extends v0.13's Core/Home device-profile split and v0.15's Expedition-sync docking detection (Field Kit already detects a docked Core) — mostly orchestration (launch-on-dock, a new Dashboard view) rather than new architecture. |
| **Vitals/Stats logging** (2026-07-14 addition: maximalist local logging of user activity/position/pace/biometrics as hardware allows) | Project 1, new core service. Deliberately maximalist rather than category-limited, per the Mission section's reconciliation with "privacy-first" above — the only real ceiling is hardware capability (GPS, IMU, camera, mic), not self-imposed scope. |
| **Modular wearable backpack form factor** (2026-07-14 addition: camera/speaker/mic on the strap, Pi5+HAT+battery on the pack, plug-and-play expansion modules) | Physical/industrial design work, not software — tracked in `HARDWARE.md`'s new "Modular Backpack" section as its own parallel track, same way Fleet/Communications hardware choices are deferred until acquired. |
| **Memory Palace** (2026-07-15 addition: categorized, cross-referenced memory trees instead of a flat fact list) | Project 1. A schema/migration on `core/user_memory_manager.py`, not a new service — see the critical-evaluation note above on why this isn't purely additive. **Categorization half built 2026-09-10** (real `category` field, LLM-tagged at extraction time, filterable in `gui/user_memory_dialog.py`). **Cross-linking also built 2026-09-10** — `related_memories()`, a pure keyword-overlap computation (weighted toward shared proper nouns), surfaced as a "Related:" line per memory in the dialog; deliberately unpersisted (no new field, no LLM call at write time) — see the critical-evaluation note above and `docs/ROADMAP.md`'s dated entry for why that scope was chosen over a richer, persisted-link design. A fuller graph/tree visualization is still unbuilt. |
| **Intelligent UI Navigation** (2026-07-15 addition: the GUI opens the right module and fills in a form live while the conversation continues) | Project 1. A new tool category alongside the existing domain-scoped data tools (2026-07-14) — see the critical-evaluation note above; needed before voice-first can feel seamless rather than "chat, then go check the screen." |
| **Voice-first primacy** (2026-07-15 addition: voice becomes the primary interface, GUI a supporting visual) | Project 1. UX-sequencing principle applied to every future module's design, not a new service — today's push-to-talk Assistant voice path (v0.5+) is the existing foundation. |
| **Startup Dashboard Briefing** (2026-07-15 addition: an intelligent spoken/written summary at launch instead of a static dashboard) | Project 1. **Built 2026-07-15** — `core/startup_briefing.py` + `gui/home_dashboard.py`'s `_build_briefing_text()`/`_speak()`, spoken aloud via TTS automatically at every launch (human-confirmed audio output, `docs/KNOWN_ISSUES.md`), genuinely reflects live dashboard-widget state via a `_<widget_id>_highlight()` provider per widget rather than a separately-maintained list. **Extended 2026-09-10** as newer domains shipped real data — Budget/Maintenance/Kitchen/Workout/Relationships all gained a highlight provider (only Music and the native Real Estate portfolio widget remain deliberate exclusions, documented inline at their own registration point). Deliberately still template-based, not an LLM call — `core/startup_briefing.py`'s own docstring states this explicitly as a considered latency trade-off, not an oversight; revisit if a template ever stops feeling "intelligent enough." |
| **Smart Suggestions** (2026-07-15 addition: proactive, unprompted recommendations from recent activity) | **Built 2026-09-10** — `core/smart_suggestions.py`, wired into `core/application.py`'s existing daily-check timer (`_check_daily_occasions()`), same shape `core/daily_occasions.py` (2026-07-14) established, confirming that was the right precedent. All 3 of VISION's own named examples now built: workout recovery and grocery-trip-when-pantry-expires shipped first; the birthday-gift-reminder example (`build_gift_reminder_suggestion()`) closed the same day once Relationship Profiles shipped and gave it real birthday data to read. Maintenance-overdue/Missions-stale suggestions are natural, cheap future extensions of this same engine, not built in this pass. |
| **Workout Module** (2026-07-15 addition: personal-trainer-style guided sessions, PRs, progress charts) | **Built 2026-09-10** — `core/workout_manager.py` + `modules/workout/module.py` (Exercises/Templates/Log Session/History/Progress tabs). The live session's real elapsed-time stopwatches (session + independent rest timer) reuse `time.monotonic()` + a 100ms `QTimer`, the exact precedent `modules/toolbox/tools/stopwatch_tool.py` already established — closer and more direct than Expedition Mode's speed/splits tracking, which this build didn't end up needing as a model. PRs are the heaviest weight ever logged (no fabricated 1RM-estimate formula); calorie estimates are manual entry only. |
| **Kitchen Module** (2026-07-15 addition: recipes, inventory, grocery lists, nutrition, meal suggestions) | **Built 2026-09-10** — `core/kitchen_manager.py` + `modules/kitchen/module.py` (Recipes/Pantry/Grocery List/Meal Log/Suggestions tabs). Deliberately its own manager, not a reuse of `core/inventory_manager.py`'s generic Toolbox Inventory tool — same reasoning `docs/ROADMAP.md` milestone 8.3 already gave for Workshop's own component DB. Nutrition is manual entry only (no USDA lookup); units are freeform strings (no conversion system). Still overlaps in spirit with the already-planned Agriculture section (garden → kitchen supply chain is a natural future link, not built yet). |
| **Finance** (2026-07-15 addition: budgets, savings, mortgage/loan payoff, real estate, crypto, stocks, net worth, cash flow, projections) | **Corrected 2026-07-16: Home (Project 2), not Project 1.** See the dedicated "MIA Home's expanded scope" section above — this is a real, substantially-planned body of work (three financial widget sources, a live Kraken trading agent, a real estate dashboard), not a lightweight read/tracking add-on, and it's desktop-class scope, not field-device scope. |
| **Kraken Trading Agent** (2026-07-16 addition: live crypto trading agent — paper engine, ATR risk manager, screener, kill switch, Kraken REST broker) | Home (Project 2), see the expanded-scope section above. Built as a separate project; not yet connected to this repo or running 24/7. |
| **Real Estate Portfolio** (2026-07-16 addition: per-property income/expense/payoff/cap-rate tracking, CSV bank-statement import) | **Superseded 2026-09-08**: rather than the separate sandboxed React dashboard originally planned here, the user chose a native Home module instead (`modules/real_estate/module.py`, `core/real_estate_manager.py`) once per-property Maintenance-history linking mattered — properties, equity, cap rate, and rental income (linked to `core/budget_manager.py` entries) all live in Home directly now. The external React dashboard's JSON-export ingestion path (`core/finance_manager.py`, `_REAL_ESTATE_SOURCE`) still exists as a separate, still-valid widget for that other tool if it's ever used — the two are intentionally distinct ("Real Estate" vs. "My Properties" on the dashboard), not a replacement of one by the other. |
| **Workshop Hardware Module Framework** (2026-07-16 addition: a standard `MIAModule` interface — get_status/send_job/pause/stop — for fab-shop hardware like laser engravers/CNC) | Home (Project 2), see the expanded-scope section above. A real open question on how it relates to this repo's existing `ModuleBase` contract — not yet reconciled. |
| **Smart Home & Homestead** (2026-07-15 addition: lighting, cameras, doors, sensors, garden automation, solar, weather stations) | Project 1/3 boundary — merges into the already-planned Smart Home/Agriculture sections in `ROADMAP.md`'s v1.0+ bucket and Project 3 ("The Senses") above; all genuinely hardware-gated, same treatment as Fleet/Communications. |
| **Relationship Profiles** (2026-07-15 addition: people MIA knows — birthdays, gift ideas, shared memories, optional visual recognition) | Project 1, new core service, a structured extension of Memory Palace scoped to people specifically. **Text-only profiles built 2026-09-10** — `core/relationships_manager.py` (`Person`) + `modules/relationships/module.py`'s People tab; feeds `build_gift_reminder_suggestion()` directly. Visual recognition ("who am I looking at") still needs the camera hardware/on-device classification already flagged as this vision's biggest open hardware question above — not attempted. |
| **Pet Profiles** (2026-07-15 addition: names, photos, medical history, vet visits) | Project 1, same shape as Relationship Profiles, camera-independent (no recognition implied) so fully buildable now. **Built 2026-09-10 minus photos** — `core/relationships_manager.py` (`Pet`) + `modules/relationships/module.py`'s Pets tab; name/species/birthday/medical-notes/notes all buildable and built. Photos deliberately deferred — real file-import handling (configurable photo root, import dialog, orphaned-file cleanup, the exact `core.trip_manager.TripManager.add_photo()` precedent) is real added scope beyond an already-large pass. |
| **Interactive onboarding + modular tutorial system** (2026-07-15 addition: MIA teaches herself through real conversation and real tasks, always available via "teach me how X works") | Project 1. Builds on the existing Assistant conversation/personality pipeline (2026-07-14 part 5) plus `looks_like_action_request()`-style intent classification — a new "teaching mode" conversation path, not a new backend. **The teaching-mode conversation path + a one-time first-run welcome built 2026-09-10** — `looks_like_teaching_request()`/`_TEACHING_INSTRUCTION` in `core/assistant_chat.py` (reuses self-knowledge's existing grounded retrieval, just a different system-message framing), `core/onboarding.py`'s `build_first_run_welcome_message()` injected once via `gui/main_window.py`. Deliberately does NOT attempt the fuller "MIA as tutor" convergence with Intelligent UI Navigation (live on-screen demonstration, separate row below, not built) or proactive "suggest a walkthrough for never-used features" (needs a real, new per-feature usage-tracking subsystem that doesn't exist anywhere yet) — both stated plainly as deferred, not silently skipped. |
| **Self-knowledge** (2026-07-15 addition: MIA can explain any of her own modules/features/workflows conversationally) | Project 1. Directly extends `core/device_help_manager.py`'s existing end-user-docs grounding (2026-07-14 part 4) — that system already answers "how do I use X"; this generalizes its coverage and hooks it into the tutorial system above rather than replacing it. **Not a one-time "done" item — ongoing per-module upkeep.** 2026-09-10 fixed a real bug in `core/device_help_manager.py` that was silently suppressing hand-written `docs/user_help/*.md` content whenever a query named its module by name (see `docs/ROADMAP.md`'s dated entry), and backfilled real workflow docs for the 8 modules that had none at the time (Budget, Real Estate, Maintenance, Kitchen, Workout, Relationships, Music, Memories) plus a shared file for smaller system-tier ones. But coverage isn't a checklist that gets fully checked off — **every new module this project ships from here on needs its own `docs/user_help/<module_id>.md` companion, or MIA can only give a one-sentence gloss for it**; revisit this any time a module ships without one. **Hooked into the tutorial/teaching-mode conversation path 2026-09-10** — see the separate "Interactive onboarding + modular tutorial system" row below. |
| **Multi-platform architecture + browser/XR support** (2026-07-15 addition: the same assistant/memory/modules reachable from desktop, web, mobile, wearable, voice-only, and future AR/XR) | **Resolved 2026-07-15** — see the dedicated "Core/Home split" section above. Core stays fully offline-capable (Project 1); Home (Project 2) gets both a deep-reasoning hand-off and a separate browser/app streaming access mode. Neither built yet, but the architecture question itself is no longer open. |
| **Educational games** (2026-07-19 addition: games that teach real engineering concepts, homesteading, tool use, electronics, mechanics, and more) | Home (Project 2), new module(s) — desktop-class scope (real game-loop/rendering work), not a Core/field-device feature. Natural links to existing systems rather than a standalone content silo: Workshop & Electronics' component/machine data, the Missions/Gamification engine's objective-tracking primitives, and the Interactive onboarding/tutorial system above ("MIA teaches herself through real conversation and real tasks") are all plausible foundations once this is scoped for real. Not designed yet — flagged here so it isn't lost, same "don't build blind" discipline as everything else in this document. |
| **MIA as a "User OS" / AR-XR HUD interface** (2026-09-11 addition: a persistent capability layer eventually reachable through an AR/XR contextual HUD, desktop/mobile/voice/wearable all as equal clients of the same core) | See the dedicated section above. Architectural constraint, not new work: the Skills/Missions/Pathways/Projects/Intent/Discovery stack built this session already satisfies it by construction (no `core/` file imports `gui/`; `core/core_runtime.py` already proves the same manager stack runs headless). Extends, doesn't replace, the already-resolved "Multi-platform architecture + browser/XR support" row below. |
| **"Inspect" capability** (2026-09-11 addition: query MIA about your own capability state, or — later — a real-world object via AR glasses) | Project 1/2, future. Depends on capability-status tracking (Locked/Learning/Practiced/Demonstrated, itself still deferred — see `docs/ROADMAP.md`'s Discovery/Pathways entries) for the self-query form, and on the same camera/on-device-classification hardware question already flagged above for the contextual/object-recognition form. Not designed further. |
| **Classroom as the knowledge/education layer** (2026-09-11 addition: connect Missions/Pathways/Discovery to real lessons/tutorials/reference material when a capability gap is identified) | Project 1. **v1 shipped 2026-09-11** — `core/classroom_manager.py` + `modules/classroom/module.py` (Subjects → Courses → Lessons, derived completion). Confirmed first it never existed before building it. Deliberately just the content/lesson structure so far — the Skills/Missions/Discovery connection described in the dedicated section above is still unbuilt. |
| **Multi-user "living world"** (2026-09-14 addition: every profile is their own player — own level/XP/skills/missions/stats/history — inside one shared household world; shared object ≠ shared progression) | Project 1. Real, separate vision doc (`project_mia_multiuser_vision` memory). **Slice 1 shipped 2026-09-14** — Recipes as shared object + personal per-profile stats (`core/kitchen_manager.py`'s `RecipeUserStats`, see `ROADMAP.md`). Prerequisite groundwork (per-profile Mission/Workout attribution, per-vehicle Maintenance ownership) shipped the same day, ahead of the vision doc itself arriving. Remaining slices: reapply the pattern to other shared objects, shared missions/group quests, the personalized "Welcome back, Faith" dashboard — all still open. |
| **Universal engine vs. individual module experiences** (2026-09-14 addition: a shared core — Users/Memory/Events/Objects/Missions/XP/Skills/Achievements/Notifications — that every new module gets for free rather than reinventing) | Project 1. Mostly already true by construction (every module this session built plugs into the one shared `RewardsManager`/skill-XP/notification pipeline) — newly named as a deliberate constraint on future module design, not new work itself. |
| **Profile-creation interview** (2026-09-14 addition: a real onboarding conversation at profile creation — hobbies, goals, responsibilities, interests — used to seed which modules/missions/skills feel relevant to that specific person) | Project 1. **v1 shipped 2026-09-14** — `gui/widgets/interview_form.py` (real category checkboxes from `core.skill_manager.categories()` + free-text goals field), wired into `gui/setup_wizard.py`'s first-run flow and a new `gui/profile_interview_dialog.py` for later profiles; `Profile.interests`/`interview_notes` persisted (`core/profile_manager.py`). One real use so far: Skills' own category tabs sort/star the user's picked interests first. Mission/module generation from the answers is still real, separate future scope — not attempted. |

## Realistic phased horizon (coarse-grained, not a commitment)

| Horizon | Focus |
|---|---|
| **Now** | Project 1, MIA Core v0.2–v1.0 per `ROADMAP.md` — a working, reliable, offline field device |
| **Next** | Project 1 continues to v1.0+ (Fleet, Communications, Navigation, Agriculture, Medical, etc., as real hardware is acquired) |
| **Later** | Project 2 (Home Cloud) begins — this is where Expert Council, GA/PSO, and simulation become realistic to attempt, once Project 1 is stable and there's a genuine compute-offload target to build against |
| **Eventually** | Projects 3 and 4 — likely absorbed largely into Project 1's existing section structure rather than needing wholly separate builds, revisited once real hardware for each exists |

The goal is not to build every capability in this document. The goal
is a device that is genuinely useful today, architected so that none of
these future directions are foreclosed.
