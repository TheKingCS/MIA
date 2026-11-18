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
| **03** | **Application framework** | **done; reviewed by Zac 2026-11-15 (DEC-0175 to 0177; prompt 22 follows)** | `MIA_OS_APPLICATION_FRAMEWORK.md` and sixteen more (listed in it) |
| **04** | **Requirements and system philosophy** | **done 2026-11-15 (Opus); reviewed by Zac (Q-32 to Q-36 answered, DEC-0179 to 0182 approved) and by Fable (2026-11-16)** | `MIA_OS_SYSTEM_PHILOSOPHY.md`, `MIA_OS_SYSTEM_REQUIREMENTS.md` and fourteen more (listed in it) |
| **05** | **Core operating system architecture** | **done 2026-11-16 (Fable); waiting for Zac's review (Q-47 to Q-51; DEC-0189 to 0195 proposed; six proofs of concept described, none run)** | `MIA_OS_CORE_ARCHITECTURE.md` and fourteen more (listed below) |
| **06** | **Hardware and platform** | **done 2026-11-17 (Opus); waiting for Zac's review (Q-63 to Q-67; DEC-0201 to 0205 proposed)** | `MIA_OS_HARDWARE_AND_PLATFORM_STRATEGY.md` and twenty more (listed in it) |
| **07** | **Intelligence infrastructure** | **done 2026-11-17 (Opus); reviewed by Zac the same day (Q-68 to Q-72 yes; DEC-0206 to 0212 approved)** | `MIA_OS_INTELLIGENCE_ARCHITECTURE.md` and twenty more (listed in it) |
| **08** | **Autonomy, agents and execution** | **done 2026-11-17 (Opus); reviewed by Zac the same day (Approve Once / From Now On; Q-74 yes; no quiet hours)** | `MIA_OS_AUTONOMY_ARCHITECTURE.md` and twenty-three more (listed in it) |
| **09** | **Self-awareness, inspection and self-development** | **done 2026-11-17 (Opus); reviewed by Zac the same day (Q-76 to Q-78 yes; DEC-0222 and 0225 approved)** | `MIA_OS_SELF_AWARENESS_ARCHITECTURE.md` and twenty-one more (listed in it) |
| **10** | **The desktop and primary interface** | **done 2026-11-17 (Opus); reviewed by Zac the same day (Q-79 to Q-81 yes; Q-82: the household display for him and his wife; DEC-0227, 0228, 0231 approved)** | `MIA_OS_DESKTOP_ARCHITECTURE.md` and twenty-four more (listed in it) |
| **11** | **Visual identity, themes and spatial interfaces** | **done 2026-11-17 (Opus); reviewed by Zac 2026-11-18 (Q-83 to Q-85 yes; Q-86: an old Android or the Pi 5; DEC-0235, 0236, 0239, 0240 approved)** | `MIA_OS_VISUAL_IDENTITY.md` and twenty-four more (listed in it) |
| **12** | **One MIA across many devices** | **done 2026-11-18 (Opus); reviewed by Zac 2026-11-18 (the Pi first a TV display; Tailscale only away; the laptop a full engine; lost phones erase; DEC-0241, 0244, 0247 approved)** | `MIA_OS_DISTRIBUTED_ARCHITECTURE.md` and twenty-five more (listed in it) |
| **13** | **Security, privacy and permissions** | **done 2026-11-18 (Opus); reviewed by Zac 2026-11-18 (sensitive never to the cloud; two-step offered; a lockdown; add-ons only ours and all local when built out; DEC-0250, 0251, 0253, 0254 approved)** | `MIA_OS_SECURITY_ARCHITECTURE.md` and twenty-nine more (listed in it) |
| **14** | **Boot, updates, recovery and reliability** | **done 2026-11-18 (Opus); reviewed by Zac 2026-11-18 (all four as recommended; DEC-0257, 0258, 0259 approved)** | `MIA_OS_BOOT_AND_STARTUP_ARCHITECTURE.md` and twenty-five more (listed in it) |
| **15** | **Development, builds and releases** | **done 2026-11-18 (Opus); waiting for Zac's review (Q-99 to Q-101; DEC-0262 to 0268 proposed)** | `MIA_OS_DEVELOPMENT_INFRASTRUCTURE.md` and twenty-five more (listed in it) |
| 16–17 | (see `prompts/`) | not started | |
| 18–20 | World Intelligence, Procurement, the Living System doctrine (handoffs, 2026-11-15) | proposals done; 18–20 approved (DEC-0170, 0172, 0173) | `MIA_OS_WORLD_INTELLIGENCE_PROPOSAL.md`, `MIA_OS_PROCUREMENT_PROPOSAL.md`, `MIA_OS_LIVING_SYSTEM.md` |
| 21 | Living System completeness (supplemental directive) | **scheduled after Prompt 17** (Zac, 2026-11-15), on **Fable**; it assumes 03–17 are done | `prompts/21_LIVING_SYSTEM_COMPLETENESS.md` |
| 22 | Runtime-owned application ecosystem (handoff) | approved (DEC-0175, DEC-0178); registry phases M1 to M5 built | `MIA_OS_APPLICATION_REGISTRY.md` |
| 23 | Universal Intelligence and intent-driven computing (handoff) | **Fable's architectural review done 2026-11-16 (DEC-0188 proposed, Q-43 to Q-46); Opus's independent review next; its steps UI-1 to UI-10 run beside the prompts** | `MIA_OS_UNIVERSAL_INTELLIGENCE_REVIEW.md` |
| 24 | Visual identity, glass, the appearance engine (handoff) | built to phase A7 (DEC-0183, 0186, 0187 approved; DEC-0184 built, still marked proposed) | `MIA_OS_APPEARANCE_ENGINE.md` |

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

