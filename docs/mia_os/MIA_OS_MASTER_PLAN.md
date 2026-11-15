# MIA OS master plan

*The authoritative consolidated description of the MIA OS initiative
(Master Directive §13). Claude maintains it; Zac approves.*

*Version 0.3, 2026-11-15, after Prompt 02. Status: planning. Nothing is
built and no MIA OS decision is approved.*

## 1. What we're doing

Zac's prompt library is in [`prompts/`](prompts/), kept verbatim. It has
19 files:
- the Master Directive;
- Prompts 01–17;
- a supplemental directive for 17.

It turns MIA from an application family into a Linux-based, AI-native operating environment. Claude works through it **one prompt at a time and stops for Zac's review after each one**.

Five decisions are established by Zac (Master Directive §3) and are requirements, not options:
1. The foundation is Linux.
2. The experience is MIA-first, with a conventional desktop available.
3. The intelligence is hybrid and local-first.
4. MIA is proactive, and consequential actions need approval.
5. MIA boots by default, with a conventional desktop, a recovery environment, safe mode and a no-AI mode.

## 2. Progress

| Prompt | Subject | Status | Documents |
|---|---|---|---|
| 00 | Master Directive | received | `prompts/00_MASTER_DIRECTIVE.md` |
| first pass | 10-document plan (2026-11-13, before the library) | done; **superseded**, kept in `preliminary/` | `preliminary/*` |
| 01 | Existing system audit | done; reviewed by Zac on 2026-11-15 | listed below |
| **02** | **Feature ecosystem** | **done; waiting for Zac's review** | listed below |
| 03–17 | (see `prompts/`) | not started | |
| 18–20 | World Intelligence, Procurement, the Living System doctrine (handoffs, 2026-11-15) | proposals done; 18–20 approved (DEC-0170, 0172, 0173) | `MIA_OS_WORLD_INTELLIGENCE_PROPOSAL.md`, `MIA_OS_PROCUREMENT_PROPOSAL.md`, `MIA_OS_LIVING_SYSTEM.md` |
| 21 | Living System completeness (supplemental directive) | **scheduled after Prompt 17** (Zac, 2026-11-15), on **Fable**; it assumes 03–17 are done | `prompts/21_LIVING_SYSTEM_COMPLETENESS.md` |

## 3. Prompt 01 in brief

The full audit is [MIA_OS_EXISTING_SYSTEM_AUDIT.md](MIA_OS_EXISTING_SYSTEM_AUDIT.md).

**What exists:**
- **Structure.** A modular monolith with satellite apps, of about 300k lines:
  - the engine (`core/`, 521 files);
  - one API server (265 routes);
  - one web front end (102 pages);
  - a Qt classic view;
  - two Android apps;
  - a glasses relay;
  - the self-contained homestead subproject.
- **Tests.** 6,284 tests pass on Linux. 8 fail: 6 are test-isolation or environment problems, and 2 have causes not yet isolated.
- **Already independent of the OS:**
  - the engine (headless and on Android);
  - the action contract with undo;
  - the stores;
  - the web front end;
  - the grounding of facts in code.
- **Not yet independent of the OS:**
  - the runtime (scheduler, server host, store owner), which lives in the PC's Qt process (R-01);
  - encryption at rest, which works only on Windows (R-02).
- **Missing for an OS:**
  - capability grants (R-05);
  - Linux CI (R-07);
  - reproducible builds (R-08);
  - sandboxing (R-04);
  - device identity beyond tokens.
- **Zac's named features:**
  - built: Workout, Memory Vault, finances, businesses, homestead, the Inspect skill, Game Master and the Dungeon;
  - phase 1 only: Living Worlds;
  - not built: Smart Closet, Life Enrichment Protocol, Shared Conversation, the Convergence.
- **Could not be checked here:** the PC, the phone, the glasses, the Pi, the model's answer quality.

## 3b. Prompt 02 in brief

The full report is [MIA_OS_FEATURE_ECOSYSTEM.md](MIA_OS_FEATURE_ECOSYSTEM.md).

- **The data layer already makes MIA an ecosystem.** One identity, one set of stores, one action contract, one context, one gate.
- **Zac's answers (DEC-0159 to DEC-0164):**
  - MIA OS is for Zac, perhaps close friends later.
  - The Companion app is retired.
  - The Life Enrichment Protocol is committed; its spec is in the repo with personal details left out.
  - Smart Closet is committed, and its minimum version is being built.
  - MIA must tell who is talking.
  - "Send to MIA" works on any selection (proposed).
- **New shared services this needs:**
  - speaker identification;
  - a discretionary-money calculation;
  - an online fetch policy for background discovery;
  - free time across two people;
  - a runtime scheduler.
