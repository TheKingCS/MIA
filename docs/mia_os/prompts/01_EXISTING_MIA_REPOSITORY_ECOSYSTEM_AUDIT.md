PROMPT 01 — EXISTING MIA REPOSITORY & ECOSYSTEM AUDIT

Comprehensive Technical Discovery, Architecture Analysis, and Current-State Assessment

1. OBJECTIVE

Conduct a comprehensive engineering audit of the existing MIA project.

Your objective is to develop an accurate, evidence-based understanding of the software ecosystem that currently exists, how its components function, how they communicate, what capabilities are operational, and what technical limitations or architectural problems must be considered when evolving MIA into MIA OS.

This is a discovery and documentation assignment.

You are not being asked to redesign MIA, implement MIA OS, or begin migrating existing functionality.

You must first understand the existing system.

Approach this assignment as though you are a new senior engineering team taking responsibility for a substantial, established software platform.

Do not assume that existing documentation is completely accurate or that the original architectural intentions match the current implementation.

Inspect the actual source code and verify important claims.

The resulting audit will serve as the factual baseline for all subsequent MIA OS architecture and implementation planning.

---

2. PROJECT CONTEXT

MIA stands for Multifunctional Intelligent Assistant.

The existing project is a growing ecosystem of applications, AI services, capabilities, interfaces, integrations, and supporting infrastructure.

The long-term objective is to transform MIA into a Linux-based, AI-native operating environment.

The established MIA OS requirements are:

- Linux-based foundation.
- MIA-first computing experience.
- Conventional desktop access.
- Hybrid AI infrastructure, local-first with cloud capabilities when useful.
- Proactive intelligence with approval for consequential actions.
- Default boot directly into MIA.
- Recovery and conventional desktop alternatives.
- A long-term architecture supporting PCs, Android devices, smart glasses, wearables, and embedded systems.

These are the future requirements, not assumptions about the existing implementation.

Your current assignment is to determine what MIA actually consists of today.

Repository

The primary project repository is:

"TheKingCS/MIA"

The local development environment has historically used:

"C:\Users\zacrh\MIA"

Verify the actual repository location and current structure before proceeding. Do not assume that the historical path or repository state is unchanged.

Inspect the existing Git repository, documentation, source code, configuration, tests, and available development infrastructure.

---

3. AUDIT PRINCIPLES

Follow these rules throughout the investigation.

3.1 Evidence over assumptions

Every important finding should be supported by repository evidence.

Whenever possible, include:

- File paths.
- Relevant classes, functions, or services.
- Configuration locations.
- API endpoints.
- Database models.
- Test locations.
- Documentation references.
- Git history when relevant.

Distinguish between something documented, something implemented, and something verified to work.

3.2 Do not mistake structure for functionality

A module existing does not prove that its functionality works.

A UI screen does not prove that its backend is connected.

An API endpoint does not prove that the operation succeeds.

A model integration does not prove that the model can be used in a complete workflow.

A test existing does not prove that the feature is fully covered.

Investigate the actual implementation and available evidence.

3.3 Preserve existing work

Do not delete, rename, reorganize, or rewrite existing project components.

Do not make architectural changes during this audit.

Do not attempt to fix technical debt as part of this assignment.

Your responsibility is to discover and document, not modify.

3.4 Be precise about uncertainty

Use the following classifications:

- Verified: supported by direct implementation evidence and successful verification where possible.
- Implemented: implementation exists, but runtime functionality has not been verified.
- Partially implemented: some required functionality exists, but the feature is incomplete.
- Experimental: prototype or unstable implementation.
- Documented only: described in documentation but not found in the implementation.
- Planned: explicitly intended for future development.
- Unverified: insufficient evidence to determine its status.
- Deprecated: no longer intended to be maintained or used.
- Broken: a specific failure has been reproduced or otherwise reliably established.

Never label a feature broken merely because you could not run it.

Never label something complete merely because it appears in documentation.

3.5 Respect security and privacy

Do not expose passwords, API keys, tokens, private credentials, or other secrets in audit documentation.

Identify where sensitive configuration is stored without reproducing its contents.

Do not transmit private project data to external services without authorization.

---

4. REPOSITORY STRUCTURE AND PROJECT INVENTORY