## 3o. Prompt 15 in brief

The architecture is [MIA_OS_DEVELOPMENT_INFRASTRUCTURE.md](MIA_OS_DEVELOPMENT_INFRASTRUCTURE.md), with twenty-five
supporting documents. Built: one repository, about 6,800 tests before every commit, every definition documented and
checked, generated maps checked by tests, seven CI workflows, the lab and Night School, knowledge entries, a team
board. One repository, layers enforced (DEC-0262); a reproducible setup (DEC-0263); CI the gate (DEC-0264); signed
releases with SBOMs, versions by date (DEC-0265); tests in layers, AI quality gating models (DEC-0266); additive
formats or versioned migrations (DEC-0267); several models, independent review, Zac decides (DEC-0268).
REQ-DEV-010 to 030.

## 3n. Prompt 14 in brief

The architecture is [MIA_OS_BOOT_AND_STARTUP_ARCHITECTURE.md](MIA_OS_BOOT_AND_STARTUP_ARCHITECTURE.md), with
twenty-five supporting documents; it answers the reliability requirements Prompt 04 left to it. Built today: atomic
writes with the previous copy, corrupt-store recovery, nightly encrypted backups with a checked restore, the
headless runtime and its systemd units, self-repair, job backoff. The OS boots without MIA, readiness in levels
(DEC-0255); each part its own unit with limits and a watchdog (DEC-0256); whole-image updates rolled back by
themselves (DEC-0257); data in layers with snapshots (DEC-0258); backups in two places and a monthly drill
(DEC-0259); Plasma, safe mode and the previous deployment (DEC-0260); objectives (DEC-0261). REQ-REL-015 to 037.

## 3m. Prompt 13 in brief

The architecture is [MIA_OS_SECURITY_ARCHITECTURE.md](MIA_OS_SECURITY_ARCHITECTURE.md), with twenty-nine supporting
documents (the specific gaps found stay on the PC, in `audit/`, until fixed: the repository is public). Much is
built: hashed passwords with a guessing wait, two-step, sessions that end, a security log, a CSP, encrypted vaults, 56
sealed store files, a weekly dependency check, secrets kept out of logs by test. Authority only from the person
(DEC-0248); outside content is data (DEC-0249); approvals bound and used once (DEC-0250); four data classes, sensitive
never to a cloud model (DEC-0251); encryption in three layers (DEC-0252); least privilege (DEC-0253); fail closed,
safety outside MIA, an audit trail that can't be rewritten (DEC-0254). REQ-SEC-011 to 039; scenarios A to L.

## 3l. Prompt 12 in brief

The architecture is [MIA_OS_DISTRIBUTED_ARCHITECTURE.md](MIA_OS_DISTRIBUTED_ARCHITECTURE.md), with twenty-five
supporting documents. The audit found MIA already one MIA on two full engines: the phone runs the whole engine with
its own model, links once with his password, uses the PC's model when it can reach it, and syncs both ways by a
three-way merge; the glasses ride on the phone; sensors and the greenhouse node feed the PC. The PC is the hub, full
engines work alone (DEC-0241); trust by pairing, one scoped key per device (DEC-0242); sync stays the merge
(DEC-0243); HTTP and SSE over the home network or Tailscale (DEC-0244); thinking on the most capable reachable
machine (DEC-0245); controllers keep their loops and safety (DEC-0246); a lost device unlinked from anywhere
(DEC-0247). REQ-DST-001 to 033; scenarios A to J.