- **What's still missing for the ecosystem:**
  - a cross-app planner (Prompt 08);
  - one owner per fact (R-10);
  - identity for two people speaking at once.

## 4. Documents

**Central:**
- this plan;
- [Vision](MIA_OS_VISION.md);
- [Status](MIA_OS_STATUS.md);
- [Decisions](MIA_OS_DECISIONS.md);
- [Open questions](MIA_OS_OPEN_QUESTIONS.md);
- [Risk register](MIA_OS_RISK_REGISTER.md).

The Master Directive also lists REQUIREMENTS, ARCHITECTURE and later central documents. Each is created by its own prompt; none exists yet.

**Prompt 01:**
- [Existing system audit](MIA_OS_EXISTING_SYSTEM_AUDIT.md)
- [Feature inventory](MIA_OS_FEATURE_INVENTORY.md)
- [Technology stack](MIA_OS_TECHNOLOGY_STACK.md)
- [Data architecture](MIA_OS_DATA_ARCHITECTURE_AUDIT.md)
- [Security assessment](MIA_OS_EXISTING_SECURITY_ASSESSMENT.md)
- [Testing and quality](MIA_OS_TESTING_AND_QUALITY_AUDIT.md)
- [Technical debt and risks](MIA_OS_TECHNICAL_DEBT_AND_RISK_REGISTER.md)
- [Dependency and data-flow map](MIA_OS_DEPENDENCY_AND_DATA_FLOW_MAP.md)
- [Migration readiness](MIA_OS_MIGRATION_READINESS.md)

**Prompt 02:**
- [Ecosystem](MIA_OS_FEATURE_ECOSYSTEM.md)
- [Classification](MIA_OS_CAPABILITY_CLASSIFICATION.md)
- [Shared services](MIA_OS_SHARED_SERVICES_CATALOG.md)
- [Dependency map](MIA_OS_CAPABILITY_DEPENDENCY_MAP.md)
- [Navigation and discovery](MIA_OS_NAVIGATION_AND_DISCOVERY.md)
- [Workspaces](MIA_OS_WORKSPACE_AND_CONTEXT_MODEL.md)
- [More than one person](MIA_OS_MULTI_USER_REQUIREMENTS.md)
- [Device matrix](MIA_OS_DEVICE_CAPABILITY_MATRIX.md)
- [Future capabilities](MIA_OS_FUTURE_CAPABILITIES.md)
- [Priorities](MIA_OS_CAPABILITY_PRIORITY_MATRIX.md)
- [Acceptance requirements](MIA_OS_FUNCTIONAL_ACCEPTANCE_REQUIREMENTS.md)
- [Application framework requirements](MIA_OS_APPLICATION_FRAMEWORK_REQUIREMENTS.md)
- The feature inventory, updated

**Added by Zac, 2026-11-15:**
- [World Intelligence proposal](MIA_OS_WORLD_INTELLIGENCE_PROPOSAL.md) (prompt 18, 2026-11-15; DEC-0170 proposed): standing watches, one discovery store, relevance worked out in code from MIA's records, built from the pieces she has (news feeds, search, research and verify, her browser, taught skills, the gate, links). Phases W0–W8, beside the MIA OS work.
- [The Living System](MIA_OS_LIVING_SYSTEM.md) (prompt 20, the foundational doctrine, 2026-11-15; DEC-0173 proposed): the doctrine's ten characteristics and ten shared services mapped onto MIA with evidence, the gaps (grants, homeostasis, one epistemic contract, cross-domain objectives), and the invariants as tests. Once approved, every later prompt carries its invariants as acceptance criteria. No new "Living System" service.
- [Procurement proposal](MIA_OS_PROCUREMENT_PROPOSAL.md) (prompt 19, 2026-11-15; DEC-0172 proposed): World Intelligence's listings half: requirements per project, specifications compared by numbers, price observations, acquisition plans.
- [Universal Action Layer plan](MIA_OS_UNIVERSAL_ACTION_LAYER_PLAN.md), with the spec in `docs/specs/UNIVERSAL_ACTION_LAYER.md`. Its first three phases (registry and offer, the phone's selection menu, the first action set) are useful before MIA OS.
- [Model assignments](MIA_OS_MODEL_ASSIGNMENTS.md): Fable 5.2 for prompts 05, 08, 13, 14, 16 and 17 and the foundational refactors; Opus 5.5 for everyday building.

**History:** `preliminary/`, the 2026-11-13 first pass. It is input for Prompts 05, 13, 14 and 16, not authoritative.

## 5. Which document wins

1. This master plan.
2. Approved decisions in `docs/DECISIONS.md`.
3. The prompt's own reports.
4. `preliminary/`.

The code beats every document when they disagree about what exists.