Begin by establishing the actual state of the repository.

Investigate:

- Repository root.
- Directory structure.
- Major application directories.
- Backend and frontend organization.
- Core services.
- Shared libraries.
- Configuration directories.
- Database and persistence layers.
- API definitions.
- Scripts and development utilities.
- Test directories.
- Documentation.
- Build and deployment configuration.
- Platform-specific implementations.
- Generated files and artifacts.
- Third-party dependencies.

Identify the major architectural boundaries.

Determine whether the project is:

- A monolith.
- A modular monolith.
- A collection of independently running services.
- A hybrid architecture.
- Another structure.

Do not choose a label based on appearance alone. Explain how the components actually execute and communicate.

Required deliverable: Repository Structure Report

Produce a useful hierarchical overview of the repository.

For every major directory, explain:

1. Its purpose.
2. Its primary components.
3. Its dependencies.
4. Its importance to the existing MIA ecosystem.
5. Whether it appears active, experimental, obsolete, or uncertain.

Do not produce an enormous unfiltered file listing. Focus on meaningful architectural structure.

---

5. TECHNOLOGY STACK AND DEVELOPMENT INFRASTRUCTURE

Identify the actual technologies used throughout MIA.

Investigate:

Programming languages

- Primary and secondary languages.
- Frameworks.
- Runtime environments.
- Build tools.
- Package managers.

Frontend

- UI frameworks.
- Component systems.
- Routing.
- State management.
- Styling.
- Responsive behavior.
- Browser dependencies.
- Native application integration.

Backend

- Server frameworks.
- Application services.
- Background workers.
- API architecture.
- Communication protocols.
- Authentication.
- Authorization.

Data and persistence

- Databases.
- File storage.
- Caching.
- Local persistence.
- Remote persistence.
- Data synchronization.
- Backup mechanisms.
- Encryption where implemented.

Infrastructure

- Deployment methods.
- Development servers.
- Containerization.
- Virtualization.
- CI/CD.
- Build processes.
- Logging.
- Monitoring.
- Error reporting.

External dependencies

- Third-party packages.
- External APIs.
- Cloud services.
- AI providers.
- Device-specific libraries.

For significant dependencies, record their versions and identify potential maintenance, licensing, compatibility, or security concerns.

Do not perform an indiscriminate dependency upgrade.

Required deliverable: Technology Stack Inventory

Create a structured inventory containing:

Component| Technology| Version| Purpose| Current Status

Include important dependencies and identify which technologies are foundational versus incidental.

---

6. MIA CORE AND INTERNAL ARCHITECTURE

Investigate the systems that make MIA function as a unified assistant.

Identify:

- Core application entry points.
- Core service architecture.
- Service initialization.
- Dependency injection or service registration.
- Event systems.
- Internal messaging.
- Shared state.
- Configuration management.
- Capability registration.
- Plugin or extension mechanisms.
- Error handling.
- Lifecycle management.
- Inter-service communication.

Determine whether MIA has a genuinely independent core or whether important functionality is tightly coupled to its current interfaces.

Investigate what happens when individual services fail.

Determine whether one unavailable service can cause unrelated capabilities to fail.

Questions to answer

1. Where does MIA's central application logic reside?
2. Which components represent MIA's persistent identity?
3. Which services are essential for basic operation?
4. Which services can operate independently?
5. How are capabilities discovered and invoked?
6. How are services initialized and shut down?
7. How is application state shared?
8. What dependencies prevent the core from operating independently of the current interface?
9. What would need to be extracted or decoupled to support an operating-system environment?

Required deliverable: MIA Core Architecture Report

Provide a component diagram and written explanation of the existing architecture.

Clearly identify architectural strengths, limitations, and potential OS migration implications.

Do not propose a complete replacement architecture here. That belongs to a later planning prompt.

---

7. EXISTING APPLICATIONS AND CAPABILITIES

Identify all applications, features, modules, and capabilities currently present in the repository.

Inspect both user-facing interfaces and their corresponding underlying services.

Organize findings into meaningful categories, such as:

- Core assistant.
- Conversations and AI interactions.
- Memory and knowledge.
- Voice and audio.
- Applications and navigation.
- Personal productivity.
- Home and smart devices.
- Homestead and agriculture.
- Finance and business.
- Health and fitness.
- Learning and personal development.
- Entertainment and recreation.
- Agent systems.
- System inspection and management.
- Communications.
- Wearables and external devices.
- Administrative and configuration tools.

This categorization is illustrative. Discover the actual structure rather than forcing every component into these categories.

For every significant feature, identify:

1. Feature name.
2. User-facing purpose.
3. Frontend implementation.
4. Backend implementation.
5. Supporting services.
6. Data dependencies.
7. External dependencies.
8. APIs or communication pathways.
9. Tests and verification evidence.
10. Current implementation status.
11. Known limitations.
12. Architectural dependencies.

Identify features that have overlapping responsibilities or duplicated functionality.

Required deliverable: Existing Capability Inventory

Create a structured feature inventory with clear evidence and status classifications.

This inventory must become the reference point for Prompt 02, which will determine how existing and planned capabilities should fit into MIA OS.

Do not design the migration strategy yet.

---

8. AI INFRASTRUCTURE AND MODEL INTEGRATIONS

Conduct a detailed investigation of MIA's existing AI infrastructure.

Identify:

Model integrations

- Local AI models.
- Cloud AI providers.
- Model APIs.
- Model configuration.
- Inference engines.
- Hardware acceleration.
- Model loading and unloading.
- Model selection.

Intelligence architecture

- Conversation management.
- Context construction.
- Prompt management.
- Reasoning and planning systems.
- Tool calling.
- Agent orchestration.
- Specialized agents.
- Multi-model interactions.
- Model fallback.
- Error handling.
- Response processing.

Memory and context

- Short-term conversation context.
- Persistent memory.
- User preferences.
- Long-term knowledge.
- Retrieval systems.
- Embeddings.
- Vector databases, if present.
- Memory indexing.
- Memory updates.
- Context retrieval.
- Memory privacy and deletion mechanisms.

Multimodal capabilities

- Speech recognition.
- Speech synthesis.
- Image understanding.
- Camera integration.
- Audio processing.
- Video or screen context, if implemented.
- Other sensor integrations.

Performance and reliability

Determine:

- Whether local inference actually works.
- Which hardware is required.
- How models are selected.
- Whether cloud fallback exists.
- How unavailable providers are handled.
- Whether inference can run independently of the interface.
- Whether model operations can be interrupted or cancelled.
- How resource consumption is managed.

Important quality investigation

Examine the reliability of MIA's responses and self-awareness.

Investigate whether the existing architecture distinguishes:

- Verified information.
- Retrieved information.
- Model inference.
- Speculation.
- Unknown information.

Determine whether MIA can accurately identify its own available capabilities and whether it has mechanisms for verifying that an application or integration actually exists.

Identify any known weaknesses in grounding, memory retrieval, context management, or self-knowledge that are supported by implementation evidence or reproducible tests.

Required deliverable: AI Infrastructure Audit

Document the actual AI architecture, model integrations, memory systems, multimodal capabilities, dependencies, and limitations.

Include a diagram showing the path from user input to model processing, tool execution, and response delivery.

---

9. USER INTERFACES AND DEVICE INTEGRATIONS

Investigate all existing interfaces and how they communicate with the rest of MIA.

Web interface

- Application structure.
- Routing.
- Navigation.
- UI component organization.
- State management.
- Backend communication.
- Responsive design.
- Authentication.
- Desktop and mobile behavior.

Android

- Native application structure.
- WebView or native components.
- Permissions.
- Background operation.
- Voice integration.
- Local services.
- Network communication.
- Device APIs.
- Packaging and installation.

PC integration

- Desktop functionality.
- Local server components.
- File access.
- Application launching.
- Hardware access.
- Input/output integrations.

Wearables and spatial interfaces

Investigate existing integrations or prototypes involving:

- Meta Ray-Ban Display.
- Smart glasses.
- Spatial interface components.
- Gesture interaction.
- Neural Band.
- Smartwatches.
- Other connected hardware.

Do not assume a planned integration is operational.

Identify what is implemented, what is experimental, and what remains conceptual.

Networking and device communication

Investigate:

- Local network communication.
- API endpoints.
- WebSockets or other persistent connections.
- Device discovery.
- Tailscale or other remote access integrations.
- Authentication between devices.
- Synchronization.
- Connection recovery.
- Data exchange.
- Offline behavior.

Required deliverable: Interface and Device Integration Report

Provide a device-by-device inventory and explain how each interface communicates with MIA's core services.

---

10. DATA ARCHITECTURE AND KNOWLEDGE MANAGEMENT

Investigate how MIA stores, organizes, accesses, and protects information.

Identify:

- Database schemas.
- Data models.
- User profiles.
- Preferences.
- Conversations.
- Memory records.
- Application data.
- Documents and files.
- Device information.
- Agent state.
- Project information.
- Logs and telemetry.
- Configuration.
- Credentials and secrets.

Determine which data is:

- Local.
- Cloud-hosted.
- Synchronized.
- Cached.
- Temporary.
- Persistent.
- Encrypted.
- Backed up.

Investigate relationships between data models and services.

Identify duplicated sources of truth, inconsistent schemas, data migration risks, and potential portability problems.

Determine whether MIA has a unified identity and data model or whether each application manages its information independently.

Required deliverable: Data Architecture Audit

Produce an overview of databases, schemas, storage locations, important data flows, and data ownership.

Include an assessment of what would be necessary to support persistent, cross-device MIA context in the future.

Do not redesign the data architecture yet.

---

11. SECURITY, PRIVACY, AND PERMISSIONS

Inspect the security model currently implemented.

Investigate:

- User authentication.
- Session management.
- API authentication.
- Authorization.
- Application permissions.
- Service privileges.
- File access.
- Command execution.
- Credential storage.
- Secrets management.
- Network security.
- Data encryption.
- External integrations.
- Agent permissions.
- Logging and audit trails.
- Administrative access.

Pay particular attention to any functionality that allows MIA to:

- Execute commands.
- Read or modify files.
- Access external services.
- Manage applications.
- Interact with connected devices.
- Control system resources.
- Modify its own configuration or code.

Identify the actual permission boundaries.

Determine whether security is enforced by trusted application code or merely by instructions given to an AI model.

Identify security weaknesses, privilege escalation risks, insecure defaults, and missing safeguards.

Do not expose credentials or reproduce sensitive values in reports.

Required deliverable: Existing Security Assessment

Document the current security architecture, implemented protections, known weaknesses, and areas requiring further investigation.

This is an assessment of the current system, not the final MIA OS security design.

---

12. TESTING, QUALITY, AND SOFTWARE RELIABILITY

Investigate the existing quality assurance infrastructure.

Identify:

- Unit tests.
- Integration tests.
- End-to-end tests.
- UI tests.
- API tests.
- AI evaluation tests.
- Security tests.
- Performance tests.
- Hardware tests.
- Device integration tests.
- Build validation.
- Continuous integration.

Determine:

1. How tests are organized.
2. How tests are executed.
3. Which components have meaningful coverage.
4. Which important workflows lack tests.
5. Whether tests are reliable and reproducible.
6. Whether tests require external services or hardware.
7. Whether test results are recorded.
8. Whether there are known failing or flaky tests.

Where practical, run existing non-destructive tests.

Record the exact commands used, environment requirements, results, failures, and limitations.

Do not claim a test suite passes if only a portion was executed.

Do not invent coverage percentages.

Required deliverable: Quality and Testing Assessment

Provide a factual overview of testing infrastructure, verified test results, quality gaps, and areas requiring future validation.

---

13. GIT HISTORY AND PROJECT EVOLUTION

Investigate the development history to understand how the architecture evolved.

Inspect:

- Current branch.
- Repository status.
- Recent commits.
- Major architectural changes.
- Significant feature additions.
- Refactoring history.
- Existing branches.
- Documented architectural decisions.
- Existing development milestones.
- Potentially abandoned approaches.

Identify relevant architecture decision records and explain their current significance.

Do not rely on historical commit counts or previous audit statistics without verifying them against the current repository.

Determine whether the current implementation reflects the most recent architectural direction.

Do not modify branches, commits, tags, or Git history.

Required deliverable: Project Evolution Report

Summarize important architectural milestones and decisions, current development state, and any historical context relevant to MIA OS.

---

14. TECHNICAL DEBT AND ARCHITECTURAL RISKS