## 3k. Prompt 11 in brief

The identity is [MIA_OS_VISUAL_IDENTITY.md](MIA_OS_VISUAL_IDENTITY.md), with twenty-four supporting documents. The
audit found it built in its essentials: glass over depth with Aquatic the default, one cyan accent for MIA, fixed
meaning colours, five clamped surface tiers, ten themes as data, schemes and layouts, the orb's presence from real
events, the glasses' see-through composition. One design system for every device (DEC-0234); an identity that
holds without colour, transparency or motion (DEC-0235); themes as validated data (DEC-0236); the orb's fourteen
states (DEC-0237); motion in three speeds (DEC-0238); spatial as views of the same capabilities (DEC-0239); a
small local audio identity (DEC-0240). REQ-VIS-001 to 026.

## 3j. Prompt 10 in brief

The architecture is [MIA_OS_DESKTOP_ARCHITECTURE.md](MIA_OS_DESKTOP_ARCHITECTURE.md), with twenty-four supporting
documents. The audit found MIA's desktop already built as her web front end: 109 screens on one frame, 19 area
dashboards, Talk everywhere, Ctrl+K search, one change path with Approve Once or From Now On, themes apart from
behaviour. On MIA OS it becomes a full-screen window under KWin with ordinary windows beside it and Plasma one
press away (DEC-0227); one navigation model (DEC-0228); search that never executes a change (DEC-0229); context
only when shared, workspaces restored through KWin (DEC-0230); three modes of one shell (DEC-0231); one
notification pipeline (DEC-0232); apps left in the framework that suits them (DEC-0233). REQ-DSK-001 to 032.

## 3i. Prompt 09 in brief

The architecture is [MIA_OS_SELF_AWARENESS_ARCHITECTURE.md](MIA_OS_SELF_AWARENESS_ARCHITECTURE.md), with twenty-one
supporting documents. The audit found most of her self-knowledge built in pieces: capability status from the code,
the service map, the model registry, the Fix-It Log, the loops, the weekly self-audit and the lab. One capability
truth registry joins them with explicit states (DEC-0220); every self-statement carries its provenance (DEC-0221);
health and performance come from Linux and her counters (DEC-0222); quality from code checks, corrections and fixed
sets (DEC-0223); investigations end in a reproducing test (DEC-0224); self-development only through the lab, the
protected list never hers to change (DEC-0225); new capabilities through one path (DEC-0226). REQ-SLF-001 to 021.

## 3h. Prompt 08 in brief

The architecture is [MIA_OS_AUTONOMY_ARCHITECTURE.md](MIA_OS_AUTONOMY_ARCHITECTURE.md), with twenty-three supporting
documents. The audit found the execution boundary built: 482 action kinds on one contract, each tiered, with reach,
reversibility, undo, runs and the stop. The action contract is the one boundary for apps, the system and devices
(DEC-0213); one task model of goals, plans with dependencies and runs (DEC-0214); autonomy grows only by grants he
gives, offered with evidence (DEC-0215); risk computed in code sets each kind's least tier (DEC-0216); proactive help
only through the gate (DEC-0217); done means read back (DEC-0218); agents propose, the coordinator acts (DEC-0219).
REQ-AGT-001 to 034.

## 3g. Prompt 07 in brief

The architecture is [MIA_OS_INTELLIGENCE_ARCHITECTURE.md](MIA_OS_INTELLIGENCE_ARCHITECTURE.md), with twenty supporting
documents. The audit found most of it built: one provider interface (`core/llm_manager.py`), identity in one place
(`core/personality.py`), facts assembled in code, the worksheet for figures, specialists' models chosen from a bench,
a second-model review and Claude's inspection. MIA is the program, not the model (DEC-0206); one provider interface,
local first, cloud for her own work only on a per-request yes (DEC-0207); routing in code from measurements (DEC-0208);
her own council on local models of different families (DEC-0209); memory in her stores with one recall index beside
them (DEC-0210); voice local, whisper.cpp measured (DEC-0211); three kinds of learning with their own gates (DEC-0212).
REQ-INT-001 to 036 added. The everyday model is qwen2.5:14b (CLAUDE.md said llama3.2 3B).

