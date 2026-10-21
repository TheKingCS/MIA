# MIA Intelligence Integration — Self-Aware, Deeply Integrated Local AI

*From Zac, 2026-10-21, kept as given (lightly condensed into lists).
Claude's audit, plan and the first slice: `docs/INTELLIGENCE_AUDIT.md`.*

## Mission

Transform MIA's local Qwen model into the central intelligence layer of the MIA ecosystem. The model should understand MIA's architecture, identify which model it is running, know what features and tools are available, retrieve relevant project knowledge, interact with existing services, and coordinate actions across the entire application. This should be a persistent, maintainable architecture, not a system prompt full of hardcoded descriptions.

**Primary goal:** MIA should understand its own software environment, know what it can and cannot do, and use its existing capabilities intelligently.

**Long-term goal:** MIA should be capable of analyzing, improving, testing, and extending its own codebase, with Zac's explicit permission required before code changes or other consequential modifications.

## Phase 1 — Audit before building

Inspect the repository, architecture, specifications and runtime first. Determine: which Qwen model was actually downloaded (exact tag, size, quantization, context window, runtime); whether Ollama is the active server and how MIA sends requests; which inference settings, system prompts, history, memory and tool-calling mechanisms exist; which modules expose usable APIs, services, tools or events; how permissions, authentication, persistence, background jobs and errors work; which capabilities are implemented, partial, experimental or planned; whether repository search, file reading, terminal access, Git and automated tests are available; which features integrate immediately vs. need adapters. Read the authoritative specifications, architecture docs, collaboration instructions and current-state documents. Produce a capability map and plan before modifying code. Don't recreate existing functionality or replace working components unnecessarily.

## Phase 2 — A self-awareness system

MIA must answer questions about its own implementation from verified, current information: which model it runs; hardware and inference limits; available features; how finance, property, mission, inventory and automation interact; whether it can control a device or perform an action; which tools it can call; why a previous action failed; what's incomplete; what changed in the latest update.