Conduct a systematic assessment of the existing project's limitations.

Investigate:

Architectural risks

- Tight coupling.
- Circular dependencies.
- Monolithic components.
- Duplicated services.
- Inconsistent interfaces.
- Shared mutable state.
- Unclear ownership.
- Hidden dependencies.

Operational risks

- Fragile startup procedures.
- Service failures.
- Incomplete error handling.
- Poor recovery behavior.
- Resource leaks.
- Background task instability.
- Network dependency.
- Inconsistent configuration.

AI-specific risks

- Poor context management.
- Inaccurate self-awareness.
- Unreliable tool execution.
- Missing permission enforcement.
- Model-provider coupling.
- Uncontrolled resource consumption.
- Inadequate AI evaluation.

Development risks

- Inadequate tests.
- Poor documentation.
- Dependency conflicts.
- Difficult deployment.
- Lack of reproducible builds.
- Inconsistent development environments.

Migration risks

Identify components that may be particularly difficult to adapt to a Linux-based operating environment.

Investigate:

- Windows-specific dependencies.
- Android-specific dependencies.
- Browser-only functionality.
- Cloud-dependent services.
- Hardware-specific integrations.
- Database assumptions.
- UI and backend coupling.
- OS-specific file and process operations.

Classify risks by:

- Severity.
- Likelihood.
- Affected components.
- Evidence.
- Potential consequences.
- Whether the risk must be addressed before OS development.

Required deliverable: Technical Debt and Risk Register

Produce a prioritized list of verified problems and potential risks.

Clearly distinguish actual defects from architectural concerns and future compatibility questions.

---

15. OPERATIONAL DEPENDENCY AND DATA FLOW MAPPING

The previous sections identify individual components. Now determine how they work together.

Trace important workflows from beginning to end.

At minimum, investigate:

Conversation workflow

How does a user message travel through the interface, backend, context systems, AI provider, tool execution, and response delivery?

Memory workflow

How is information captured, stored, retrieved, updated, and used in future conversations?

Voice workflow

How does audio enter MIA, get processed, reach the AI system, and produce spoken output?

Tool execution workflow

How does MIA identify a capability, authorize it, invoke it, and receive the result?

Device communication workflow

How do devices connect, authenticate, exchange information, and recover from disconnection?

Application workflow

How does an application start, communicate with services, retrieve information, and maintain state?

For each workflow, identify:

- Entry point.
- Components involved.
- Sequence of operations.
- Data exchanged.
- Dependencies.
- Security checks.
- Failure handling.
- Exit point.

Use sequence diagrams or architecture diagrams where helpful.

Required deliverable: Existing System Data Flow and Dependency Map

Provide diagrams and explanations showing how the existing MIA ecosystem actually operates.

---

16. OS MIGRATION READINESS ASSESSMENT

This section is an initial assessment, not the complete migration design.

Based on the evidence gathered, evaluate the existing MIA ecosystem against the future Linux-based MIA OS requirements.

For each major component, assess:

- Can it operate independently of the current interface?
- Does it depend on Windows-specific functionality?
- Does it depend on browser-specific behavior?
- Does it require Android-specific APIs?
- Does it depend on cloud infrastructure?
- Can it operate locally?
- Does it require a persistent background service?
- Does it require hardware access?
- Does it have clear APIs?
- Does it have appropriate security boundaries?
- Does it have meaningful tests?
- Can it reasonably be reused in MIA OS?

Classify each component as:

1. Reusable with minimal changes.
2. Reusable with adaptation.
3. Requires significant refactoring.
4. Requires replacement.
5. Not suitable for migration.
6. Insufficient information.

Provide evidence and reasoning for every classification.

Do not make final technology or migration decisions. Those will be addressed in subsequent prompts.

Required deliverable: Preliminary OS Migration Readiness Matrix

This matrix will inform the feature integration and architecture planning stages.

---

17. REQUIRED FINAL DELIVERABLES

Complete the investigation and produce the following documentation in a dedicated MIA OS planning directory.

Primary documents

1. "MIA_OS_EXISTING_SYSTEM_AUDIT.md"
   
   - Comprehensive current-state assessment.
   - Repository structure.
   - Existing architecture.
   - Major components.
   - Technical condition.
   - Important findings.