## 3f. Prompt 06 in brief

The strategy is [MIA_OS_HARDWARE_AND_PLATFORM_STRATEGY.md](MIA_OS_HARDWARE_AND_PLATFORM_STRATEGY.md), with twenty
supporting documents. The PC was read on 2026-11-17: a Mini-ITX build (one graphics slot, two full memory slots),
Ryzen 7 9800X3D, RX 7900 XTX 24 GB, 32 GB, 1 TB. It's enough for the MVP with nothing bought (DEC-0201). It can't
grow inside, so MIA grows by adding machines on the network, the next being a model-serving node when measurements
show the need (DEC-0202). Linux owns the hardware; a capability registry reads Linux's own sources (DEC-0203); Linux
schedules and MIA places models, one job per GPU, conversation first (DEC-0204); the device family is tiered and
nothing depends on a later device (DEC-0205). REQ-HW-007 to 031 added. Still to run: PoC 1 (needs a USB stick),
PoC 3, W1.

## 3e. Prompt 05 in brief

The architecture is [MIA_OS_CORE_ARCHITECTURE.md](MIA_OS_CORE_ARCHITECTURE.md), with fourteen supporting documents.

- **Linux underneath, untouched; MIA as services and one session on top.** Nothing of the operating system depends
  on MIA: with every MIA part broken the machine still reaches a working KDE desktop.
- **The foundation** (DEC-0189, proposed): Fedora's KDE desktop delivered as an image built from this repository,
  updated whole and rolled back whole; the distribution's own kernel; Ubuntu 26.04 the fallback. Fedora 45 (3
  November 2026) packages the graphics card's AI stack and the model runner MIA uses. One measurement decides it.
- **One coordinator** (DEC-0190): the runtime is the only writer of his records; the shell, the model server, the
  helper, the capture agent, her browser, extensions and heavy jobs are separate processes that fail alone.
- **System changes** (DEC-0194): a small root helper with a fixed list of operations; after his approval in MIA,
  the operating system itself asks him to confirm, in a dialog MIA can't draw or press.
- **A conflict named:** the earlier proposal's kiosk compositor shows one application, which doesn't fit ordinary
  apps inside MIA's session; a test decides between it and KDE's own (DEC-0191, provisional).
- **Almost everything is reused.** MIA writes the image definition, about ten small adapters, the shell's host, the
  capture agent and the helper.
- **Every requirement of Prompt 04 is mapped**: 31 addressed, 10 partly, 8 waiting on a test, 146 belonging to later
  prompts with their component named, none unaddressed.
- **Questions for Zac:** Q-47 to Q-51.

## 3d. Prompt 04 in brief

The specification is [MIA_OS_SYSTEM_REQUIREMENTS.md](MIA_OS_SYSTEM_REQUIREMENTS.md) (with fifteen supporting documents,
listed in it); what MIA OS is, [MIA_OS_SYSTEM_PHILOSOPHY.md](MIA_OS_SYSTEM_PHILOSOPHY.md).

- **What it is** (DEC-0179, proposed): a personal, AI-native operating environment on a standard Linux image, one node
  of a distributed personal intelligence. Three layers, one-way: the OS, the MIA platform, her apps and surfaces.
- **194 requirements**, each with a priority, a release tier, a status checked against the code, a verification and an
  owner prompt; the traceability matrix is generated and tested. About half already exist in the code.
- **Measured on Zac's PC:** the 3B model answers in 0.3 s once loaded, the 14B in 0.9 s, the 32B in 3.4 s; MIA's engine
  starts in 0.5 to 1.7 s and assembles the day in 0.02 s. Performance targets are set from these.
- **The MVP** (DEC-0182, proposed): the signed image, her session by default, Plasma beside it, everything she does
  today, local models only, the phone and glasses as now, backups, rollback, recovery.
- **Questions for Zac:** Q-32 to Q-36. **Conflicts found:** the multi-user list against DEC-0119; Ubuntu (the hardware
  doc) against Fedora (DEC-0157), for Prompt 06 to settle by a GPU test.

## 3c. Prompt 03 in brief

The full report is [MIA_OS_APPLICATION_FRAMEWORK.md](MIA_OS_APPLICATION_FRAMEWORK.md) (with sixteen supporting
documents).

- **MIA already has an application framework, and it's capability-first:** what MIA invokes is a capability (419 tools,
  466 action kinds, the UAL's actions); an app is a bundle of surfaces over capabilities, with its stores and jobs.
