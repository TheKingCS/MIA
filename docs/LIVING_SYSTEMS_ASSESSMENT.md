# Living Systems Framework — repository assessment & recommendation (DEC-0137, proposed)

*claude, 2026-11-08, from ChatGPT's "MIA — Living Systems Framework" handoff. That document's own final instruction is
to **inspect the repo and return an assessment + capability map + plan before building anything**, and to avoid
duplicate services, unnecessary abstractions and premature microservices. This is that assessment.*

## The headline finding

**MIA already is this framework — in working code, not in theory.** ChatGPT's central insight (the intelligence that
runs a persistent fictional world is the same intelligence that runs a real life) is correct, and MIA's architecture
*already embodies it*: the same primitives — stores, an event history, a relationship graph, a goals/missions layer, a
propose-validate-commit gate, and improvement loops — already power real domains (maintenance, money, homestead,
learning), and I just built Living Worlds Phase 1 on those exact primitives. So the right move is **not** to build a
new "universal intelligence layer" on top (that's the premature abstraction the handoff itself warns against). It is to
**name the shared foundation that exists, add the one guarantee it's missing (domain isolation), and prove reuse across
two domains.**

## Capability map (the requested deliverable)

| Universal capability (§3) | Existing MIA implementation | Gap | Recommended action |
|---|---|---|---|
| A. Memory & Context | `context_assembler` (Life State / `assemble_life_state_v2`), `user_memory_manager`, `presence.py` ("what matters now"), `life_notes` | provenance/confidence is per-store, not uniform | **Reuse**; add a light confidence/source convention |
| B. Entity & State | the store pattern (`PERSONAL_STORES`/`HOUSEHOLD_STORES`: assets, properties, people, missions…), sealed at rest (DEC-0126) | no single cross-type entity registry; each store is its own type | **Reuse**; a thin registry *view* over stores, not a rewrite |
| C. Event History & Timeline | `life_events.py` (append-only, `kind:id` refs, `@on_change`), `event_bus` | — | **Reuse** — this *is* the event/timeline service |
| D. Goals & Progression | `mission_manager` (missions/objectives/XP), `pathway_manager`, `discovery_manager`, `obligations`, `intents` (the "why") | — | **Reuse/extend** — strong coverage already |
| E. Simulation & Scenario | `build_calcs` (quantities in code), real-estate depreciation/amortization, maintenance `predicted_due_date` | no general what-if/scenario engine | **New (small)** — a scenario layer over existing calculators |
| F. Planning & Decision | `workflows` (DEC-0092), procedures (DEC-0123 proposed), `actions.py` | no general task-decomposition planner | **Extend** workflows/missions before building a new planner |
| G. Learning & Adaptation | `paths.py` (DEC-0112 — desire→stages→teach→practice→verify), `night_school` | — | **Reuse** — this *is* the learning engine |
| H. Evaluation & Improvement | `loops.py` (DEC-0094/0101), `benchmarks`, `corrections`, `council`, `dev_knowledge` | — | **Reuse** — this *is* the continuous-improvement system §9 asks for |
| I. Orchestration | `application.py` daily checks, the assistant's ~175 tools, `actions.py` | cross-domain orchestration is implicit | **Extend** where a concrete multi-domain task appears |
| J. Narrative & Communication | "the model phrases, facts are assembled in code", web surfaces, voice | — | **Reuse** |
| Validation / Authorization (§8) | `actions.py` (Propose→Approve→Execute→Record→Undo), `browser_safety.classify`, `communication_gate`, `safety_floor` | — | **Reuse** — "reasoning is not authority" is already enforced in code |
| Domain isolation, real vs fictional (§7) | real stores vs the separate `living_worlds.json` (sealed); the actions gate | **no explicit environment tag** on records/XP/events | **New (the one critical gap)** |

**Verdict: ~80% reuse/extend, one small new engine (scenario), and one genuinely-critical new guarantee (domain
isolation).** There is no case here for a universal rewrite or new microservices.

## The one critical gap: real-vs-fictional isolation (§7)

This is the requirement that actually matters, and it's the one thing not yet guaranteed. Today, fictional state lives
in its own sealed store (`living_worlds.json`) and real state in its own stores — good separation by construction. But
there is **no explicit environment tag** that would stop, say, fictional XP from being counted as real skill XP, or a
simulated purchase from being read as a real expense. The handoff is right to make this non-negotiable: *shared
intelligence must not mean shared authority.*

**Recommendation (small, high-value, buildable now):** add an `environment` discriminator — `real` | `fictional` |
`simulated` — to the engine primitives: `life_events` entries, XP/reward grants, and any scenario output. Real stores
and real XP are `real`; Living Worlds events and its (future) character XP are `fictional`; scenario/what-if output is
`simulated` and can **never** be committed as `real` without going through the actions gate as a real, person-approved
action. A test asserts no `fictional`/`simulated` record ever reaches a real store or the real XP ledger. This is the
"no implicit transfer of state between domains" rule (§7, §16) made enforceable.

## What NOT to do (the handoff's own warnings, seconded)

- **No universal "intelligence layer" above the stores.** The shared foundation already exists at the right altitude
  (stores + events + links + actions + loops). Wrapping it in a new abstraction adds indirection, not capability.
- **No new microservices.** MIA is a single local-first process; the "logical components" in §10 are already modules.
- **No new goal/memory/event engines.** Generalize `mission_manager`/`life_events`/`paths`, don't duplicate them.

## Recommended plan (grounded, phased)

- **Phase A — Name the foundation + the isolation guarantee (small, do first).** Write the one-page "these existing
  modules *are* the Living Systems foundation" map (this doc is its seed), and build the `environment` tag + the
  isolation test. This makes the framework real with almost no new code and closes the critical safety gap.
- **Phase B — Prove cross-domain reuse (the acceptance test, §14).** Show the *same* primitives (entity + event +
  links + goals + validation) carrying both a Living Worlds campaign (fictional) and one real domain — **homestead or
  projects** is the right second domain, since it exercises dependencies and simulation. No new engine needed; this is
  the proof the architecture generalizes.
- **Phase C — The scenario engine (the one real new piece).** A small what-if layer over the existing calculators
  (`build_calcs`, finance, maintenance projection): take a system's current state, vary inputs, report consequences,
  all tagged `simulated` and never auto-committed. Driven by a concrete need (e.g. "what would the greenhouse
  expansion cost and depend on?", the handoff's §6 example).
- **Phase D — Planning/orchestration**, only where a concrete multi-domain task demands it; extend workflows/missions.
- Each phase: tests, docs, an ADR; existing functionality preserved.

## Relationship to the other proposals

This generalizes, it doesn't replace: **DEC-0134 (Living Worlds)** stays the flagship fictional domain and its Phase 1
stores are the first instance of the framework's entity/event pattern. **DEC-0128 (device fabric)**, **DEC-0133
(email watching)**, the homestead and project work are all real domains on the same foundation. The improvement-loop
system (DEC-0094/0101) is the §9 continuous-evaluation layer already built.

## Open questions for Zac

- Confirm the recommendation: **generalize + isolate, don't build a new framework layer.** (I strongly recommend this.)
- Second domain to prove reuse: **homestead** or **projects**?
- Is the scenario engine (Phase C) wanted soon, or only when a concrete what-if need arises?

## Related
DEC-0134 (Living Worlds), DEC-0094/0101 (improvement loops), DEC-0112 (learning paths), DEC-0092 (workflows),
DEC-0126 (encryption at rest); `core/life_events.py`, `core/links.py`, `core/actions.py`, `core/mission_manager.py`,
`core/context_assembler.py`, `core/loops.py`, `core/living_worlds.py`.