**A. Runtime model registry.** Provider and backend; exact model identifier and version; parameter count and quantization; context window; system and inference configuration; hardware and resource constraints; tool-calling support and other verified capabilities; active, fallback or unavailable status; health, latency, errors and resource use. Query the actual runtime (e.g. Ollama's model metadata and runtime APIs), not a hardcoded name. Distinguish facts verified from the runtime, from configuration, and inferred or tested. Never claim a capability because a model's name suggests it.

**B. Live feature and capability registry.** Per feature: stable ID; name and description; implementation status; services, APIs and data; actions and read operations; permissions and dependencies; input and output schemas; known limitations and errors; related specs, docs and tests. Discovered through explicit registrations, service contracts and runtime inspection; a file's existence isn't proof a feature works. States such as implemented, partial, experimental, planned, unavailable, unknown. Kept in sync with code; validated by tests and health checks.

**C. Repository intelligence.** Locate and explain module responsibilities and dependencies, classes, functions and interfaces, service contracts and endpoints, data models, configuration and inference settings, feature implementations and their tests, decisions and specs, known issues and incomplete work. An incrementally refreshed index with appropriate parsing for code, docs, config and tests; file paths, symbols and references preserved; dependency and call graphs where practical. Respect ignored files, permissions, secrets, generated files and private data; never index credentials. Answers cite files and symbols.

## Phase 3 — Persistent knowledge through retrieval

No stuffing the repository into every prompt: retrieval-augmented generation, integrated with MIA's existing memory. Sources: system knowledge (specs, architecture, decisions, rules); code knowledge (source, symbols, dependencies, tests, APIs); capability knowledge (features, actions, permissions, availability); operational knowledge (recent errors, results, health, logs); user-approved memory (preferences, projects, goals, history); domain knowledge (property, finance, homestead, aquaponics, recipes, fitness…). Semantic and exact-keyword search; only relevant context; source references and timestamps; permissions and ownership respected; incremental indexing and invalidation; authoritative specs over outdated docs; current state distinguished from history and plans; uncertainty reported. The model knows how to find information rather than memorizing files.

## Phase 4 — Integrate the model with every feature

A unified capability and tool-execution layer over existing services (no duplicate business logic): property records, finances, inventory and projects, missions and XP, documents and notes, workouts and measurements, device and sensor status, permitted automations, codebase search, diagnostics, tests and proposed changes (examples, not assumptions). Each tool: stable identifier and description; typed, validated input; authorization and permission checks; defined output; structured errors and timeouts; audit logging; idempotency where needed; confirmation requirements. Tool choice by intent, capabilities and permissions; the existing API and service layer is the source of truth (no direct database or file edits that bypass rules). Multi-step orchestration: gather, plan, execute permitted operations, inspect results, report what actually happened. A missing capability is said, not pretended.

## Phase 5 — Context-aware intelligence

Shared context building from the request and conversation, approved memory, feature and tool availability, relevant records, recent action results, permission and safety constraints, specs and sources. Task-aware retrieval and context budgets (small requests stay cheap); conversation state without confusing old plans, completed actions and current facts; cross-module coordination through existing contracts (a homestead project touches inventory, purchasing, property, expenses, tasks and accounting).

## Phase 6 — More capable without premature fine-tuning

Order: verify the model and inference configuration; a strong system prompt and structured context builder; repository and spec retrieval; live model and feature registries; existing tools and services integrated; reliable tool selection, execution and result verification; evaluations; model-specific tuning only when evaluation finds a persistent problem prompting, retrieval, tool schemas or orchestration can't solve. Knowledge stays outside the weights. Any fine-tuning starts from a quality-controlled dataset evaluated on a held-out set.

## Phase 7 — Self-improvement workflow

Building on existing Git, terminal, repository and testing integrations: understand the request; inspect code, specs, dependencies and tests; determine what exists; propose a plan; identify affected files, risks, permissions and expected behavior; **obtain explicit approval before code changes**; make approved changes in an isolated branch or workspace; run tests and checks; inspect the diff; report results, failures, risks and follow-up; **wait for approval before merging, deploying** or other consequential operations. Read-only analysis can proceed without approval, subject to access restrictions. Approval to investigate isn't approval to modify; approval to edit isn't approval to merge, deploy, access credentials, install software or alter security policies. MIA never grants itself permissions, disables approvals or silently changes its safeguards. Record attempts, successful or not.

## Phase 8 — Model routing and resource awareness

Support several local or remote models when appropriate; route task classes (simple conversation, retrieval and summarization, structured extraction, multi-tool workflows, complex reasoning, code work) by measured quality, latency, memory and hardware, not parameter count. Offline when the model and data are local; remote models optional and clearly identified. No routing framework without a measurable benefit; start from the verified configuration and keep it extensible.

## Phase 9 — Evaluation and observability

A repeatable suite: identifying the active model; reporting implemented and unavailable features accurately; retrieving the right specs and files; tool selection and argument validation; integration with services; multi-step completion; permission and approval boundaries; recovery from tool failures; no fabricated actions or results; offline operation; context limits and performance on the hardware. Metrics: task success, retrieval accuracy, tool-call accuracy, latency, tokens, failure rate, resources. Regression tests from real failures; a versioned evaluation set.

## Phase 10 — Deliverables

After the audit: a map of the intelligence architecture; a verified inventory of the active model and inference configuration; a feature/capability matrix with status and tools; reusable components; a prioritized plan with dependencies and risks; a design for model awareness, capability discovery, repository retrieval and tool orchestration; an evaluation plan with acceptance criteria. Then small tested increments. **A first vertical slice:** MIA detects the active model from the runtime; retrieves its feature registry; answers a question about an existing feature using the relevant source; invokes one existing, permissioned tool; verifies the result and explains what it did; automated tests cover the whole workflow. Then expand across the remaining modules.

## Definition of done

MIA identifies its actual model and configuration; knows which capabilities are implemented, available and permitted; finds and explains relevant source; uses features through validated tools; coordinates multi-step work across domains; updates its understanding when code, configuration or features change; distinguishes facts from assumptions and never fabricates successful actions; works locally and offline where dependencies allow; assists with improving its own code under explicit approval; integrates new features without retraining.

*Principle:* audit first, reuse existing architecture, implement incrementally, verify everything. The goal is a real, queryable, permissioned understanding of MIA's own software and the ability to act through it reliably, not a model that merely sounds like it understands.