- **Four gaps:** one manifest per app (its parts are in five places), declared side effects and permissions per
  capability (DEC-0156), out-of-process code for anything not MIA's own (R-04), and app status from one place.
- **Proposed:** DEC-0175 (capability-first; MIA's own apps stay in the runtime), DEC-0176 (other code runs out of
  process, sandboxed, through the capability contract), DEC-0177 (MIA in the OS image, Flatpak for GUI apps, signed
  extensions, no marketplace).
- **Questions for Zac:** Q-27 to Q-29.

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

The Master Directive also lists REQUIREMENTS, ARCHITECTURE and later central documents. Each is created by its own prompt: the requirements are Prompt 04's, the architecture Prompt 05's.

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

**Prompt 05:**
- [Core architecture](MIA_OS_CORE_ARCHITECTURE.md)
- [Linux foundation](MIA_OS_LINUX_FOUNDATION.md)
- [System services](MIA_OS_SYSTEM_SERVICE_ARCHITECTURE.md)
- [Graphical and session](MIA_OS_GRAPHICAL_AND_SESSION_ARCHITECTURE.md)
- [Storage and filesystem](MIA_OS_STORAGE_AND_FILESYSTEM_ARCHITECTURE.md)
- [IPC and communication](MIA_OS_IPC_AND_COMMUNICATION_ARCHITECTURE.md)
- [Hardware abstraction and connectivity](MIA_OS_HARDWARE_ABSTRACTION_ARCHITECTURE.md)
- [Resource management](MIA_OS_SYSTEM_RESOURCE_MANAGEMENT.md)
- [Observability](MIA_OS_SYSTEM_OBSERVABILITY_ARCHITECTURE.md)
- [Privilege boundaries](MIA_OS_SYSTEM_PRIVILEGE_BOUNDARIES.md)
- [Build versus reuse](MIA_OS_SYSTEM_BUILD_VS_REUSE.md)
- [Technology evaluation](MIA_OS_CORE_TECHNOLOGY_EVALUATION.md)
- [Diagrams](MIA_OS_CORE_ARCHITECTURE_DIAGRAMS.md)
- [Acceptance criteria and the requirement mapping](MIA_OS_CORE_ARCHITECTURE_ACCEPTANCE_CRITERIA.md)
- [Open questions and proofs of concept](MIA_OS_CORE_ARCHITECTURE_OPEN_QUESTIONS.md)

**Added by Zac, 2026-11-15:**
- [World Intelligence proposal](MIA_OS_WORLD_INTELLIGENCE_PROPOSAL.md) (prompt 18, 2026-11-15; DEC-0170 proposed): standing watches, one discovery store, relevance worked out in code from MIA's records, built from the pieces she has (news feeds, search, research and verify, her browser, taught skills, the gate, links). Phases W0–W8, beside the MIA OS work.
- [The runtime-owned application ecosystem](MIA_OS_APPLICATION_REGISTRY.md) (prompt 22, 2026-11-15; DEC-0175 and DEC-0178 approved; M1 built): one manifest per MIA-native app, an Application Registry in the runtime, MIA Forge, the migration M1–M8, and how MIA-native apps sit on the conventional Linux underneath.
- [Prompt 24, visual identity and the appearance engine](MIA_OS_APPEARANCE_ENGINE.md) (Zac, 2026-11-15; kept verbatim in `prompts/`): glass as MIA OS's identity (DEC-0183, direction approved), the appearance engine as theme, colour scheme and layout on the existing theme engine (DEC-0184, proposed), phases A1 to A7. Phase 1 (the plan) done; Q-37 to Q-39 for Zac.
- [Prompt 23, Universal Intelligence and intent-driven computing](prompts/23_UNIVERSAL_INTELLIGENCE_INTENT_DRIVEN_COMPUTING.md) (Zac, 2026-11-15): kept verbatim; Fable's architectural review first, then Opus's engineering review; nothing built from it yet.
- [The Living System](MIA_OS_LIVING_SYSTEM.md) (prompt 20, the foundational doctrine, 2026-11-15; DEC-0173 approved): the doctrine's ten characteristics and ten shared services mapped onto MIA with evidence, the gaps (grants, homeostasis, one epistemic contract, cross-domain objectives), and the invariants as tests. Once approved, every later prompt carries its invariants as acceptance criteria. No new "Living System" service.
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