2. "MIA_OS_FEATURE_INVENTORY.md"
   
   - Existing applications and capabilities.
   - Implementation status.
   - Dependencies.
   - Evidence.
   - Known limitations.

3. "MIA_OS_TECHNOLOGY_STACK.md"
   
   - Languages.
   - Frameworks.
   - Libraries.
   - Databases.
   - Infrastructure.
   - Versions.
   - Important dependencies.

4. "MIA_OS_DATA_ARCHITECTURE_AUDIT.md"
   
   - Databases.
   - Data models.
   - Storage.
   - Synchronization.
   - Data flows.
   - Data ownership.

5. "MIA_OS_EXISTING_SECURITY_ASSESSMENT.md"
   
   - Current security implementation.
   - Permission boundaries.
   - Vulnerabilities and gaps.
   - Unresolved questions.

6. "MIA_OS_TESTING_AND_QUALITY_AUDIT.md"
   
   - Test infrastructure.
   - Verified results.
   - Coverage information where available.
   - Quality gaps.

7. "MIA_OS_TECHNICAL_DEBT_AND_RISK_REGISTER.md"
   
   - Technical debt.
   - Architectural limitations.
   - Operational weaknesses.
   - Migration risks.
   - Priorities.

8. "MIA_OS_DEPENDENCY_AND_DATA_FLOW_MAP.md"
   
   - Component relationships.
   - Operational workflows.
   - Data flow diagrams.
   - Dependency diagrams.

9. "MIA_OS_MIGRATION_READINESS.md"
   
   - Preliminary component-by-component migration readiness.
   - Compatibility concerns.
   - Reuse opportunities.
   - Areas requiring additional investigation.

Central documentation updates

Update:

- "MIA_OS_STATUS.md"
- "MIA_OS_OPEN_QUESTIONS.md"
- "MIA_OS_RISK_REGISTER.md"
- "MIA_OS_MASTER_PLAN.md"

The master plan should include a concise summary of the audit and reference the supporting documents.

Do not duplicate entire reports unnecessarily.

---

18. AUDIT COMPLETION CRITERIA

This assignment is complete only when:

1. The actual repository has been inspected.
2. Major directories and architectural components have been identified.
3. The technology stack has been inventoried.
4. Existing applications and capabilities have been catalogued.
5. The MIA Core architecture has been investigated.
6. AI and memory infrastructure has been traced.
7. User interfaces and device integrations have been examined.
8. Data architecture and persistence have been documented.
9. Security implementation has been assessed.
10. Testing infrastructure has been examined.
11. Important operational workflows have been traced.
12. Technical debt and migration risks have been documented.
13. A preliminary migration readiness assessment has been completed.
14. Findings are supported by evidence.
15. Uncertainties and missing information are clearly identified.
16. All required planning documents have been created or updated.

Do not artificially inflate the completeness of the audit.

If a component cannot be inspected or tested, document the limitation and explain what would be required to verify it.

---

19. FINAL RESPONSE FORMAT

After completing the investigation, provide a concise but informative completion report containing:

A. Repository condition

What was inspected and the overall state of the project.

B. Architectural findings

The most important discoveries about how MIA currently works.

C. Existing capabilities

A summary of the actual applications, services, and capabilities found.

D. Major strengths

Existing architecture and functionality that should be preserved.

E. Major weaknesses

The most important technical debt, reliability issues, and architectural limitations.

F. OS migration implications

The most important findings affecting the transformation into MIA OS.

G. Unresolved questions

Information that still needs to be established.

H. Documentation produced

A list of all reports and supporting diagrams.

I. Recommended next step

A brief explanation of what Prompt 02 should investigate based on the actual findings.

Do not begin Prompt 02 automatically.

Wait for project-owner review and authorization before continuing.

---

FINAL INSTRUCTION

The most important outcome of this assignment is an accurate understanding of the MIA ecosystem as it actually exists.

Do not optimize for making the project appear more advanced than it is.

Do not hide weaknesses.

Do not dismiss existing accomplishments.

Understand the architecture, establish the facts, and document the findings.

We are building the foundation for an operating system that may evolve over many years. The quality of every subsequent architectural decision depends on the accuracy of this initial investigation.
