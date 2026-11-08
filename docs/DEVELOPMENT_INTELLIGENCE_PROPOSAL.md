# Development Intelligence & The Convergence — reconciliation and first slice

*claude, 2026-11-08, from ChatGPT's two handoffs: "MIA Development Handoff: Real-World Development Intelligence"
(Homestead/Business Architect) and "MIA Architecture Handoff: The Convergence" (unified progression + living campaign).
Both docs' own section 11 asks to **inspect the existing architecture and return a proposal before building, reusing
MIA's progression/mission/memory/campaign systems and not duplicating them.** This is that proposal. It is a proposal
only — nothing here is built, and only Zac approves it.*

## Headline: this is the Living Systems Framework you already approved

These two handoffs are a more detailed, domain-specific restatement of **DEC-0137 (Living Systems Framework)**, which
Zac approved on 2026-11-08: *generalize the existing foundation, isolate real from fictional authority, don't build a
new layer.* My earlier assessment (`docs/LIVING_SYSTEMS_ASSESSMENT.md`) already did the capability-map these docs
request and found **~80% of it is working code today.** So the honest answer to "build this huge system" is: most of
it exists; the new docs name the one real missing piece more sharply than before, and add one net-new domain. The
right move is a **thin strategic coordinator over the systems MIA already has**, not the rebuild the docs could be
read to imply (and which they themselves warn against).

## What MIA already has (reuse — do not rebuild)

| Handoff component | Already in MIA | Verdict |
|---|---|---|
| Mission & Execution System | `mission_manager` (Mission/Objective/XP), `questlines` (ordered chapters, MIA as quest-giver/narrator, seasons — DEC-0028), `recurring_mission_manager`, `mission_patterns/insights`, `fitness_missions` | **Reuse** |
| Unified Progression System | `profile_manager.total_xp`, `leveling` (pure XP math), `skill_leveling`/`skill_manager`, `achievements` (derived milestones), `character_stats`, expeditions | **Reuse** |
| Project Architect | `project_manager` (Project with `intent_id`, budget, status, skill weights), `plan_library` (15 built-in plans), `build_calcs` (material/cut lists), `calculator_engine` | **Reuse/extend** |
| Campaigns + the "why" | `intent_manager` (long-running goals like "Homestead Independence" a Project `serves`), `why_graph` (reasons as a chain with live evidence), `life_events` + `links` (history + relationship graph) | **Reuse — this is the campaign spine** |
| Dungeon Master / narrative over real life | `work_dungeon` (DEC-0046: real work as a narrated dungeon, MIA as Game Master), `questlines`, `living_worlds` + `dungeon_master` (DEC-0134, fictional campaigns, Phase 2 turn loop) | **Reuse** |
| Two-Layer Reality Model (real vs narrative) | `core/environment.py` (DEC-0137): `real`/`fictional`/`simulated` with `require_real`→`DomainLeak`; every life event tagged | **Already built — this IS the two-layer model** |
| Domain Intelligence (knowledge) | Specialists (DEC-0109): construction, homesteading, business knowledge workers with sourced workbooks; `ask_specialist` | **Reuse** |
| Skill development ("read→understand→practice→demonstrate→apply") | `paths.py` (DEC-0112): desire→stages→teach→practice→verify→next, evidence-graded | **Reuse — this is the skill engine, and the staging template** |
| Homestead domain | `homestead_manager` (ingests snapshots from the separate `mia-homestead` repo), `homestead_costs`, `grow_lab`/`grow_actions`, `food_table` | **Reuse; note it's partly a sibling repo** |
| Continuous improvement / proactive guidance | `loops.py` (DEC-0094/0101), `communication_gate`, the daily checks, and the new capability reminders (DEC-0143) | **Reuse** |
| Validation ("reasoning is not authority") | `actions.py` (Propose→Approve→Execute→Record→Undo), `safety_floor`, `browser_safety` | **Reuse** |

## What is genuinely new (the real work)

Three components, in priority order. All are **advisory/`simulated`** — they recommend and score; they never commit a
real change except through the existing `actions.py` gate with the person's approval.

1. **Development Intelligence Engine** — the strategic layer the docs are really about, and the piece MIA lacks.
   Three parts:
   - **Development profile** — a resource/context assessment assembled *in code* from state MIA already holds
     (budget from finance, time/labour, skills from `skill_manager`/`paths`, tools/materials from `material_manager`/
     `inventory`, assets from the garage/properties, season from the date, objectives from `intents`). No new data the
     person must re-enter; it reads what's there and names the gaps.
   - **Prioritizer with Compounding Development Value** — scores candidate projects/opportunities by cost of entry,
     expected return/benefit, time to payoff, recurring cost, labour, risk, dependencies, scalability, opportunity
     cost — and, crucially, **what each one unlocks** (compost → soil → greenhouse). This is a transparent score over
     a dependency graph, honest that estimates are estimates (never fake-precise dollars).
   - **Logical Next Step engine** — given what's done, what's underway, what's blocked, and what resources are on
     hand, recommend the single highest-value next action, explain the reasoning, and offer to turn it into a mission
     (reusing `mission_manager`/`questlines`). This is the proactive heart, and it rides the existing gate/cadence so
     it stays a gentle recommendation, never a push.
2. **Cross-domain dependency / opportunity graph** — extend `links.py`/`why_graph` with development edges: project →
   unlocks → project, asset → enables → opportunity, skill → qualifies → project. This is what lets MIA see that a
   workshop serves both a woodworking business and the homestead, and that one greenhouse enables food *and* plant
   sales. Not a new graph engine — development edge kinds on the graph that already exists.
