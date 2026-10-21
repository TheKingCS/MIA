# MIA UX & Intelligence Architecture: From App Launcher to Personal System

*Chat's handoff, sent by Zac 2026-10-21, kept as given (lightly condensed
into lists). Claude's audit and plan: `docs/UX_SYSTEM_AUDIT.md`
(DEC-0044).*

## Objective

Evolve MIA from a collection of useful applications behind a futuristic interface into a unified, context-aware personal intelligence system. MIA should feel like a second, more organized consciousness that helps the user understand, plan, and manage their life, taking inspiration from the Solo Leveling System, My Vampire System, Cortana, JARVIS and EDITH. This is a behavioral and architectural goal, not merely a visual reskin. First step: audit what already exists; don't rebuild existing functionality just because it needs a better experience.

## 1. Core product philosophy

MIA is the intelligence layer; apps, modules, screens, services and tools are capabilities she coordinates. The user shouldn't need to know which module owns a capability or manually move information between modules. MIA should: keep a coherent, persistent understanding of the user's goals, projects, commitments, preferences and world state; understand requests in context; coordinate multiple capabilities for one objective; identify dependencies, blockers, deadlines, opportunities and useful next actions; turn long-term goals into projects, milestones and missions; keep continuity across conversations, sessions and devices; proactively surface useful information within notification and permission preferences; verify actions and update state from actual outcomes; explain reasoning and distinguish facts from assumptions; respect autonomy and the existing anti-nagging principles. Don't simulate consciousness or claim awareness beyond the system's real capabilities: deliver persistent context, coherent planning, reliable memory and controlled initiative.

## 2. Audit before changing anything

Document current navigation, the apps tab, home/dashboard and major journeys; core services, module boundaries, shared state, events and APIs; memory, context retrieval, model selection, tool calling and planning; missions/objectives/projects and their XP, skills and achievements; proactive notifications, scheduling, automation and permissions; cross-device sync and shared state (phone, desktop, Pi, glasses); tests and decisions to preserve. Identify duplication, disconnected modules, navigation friction and manual context transfer. An evidence-based gap analysis: implemented and working; implemented but fragmented or poorly surfaced; partial; missing; architecturally risky.

## 3. Navigation around intent

Replace the long app-centric Apps experience with a few meaningful destinations: **Presence** (a synthesized, glanceable overview of priorities, active missions, alerts, progression and the next useful action); **Conversation** (the universal entry point for questions, commands, planning, brainstorming and continuing work); **My Hero's Path** (quests, objectives, projects, milestones, skills, stats, achievements, history); **World** (finances, health, properties, homestead, inventory, assets, connected systems); **System** (settings, integrations, permissions, model configuration, diagnostics, logs, advanced controls). Conceptual destinations adapted per interface, not five fixed buttons everywhere. Keep advanced views and detailed tools reachable; most relevant information first, depth on demand.

## 4. One intelligence loop

OBSERVE → UNDERSTAND → REASON → PLAN → AUTHORIZE → EXECUTE → VERIFY → UPDATE STATE, on existing services. Observe only permitted information; understand with relevant personal context, objectives, world state, constraints and prior decisions; reason and plan (intent, dependencies, tools, uncertainties, next actions; structured plans for multi-step requests); authorize (permissions and risk; confirmation when required); execute and verify through authoritative state, never equating an attempt with success; update state (verified outcomes, mission/project state, events). No second mission system, memory database or domain-specific intelligence engine where existing infrastructure can serve.

## 5. Shared personal state and context

Retrievable, structured, consistent state: goals, preferences, routines, constraints; active projects, missions, objectives, dependencies; schedules, commitments, deadlines, recurring tasks; assets, inventory, properties, resources; progression, skills, stats, achievements, verified history; observations and patterns with timestamps, provenance, confidence and permission boundaries; pending decisions, blockers, next actions. Domain systems stay authoritative; the shared layer references and synthesizes. Context is retrievable, inspectable, permission-aware and updated on change.

## 6. Cross-feature intelligence

One objective may span modules (a greenhouse project: homestead inventory, finances, scheduling, permits, maintenance, production, progression). MIA coordinates them behind one workflow; universal mission and project objects linked to domain records, dependencies, schedules, completion events and progression; completion events update downstream systems through existing mechanisms.

## 7. Proactive assistance

Three levels: responsive; contextually proactive (insights, blockers, reminders, suggestions); authorized autonomous execution of permitted routine workflows. Respect quiet hours, limits, urgency, confidence and preferences; combine low-priority updates; prioritize what changes a decision or needs action; distinguish facts, inferences, recommendations, pending and completed actions; authorization for consequential external actions, never bypassed because the model thinks it's beneficial.

## 8. Model integration

The model receives, as appropriate: a maintained identity and operating instructions; repository-defined capabilities and tool schemas; retrieved task context; current state and constraints; permission and action policies; structured planning and tool interfaces; prior tool results and errors in the workflow. It discovers capabilities without hardcoded or outdated descriptions; no whole-repo or all-personal-data prompts. Deterministic services for calculations, authorization, progression, integrity and state transitions; the model for interpretation, reasoning, synthesis and planning.

## 9. One intelligence, multiple interfaces

MIA Core is the shared intelligence; devices are presentation layers (desktop: rich workspace and project views; phone: conversation, quick actions, notifications; Pi: local/offline; Meta Display: concise, glanceable). Reuse APIs, shared state and action handlers; no separate business logic per device. The visual identity is cyan/light blue (JARVIS/EDITH): clarity, responsiveness and hierarchy over decoration.

## 10. Acceptance criteria

An objective without locating an app; relevant context without repeating it; a multi-step objective coordinated across capabilities; changes update connected missions, projects and state without duplicate entry; home prioritizes meaningful information; detail available on request; MIA explains why and names uncertainty; proactive actions respect preferences and permissions; all interfaces share intelligence and state; functionality, integrity and tests preserved or deliberately migrated; actions verified before reported complete.

## 11. Implementation plan

After the audit: present the architecture and the main gaps; map modules to the proposed experience and reusable foundations; recommend the smallest high-impact changes; implement the new navigation and Presence on existing services; improve context retrieval, orchestration and verification; integrate proactive assistance and progression; adapt to phone, desktop, Pi and glasses; add regression tests and demonstrate complete journeys. No massive rewrite; tested increments.

*The guiding question:* does this make MIA better at understanding the user's world and helping manage it, or does it merely add another place the user has to navigate?