3. **Unified Campaign model** — a thin wrapper binding an `intent` (the why/end-state) to its active projects, its
   questline (narrative chapters), its missions, and its progression, tagged with an `environment` so a real
   Homestead Campaign and a fictional Living Worlds campaign share *shape and code* but never *authority*. `intents`
   are already most of this; the Campaign is the view that assembles them.

**Net-new domain:** Business Development Intelligence (opportunity discovery → validation → launch missions →
operations → growth) is a new domain *application* of the engine above — it reuses every primitive and adds a
business knowledge workbook (Specialists already has the slot). It is **Phase 4**, not now.

## The one thing already done for the Convergence

The Convergence doc's "Two-Layer Reality Model" (real-world truth vs. narrative presentation, fictional rewards never
confused with real ones) is **already enforced** by `core/environment.py` (DEC-0137, built). The Dungeon Master
describing a greenhouse as "a new agricultural outpost" while `build_calcs` supplies the real measurements is exactly
the split MIA runs on ("the model phrases; facts are assembled in code"). The "Voice of the Convergence" is a
narrative identity over the existing `work_dungeon`/`questlines` narrator — a tone, not a new system.

## Minimal first slice (one session, proves the architecture)

Build the **Development Intelligence Engine as a read-only advisor** over the systems that already exist, proven by a
benchmark test — nothing it outputs is committed without the person:

- `core/development_engine.py`: `development_profile(context)` (resources/gaps from existing state, all `simulated`),
  `score(candidate, profile, graph)` (transparent compounding-value scoring), `next_step(context)` (the highest-value
  recommendation + its reasoning), reusing `intents`/`projects`/`plan_library`/`paths`/`material_manager`.
- Development edge kinds added to `links.py` (`unlocks`, `enables`, `qualifies_for`), with a couple of seeded edges
  for Zac's real projects.
- A **Zero-to-Something benchmark as a test** (`tests/test_development_benchmark.py`): a fixture person with a small
  budget, few tools, and an objective; assert the engine assesses the start correctly, prioritises low-cost/
  high-unlock projects first, respects dependencies and season, and names a sensible logical next step. This is the
  docs' section-10/section-12 acceptance test, made executable.
- A `development.next_step` advisory surfaced through the existing gate (never auto-acting), and an `ask`/tool so Zac
  can say "what should I do next on the shop?" and get a grounded answer.

No new progression, mission, memory, or campaign engine is created — the slice is pure coordination + scoring + one
test.

## Phases (mapped onto the handoffs, compressed onto existing infra)

- **Phase 1 — Engine + graph + benchmark** (the first slice above). Proves prioritisation, dependencies, next-step.
- **Phase 2 — One real domain end-to-end** (DEC-0137's open choice: **projects/workshop vs. homestead** — see
  decision below). The domain gets its candidate list, dependency edges, and a Campaign view, driven by a real
  objective of Zac's.
- **Phase 3 — Campaign model + narrative** (bind intent+projects+questline+missions+progression into one Campaign;
  the Voice over `work_dungeon`/`questlines`). Connects verified real accomplishments to progression (already how XP
  works).
- **Phase 4 — Business Development Intelligence** (opportunity→validation→launch→operations→growth; new workbook).
- **Phase 5 — Additional domains** (property, manufacturing, invention, financial), each an application, not a
  rebuild.

Each phase: tests, docs, a DEC, existing functionality preserved and the parity/loop tests held.

## Guardrails (the docs' own, seconded)

- **Advisory, never authority.** The engine scores and recommends; every real change goes through `actions.py` with
  Zac's approval and an exact Undo. Estimates are labelled estimates, not predictions.
- **Safety-critical gets a professional flag.** Structural, electrical, legal, and financial decisions carry an
  explicit "qualified verification recommended" marker — MIA guides, it doesn't certify.
- **No duplication.** Reuse `mission_manager`/`life_events`/`paths`/`intents`/`links`; the loop-coverage and parity
  tests fail on a parallel system.
- **For Zac alone (DEC-0119).** The benchmark uses a generic fixture, but the lived domain is *Zac's* — his
  producer/workshop/café-aesthetic life, not a generic stranger's homestead.

## Decisions for Zac

1. **Approve this as the plan for the two handoffs** (it extends the approved DEC-0137), and **start Phase 1** (the
   read-only engine + benchmark test)? It's safe — advisory only, nothing auto-commits.
2. **Which real domain proves reuse first (DEC-0137's open question)?** ChatGPT leads with *homestead*, but MIA is for
   you (DEC-0119) and your real life is **producer/workshop/woodworking + the café-shop aesthetic** — and homestead is
   partly a separate repo (`mia-homestead`). My recommendation: **your workshop/producer projects** as the proving
   domain, with homestead intelligence folded in later as its data grows. Your call.
3. **Timing vs. current priorities.** This is a large multi-phase direction. Does it lead now, or sit behind the
   device fabric (DEC-0128, awaiting your approval) and filling MIA with your life? The first slice is small; the full
   vision is many sessions.

## Relationship to existing docs

Extends `docs/LIVING_SYSTEMS_ASSESSMENT.md` (DEC-0137) — its Phase C/D ("the scenario engine" / "planning where a
concrete need appears") *is* this Development Intelligence Engine, now named concretely. Generalises DEC-0134 (Living
Worlds) and reuses DEC-0046 (the Dungeon), DEC-0112 (paths), DEC-0118 (plans), DEC-0109 (specialists),
DEC-0137 (environment), DEC-0143 (proactive gentle guidance). Does not replace any of them.
