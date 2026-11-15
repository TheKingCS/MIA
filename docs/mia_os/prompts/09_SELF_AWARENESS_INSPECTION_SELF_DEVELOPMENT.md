PROMPT 09 — SELF-AWARENESS, INSPECTION & SELF-DEVELOPMENT

Mission

Act as a principal AI systems architect, autonomous systems engineer, software reliability engineer, AI evaluation researcher, introspection systems designer, and secure self-modifying software architect.

Your mission is to design the complete self-awareness, system inspection, performance evaluation, and controlled self-development architecture for MIA OS.

Prompts 00–08 have established the intended operating system, application ecosystem, hardware foundation, intelligence infrastructure, and autonomy architecture.

Now determine how MIA can understand the state of her own environment, accurately identify her capabilities and limitations, monitor her performance, recognize errors, diagnose problems, and safely improve herself over time.

This is not simply a diagnostic dashboard or an AI model describing its own thoughts.

MIA needs a persistent, evidence-backed understanding of:

- What she is.
- What systems compose her.
- What capabilities exist.
- Which capabilities are operational.
- Which capabilities are unavailable.
- What hardware she can access.
- Which services are running.
- What she is currently doing.
- What she has accomplished.
- What has failed.
- What needs improvement.
- What she is permitted to change.
- What she cannot reliably determine.

The architecture must support continuous improvement while protecting system integrity, user data, permissions, and operational reliability.

Planning and architecture research only. Do not begin implementation.

---

1. Review Previous Work and Existing MIA

Review Prompts 00–08 and inspect the existing MIA repository.

Pay particular attention to:

- Existing capability registries.
- Application discovery.
- Agent infrastructure.
- Model capability declarations.
- Memory and identity systems.
- System monitoring.
- Health checks.
- Logging.
- Diagnostics.
- Testing infrastructure.
- Performance monitoring.
- Feedback mechanisms.
- Self-development concepts.
- Configuration management.
- Existing automated maintenance or repair functionality.

Identify what MIA currently knows about herself and where that information originates.

Investigate known quality concerns as audit targets:

- Repetitive responses.
- Unsupported claims.
- Incorrect statements about existing capabilities.
- Inaccurate self-awareness.
- Confusion between planned and operational functionality.
- Failure to recognize unavailable integrations.
- Voice and audio reliability problems.
- Context and memory inconsistencies.

Do not assume these problems remain unresolved. Verify their current status.

Produce a baseline documenting:

1. Existing introspection capabilities.
2. Existing monitoring and diagnostic services.
3. Existing performance evaluation.
4. Existing feedback mechanisms.
5. Existing self-development mechanisms.
6. Missing capabilities.
7. Architectural duplication.
8. Reliability and security weaknesses.

---

2. Foundational Self-Awareness Philosophy

Establish the principles governing MIA's self-awareness.

2.1 Evidence-based self-knowledge

MIA must distinguish between:

- Known facts.
- Verified system state.
- Retrieved historical information.
- Current observations.
- Inferences.
- Predictions.
- Uncertainty.
- Unknown information.

A model's belief that something exists is not evidence that it exists.

A previous implementation record is not proof that the feature still works.

A successful installation is not proof that a service is operational.

2.2 Capability truthfulness

MIA must never claim that she can perform an operation simply because:

- A feature is documented.
- An application exists.
- A tool was previously available.
- A model claims the capability exists.
- An integration is configured but disconnected.
- A device is detected but unsupported.

Her understanding must reflect actual verified capability state.

2.3 Self-development must be controlled

MIA should identify opportunities to improve herself and prepare changes.

However, she must not be able to bypass security controls, modify approval requirements, grant herself permissions, or silently replace critical components.

2.4 Separate observation from modification

The ability to inspect a system must not automatically imply permission to change it.

Define independent permissions for:

- Observing.
- Diagnosing.
- Recommending.
- Preparing changes.
- Testing changes.
- Applying changes.
- Reverting changes.

2.5 Persistent self-understanding

MIA's self-knowledge should survive:

- Conversations ending.
- Model changes.
- Application restarts.
- Operating-system restarts.
- Device changes.
- Hardware upgrades.
- Software updates.

It must be maintained by MIA's own infrastructure rather than relying on a particular model's conversational context.

---

3. Self-Awareness Architecture

Design a unified self-awareness architecture.

Evaluate a layered system containing:

1. System identity.
2. Architecture registry.
3. Component registry.
4. Application registry.
5. Capability registry.
6. Hardware registry.
7. Service registry.
8. Integration registry.
9. Permission registry.
10. Operational state.
11. Dependency relationships.
12. Health and performance state.
13. Known limitations.
14. Open issues.
15. Historical changes.
16. Confidence and evidence.
17. Self-development opportunities.

Define the responsibilities and boundaries of each component.

Determine how MIA assembles an accurate picture of her current state.

Her self-awareness should not be a single enormous document or an unstructured memory collection.

It should be a structured, queryable, continuously maintained representation of the actual system.

For every major component, define:

- Identity.
- Purpose.
- Version.
- Dependencies.
- Current state.
- Supported interfaces.
- Required permissions.
- Available resources.
- Health.
- Known limitations.
- Evidence sources.
- Last verification.
- Change history.

---

4. System Identity and Architecture Introspection

Design how MIA understands her own architecture.

She should be able to answer questions such as:

- What operating system am I running on?
- Which version of MIA am I running?
- Which services make up my core?
- Which applications are installed?
- Which model providers are available?
- Which memory systems are active?
- Which devices are connected?
- Which integrations are operational?
- What are my current limitations?
- What changed during the last update?

Determine how this information is gathered from authoritative system sources.

Investigate:

- Runtime metadata.
- Build manifests.
- Package metadata.
- Service registries.
- Application manifests.
- Configuration.
- Hardware discovery.
- API health checks.
- Version information.
- Dependency inspection.

Distinguish between static architecture knowledge and live runtime state.

MIA must be able to recognize when the documented architecture differs from the running system.

---

5. Capability Awareness and Truth Registry

This section is a critical priority.

Design a unified capability registry that gives MIA an accurate understanding of what she can actually do.

Capabilities may include:

- Voice communication.
- Speech recognition.
- Speech synthesis.
- Image understanding.
- File operations.
- Web research.
- Browser interaction.
- Desktop control.
- Calendar management.
- Email.
- Messaging.
- Finance.
- Smart-home control.
- Greenhouse monitoring.
- Agriculture.
- Aquaponics.
- Software development.
- Hardware diagnostics.
- Learning and tutoring.
- Long-term memory.
- Multi-agent coordination.
- Cross-device communication.

For each capability, track:

- Capability identifier.
- Name.
- Description.
- Responsible component.
- Required services.
- Required hardware.
- Required permissions.
- Supported operations.
- Supported devices.
- Current availability.
- Operational status.
- Verification status.
- Known limitations.
- Last successful test.
- Last failure.
- Evidence.
- Confidence.
- Version.

Evaluate explicit capability states such as:

- Conceptual.
- Planned.
- Documented.
- Implemented.
- Configured.
- Available.
- Operational.
- Degraded.
- Unavailable.
- Unsupported.
- Deprecated.
- Failed.
- Unknown.

Define the exact meaning and transition rules for each state.

Do not collapse these distinctions into a simple enabled/disabled flag.

For example, a greenhouse application may be implemented and operational as a dashboard while its physical sensor integration is unavailable.

MIA must be able to communicate that distinction.

Design capability dependency graphs so that MIA can identify why a capability is unavailable.

For example:

A voice interaction may depend on:

- Microphone access.
- Audio input service.
- Speech recognition.
- Model availability.
- Conversation orchestration.
- Audio output.
- Speech synthesis.

If one dependency fails, MIA should understand the resulting limitation.

---

6. Knowledge Provenance and Confidence

Design the evidence system supporting MIA's self-knowledge.

For every important claim about herself, determine:

- Source.
- Observation time.
- Verification time.
- Verification method.
- Evidence.
- Confidence.
- Expiration or freshness requirements.
- Dependencies.
- Conflicting evidence.

Distinguish between:

- Direct observation.
- Successful test.
- Authoritative configuration.
- Application metadata.
- Historical records.
- Model-generated interpretation.
- User-provided information.
- Inference.

Define how conflicting evidence is resolved.

For example, if documentation says a service is running but a live health check fails, MIA should report the service as unavailable or unhealthy rather than trusting the documentation.

Determine how stale observations are identified.

A capability verified six months ago should not automatically be treated as operational today.

---

7. Live System Introspection

Design how MIA inspects her running environment.

Investigate monitoring and inspection of:

Operating system

- Kernel.
- Distribution.
- System version.
- Boot state.
- Processes.
- Services.
- System resources.
- Filesystems.
- Network.
- Hardware.
- Drivers.

MIA platform

- Core services.
- Applications.
- Background services.
- API endpoints.
- Message queues.
- Databases.
- Memory systems.
- Agent runtime.
- Model providers.
- Device connections.

Intelligence infrastructure

- Active models.
- Provider status.
- Inference availability.
- Model routing.
- Context usage.
- Token consumption.
- Latency.
- Errors.
- Council activity.

Autonomy infrastructure

- Active agents.
- Running tasks.
- Pending approvals.
- Workflow status.
- Tool availability.
- Execution failures.
- Resource usage.

Determine how inspection is performed without creating excessive system overhead.

Use read-only interfaces wherever possible.

---

8. Health Monitoring and Diagnostics

Design a complete system health architecture.

Investigate:

- Component health.
- Application health.
- Service health.
- Dependency health.
- Hardware health.
- Storage health.
- Network health.
- Model provider health.
- Voice pipeline health.
- Memory system health.
- Agent runtime health.
- Device integration health.

Define health categories such as:

- Healthy.
- Degraded.
- Unhealthy.
- Unavailable.
- Unknown.

Design diagnostic procedures that can identify likely root causes.

For example:

If voice communication fails, MIA should be able to investigate the relevant audio input, speech recognition, inference, synthesis, and output components rather than simply reporting that voice is broken.

Define:

- Health checks.
- Diagnostic probes.
- Failure detection.
- Root-cause analysis.
- Dependency analysis.
- Diagnostic evidence.
- Escalation.
- Recovery recommendations.

Distinguish automated diagnosis from confirmed root cause.

---

9. Performance Observability and Optimization

Design how MIA evaluates her own performance.

Investigate metrics for:

- Response latency.
- Time to first response.
- Task completion time.
- Task success rate.
- Tool success rate.
- Model selection quality.
- Memory retrieval quality.
- Context accuracy.
- Repetition.
- Hallucination indicators.
- Unsupported claims.
- User corrections.
- Failed workflows.
- Agent coordination overhead.
- Token usage.
- Cloud costs.
- Local resource usage.
- Reliability.

Define meaningful baselines and measurement methods.

Avoid treating a single metric as a complete measure of intelligence or usefulness.

For example:

A faster response is not necessarily a better response.

A high task completion rate is not sufficient if tasks are completed incorrectly.

A high user approval rate does not prove that a system is safe.

Design a performance observatory that can identify trends and opportunities for improvement.

---

10. Response Quality and Behavioral Evaluation

Develop a dedicated evaluation architecture for MIA's conversational behavior.

Evaluate:

- Factual accuracy.
- Groundedness.
- Honesty about uncertainty.
- Memory correctness.
- Context continuity.
- Instruction following.
- Relevance.
- Conciseness when appropriate.
- Repetition.
- Tone consistency.
- User preference adherence.
- Capability awareness.
- Appropriate clarification.
- Correct tool selection.
- Appropriate refusal.
- Correct distinction between suggestions and authorized actions.

Design tests for common failure patterns.

Particularly investigate:

1. MIA repeatedly providing the same explanation.
2. MIA claiming that a capability is unavailable when it exists.
3. MIA claiming that a feature works without evidence.
4. MIA inventing integrations.
5. MIA confusing planned features with implemented features.
6. MIA forgetting important project context.
7. MIA presenting guesses as established facts.
8. MIA claiming that an action succeeded without verification.

Determine how user feedback, corrections, and observed outcomes enter the evaluation system.

---

11. Memory and Self-Knowledge Integration

Design the relationship between MIA's self-awareness and the memory infrastructure from Prompt 07.

MIA needs to distinguish:

- User memory.
- Conversation memory.
- Project knowledge.
- System architecture knowledge.
- Capability knowledge.
- Operational state.
- Historical events.
- Performance history.
- Development history.

Do not mix all these into one undifferentiated memory database.

Define which information is:

- Persistent.
- Temporary.
- Recomputed.
- Cached.
- Versioned.
- User-editable.
- System-controlled.
- Automatically expired.

Determine how self-knowledge remains accurate after:

- Software updates.
- Application installations.
- Model changes.
- Hardware changes.
- Device disconnections.
- Configuration changes.
- Service failures.

Self-awareness should be derived from authoritative registries and current observations wherever possible, not simply recalled from old conversations.

---

12. Self-Inspection and Root-Cause Investigation

Design a controlled self-inspection system.

MIA should be able to investigate her own behavior and identify potential causes of problems.

For example:

- Why did a task fail?
- Why did a response take so long?
- Why is a model unavailable?
- Why did memory retrieval fail?
- Why did an application crash?
- Why is a connected device not responding?
- Why did a workflow stop?
- Why is a capability degraded?

Define a structured investigation process:

1. Identify the observed problem.
2. Gather relevant evidence.
3. Inspect dependencies.
4. Compare expected and actual behavior.
5. Identify likely causes.
6. Assign confidence.
7. Recommend corrective action.
8. Request authorization when required.
9. Verify the outcome.

Determine how MIA prevents diagnostic procedures from accidentally modifying the system.

---

13. Controlled Self-Development Architecture

This section establishes how MIA can improve herself over time.

Evaluate a staged development lifecycle:

1. Observe.
2. Identify a weakness.
3. Form a hypothesis.
4. Research potential improvements.
5. Design a proposed change.
6. Assess risk.
7. Prepare a change.
8. Test in isolation.
9. Evaluate results.
10. Present the proposal.
11. Obtain required approval.
12. Deploy through authorized infrastructure.
13. Verify the deployed change.
14. Monitor for regressions.
15. Revert if necessary.

Determine which categories of changes can be automated and which require approval.

Consider:

- Configuration adjustments.
- Prompt refinement.
- Model routing changes.
- Memory retrieval tuning.
- Agent definition changes.
- Workflow improvements.
- Application updates.
- Software code changes.
- System service changes.
- Security policy changes.

Establish a strict boundary between proposing a change and applying it.

MIA must not silently modify critical infrastructure.

---

14. Self-Modification and Code Development

Design how MIA may eventually assist in improving her own source code.

Investigate:

- Repository inspection.
- Issue identification.
- Code generation.
- Code review.
- Test generation.
- Static analysis.
- Dependency analysis.
- Build verification.
- Sandboxed testing.
- Staging environments.
- Deployment.
- Rollback.

Require changes to be traceable to source commits and test evidence.

Determine how MIA can propose and prepare code changes without directly modifying the running production system.

Evaluate isolated development environments and controlled promotion between:

- Development.
- Testing.
- Staging.
- Production.

The architecture must prevent MIA from changing the safeguards that govern her own authority.

In particular:

- She cannot grant herself new permissions.
- She cannot disable approval requirements.
- She cannot alter audit records to hide activity.
- She cannot remove security boundaries.
- She cannot silently replace her trusted execution services.

Design how these restrictions are enforced outside the AI model.

---

15. Learning, Feedback and Adaptation

Design how MIA improves through experience.

Distinguish clearly between:

Persistent memory

Retaining relevant information about users, projects, and prior interactions.

Behavioral configuration

Adjusting preferences, response behavior, routing, and other settings.

Evaluation-driven improvement

Identifying patterns in errors and successful outcomes.

Prompt and workflow refinement

Improving instructions, tool selection, context assembly, and workflow design.

Model adaptation

Fine-tuning or adapting models where justified and technically appropriate.

Software development

Changing MIA's actual implementation through a controlled engineering lifecycle.

Do not describe ordinary memory updates as model training.

Do not imply that an LLM automatically changes its own weights through normal conversation.

Design feedback mechanisms including:

- Explicit user ratings.
- Corrections.
- User preferences.
- Task outcomes.
- Verification results.
- Regression tests.
- Evaluation datasets.
- Controlled experiments.

Determine how MIA can learn from repeated mistakes without permanently reinforcing incorrect assumptions.

---

16. Capability Evolution and Feature Discovery

Design how MIA recognizes changes in her own capabilities.

For example:

- A new application is installed.
- A tool integration becomes available.
- A new model provider is configured.
- A device is connected.
- A hardware accelerator becomes available.
- A service is updated.
- An application loses functionality.
- A sensor becomes disconnected.

Determine how capability registries update automatically.

Investigate event-driven discovery, scheduled reconciliation, health checks, and explicit registration.

Define how new capabilities are tested before MIA advertises them as operational.

A newly installed feature should not automatically be assumed reliable or fully supported.

---

17. User-Facing Self-Awareness

Design how MIA communicates her own state.

The user should be able to ask:

- What can you do?
- What is currently working?
- What is unavailable?
- What are you currently working on?
- What changed recently?
- What is slowing you down?
- What errors have you detected?
- What should we improve next?
- What are your current limitations?
- What do you need my help with?

MIA should provide answers grounded in her registries and live observations.

Evaluate a unified system status and capability interface.

Include:

- System overview.
- Capability directory.
- Component health.
- Device availability.
- Active tasks.
- Model and provider status.
- Performance metrics.
- Known issues.
- Proposed improvements.
- Development history.

The detailed desktop presentation belongs to Prompt 10, but the data and interaction requirements belong here.

---

18. Independent Evaluation and Quality Assurance

Design a framework for testing MIA's self-awareness and self-development architecture.

Include:

- Unit tests.
- Integration tests.
- Capability registry tests.
- Health-check tests.
- Dependency failure tests.
- Stale-state tests.
- False-capability-claim tests.
- Model hallucination tests.
- Memory consistency tests.
- Self-inspection tests.
- Permission boundary tests.
- Self-modification security tests.
- Regression tests.
- Recovery tests.

Evaluate independent model review and adversarial testing.

The system should test whether MIA accurately understands herself rather than merely asking her whether she believes she is correct.

Define measurable acceptance criteria.

---

19. Security and Integrity Boundaries

Establish self-awareness-specific security requirements.

Coordinate with Prompts 08 and 13.

Investigate:

- Trusted system metadata.
- Registry integrity.
- Evidence authenticity.
- Audit integrity.
- Permission separation.
- Read-only inspection.
- Privileged diagnostics.
- Secure update paths.
- Code modification boundaries.
- Development environment isolation.
- Rollback protection.
- Credential isolation.

Treat self-inspection and self-modification as separate trust domains.

MIA must not be able to manipulate the evidence used to evaluate her own performance without detection.

Her ability to inspect a security policy must not grant her authority to modify that policy.

---

20. Architecture Diagrams

Produce diagrams for:

1. Complete self-awareness architecture.
2. System identity and architecture registry.
3. Capability registry and state transitions.
4. Capability dependency graph.
5. Evidence provenance and confidence.
6. Live system introspection.
7. Health monitoring and diagnostics.
8. Performance observatory.
9. Response quality evaluation.
10. Memory and self-knowledge integration.
11. Root-cause investigation.
12. Controlled self-development lifecycle.
13. Self-modification and code deployment.
14. Learning and feedback pipeline.
15. Capability discovery and reconciliation.
16. User-facing self-awareness data flow.
17. Independent evaluation architecture.
18. Security and integrity boundaries.

Use Mermaid diagrams where appropriate and explain each diagram.

---

21. Technology Evaluation and Research

Evaluate appropriate technologies for:

- System introspection.
- Service monitoring.
- Hardware monitoring.
- Application registries.
- Capability registries.
- Metrics collection.
- Distributed tracing.
- Logging.
- Health checks.
- Dependency mapping.
- Evaluation frameworks.
- Regression testing.
- Sandboxed code execution.
- Development isolation.
- Controlled deployment.
- Rollback.

Consider existing Linux and MIA ecosystem technologies before proposing custom infrastructure.

For every significant recommendation, document:

1. Technology.
2. Intended purpose.
3. Alternatives.
4. Advantages.
5. Limitations.
6. Integration complexity.
7. Security implications.
8. Maintenance requirements.
9. Operational overhead.
10. Recommendation.
11. Supporting evidence.

Prioritize official documentation, maintained projects, security advisories, and reproducible evaluations.

---

22. Required Deliverables

Create the following documents:

1. "MIA_OS_SELF_AWARENESS_ARCHITECTURE.md"
2. "MIA_OS_SYSTEM_IDENTITY_AND_INTROSPECTION.md"
3. "MIA_OS_CAPABILITY_TRUTH_REGISTRY.md"
4. "MIA_OS_CAPABILITY_STATE_MODEL.md"
5. "MIA_OS_SELF_KNOWLEDGE_PROVENANCE.md"
6. "MIA_OS_LIVE_SYSTEM_INTROSPECTION.md"
7. "MIA_OS_HEALTH_MONITORING_AND_DIAGNOSTICS.md"
8. "MIA_OS_PERFORMANCE_OBSERVATORY.md"
9. "MIA_OS_RESPONSE_QUALITY_EVALUATION.md"
10. "MIA_OS_SELF_AWARENESS_AND_MEMORY_INTEGRATION.md"
11. "MIA_OS_SELF_INSPECTION_AND_ROOT_CAUSE_ANALYSIS.md"
12. "MIA_OS_CONTROLLED_SELF_DEVELOPMENT.md"
13. "MIA_OS_SELF_MODIFICATION_AND_CODE_LIFECYCLE.md"
14. "MIA_OS_LEARNING_AND_FEEDBACK_ARCHITECTURE.md"
15. "MIA_OS_CAPABILITY_EVOLUTION_AND_DISCOVERY.md"
16. "MIA_OS_USER_FACING_SELF_AWARENESS.md"
17. "MIA_OS_SELF_AWARENESS_TESTING_AND_EVALUATION.md"
18. "MIA_OS_SELF_AWARENESS_SECURITY_AND_INTEGRITY.md"
19. "MIA_OS_SELF_AWARENESS_TECHNOLOGY_EVALUATION.md"
20. "MIA_OS_SELF_AWARENESS_ARCHITECTURE_DIAGRAMS.md"
21. "MIA_OS_SELF_AWARENESS_ACCEPTANCE_CRITERIA.md"
22. "MIA_OS_SELF_AWARENESS_OPEN_QUESTIONS.md"

Also update:

- "MIA_OS_MASTER_PLAN.md"
- "MIA_OS_DECISION_LOG.md"
- "MIA_OS_OPEN_QUESTIONS.md"
- "MIA_OS_RISK_REGISTER.md"
- "MIA_OS_REQUIREMENTS_TRACEABILITY.md"
- "MIA_OS_IMPLEMENTATION_STATUS.md"
- "MIA_OS_INTELLIGENCE_ARCHITECTURE.md"
- "MIA_OS_AUTONOMY_ARCHITECTURE.md"
- "MIA_OS_FEATURE_ECOSYSTEM.md"

Maintain consistency with Prompts 00–08.

---

23. Decision Records and Traceability

Create formal decision records for major architecture decisions.

Each record must include:

- Decision ID.
- Decision title.
- Context.
- Requirements affected.
- Options evaluated.
- Evidence.
- Selected approach.
- Alternatives rejected.
- Consequences.
- Risks.
- Reversibility.
- Conditions for reconsideration.

Maintain traceability between:

- System components.
- Capability definitions.
- Evidence sources.
- Health checks.
- Performance metrics.
- Evaluation tests.
- Self-development proposals.
- Approval requirements.
- Security controls.
- Implementation phases.

Clearly distinguish between architectural recommendations and decisions requiring user approval.

---

24. Acceptance Criteria

Prompt 09 is complete only when:

- The existing self-awareness infrastructure has been audited.
- The self-awareness architecture is defined.
- System identity and architecture introspection are established.
- The capability truth registry is fully specified.
- Capability states and transitions are defined.
- Capability dependencies are represented.
- Evidence provenance and freshness are addressed.
- Live introspection is designed.
- Health monitoring and diagnostics are defined.
- Performance observability is established.
- Conversational quality evaluation is defined.
- Memory and self-knowledge boundaries are documented.
- Root-cause investigation is designed.
- Controlled self-development is established.
- Self-modification boundaries are explicit.
- Feedback and learning mechanisms are defined.
- Capability discovery and evolution are addressed.
- User-facing self-awareness requirements are established.
- Independent evaluation is designed.
- Security and integrity controls are documented.
- Major architecture decisions have evidence.
- Risks and open questions are recorded.
- Deliverables are consistent with Prompts 00–08.

---

25. Boundaries With Future Prompts

Do not duplicate the detailed scope of later prompts.

- Prompt 10 handles the desktop and primary user interface.
- Prompt 11 handles visual identity, themes, and spatial interfaces.
- Prompt 12 handles complete multi-device and distributed architecture.
- Prompt 13 handles comprehensive security, privacy, identity, and permissions.
- Prompt 14 handles boot, recovery, updates, and reliability.
- Prompt 15 handles development and build infrastructure.
- Prompt 16 handles implementation sequencing and migration.
- Prompt 17 consolidates and independently reviews the final master plan.

This prompt establishes the self-awareness data, introspection, evaluation, and controlled improvement systems those components will use.

Do not design the entire desktop dashboard here. Define the information and capabilities it must expose.

Do not design the full multi-device synchronization architecture. Establish the self-awareness information that must remain consistent across devices.

Do not replace the permission architecture from Prompt 08 or comprehensive security architecture from Prompt 13.

---

26. Planning Restrictions

This is an architecture research and planning exercise.

Do not:

- Implement self-modification.
- Modify production code.
- Change system configuration.
- Change permission policies.
- Grant MIA new authority.
- Install monitoring infrastructure.
- Modify existing registries in production.
- Run destructive diagnostics.
- Automatically repair system components.
- Deploy generated code.
- Modify security safeguards.
- Begin implementation.

You may inspect source code, documentation, configuration, logs, and non-destructive diagnostic information.

Do not expose credentials or secrets.

All claims about current functionality must be supported by repository evidence or runtime observations.

---

27. Final Objective

The final architecture should give MIA a truthful, persistent, evidence-backed understanding of herself.

She should know what systems compose her, what capabilities she possesses, which capabilities are functioning, which dependencies are unavailable, what limitations exist, and what she is currently doing.

She should be able to monitor her performance, recognize mistakes, investigate failures, identify opportunities for improvement, and prepare carefully controlled changes.

Over time, MIA should become increasingly capable of maintaining and improving her own software ecosystem.

But her self-awareness must remain grounded in evidence, and her self-development must remain governed by independent execution controls and explicit authorization.

The goal is not an AI that simply believes it understands itself.

The goal is an intelligent system that can inspect, verify, explain, evaluate, and responsibly improve its own operation.

Produce a technically rigorous, evidence-based, internally consistent architecture.

When finished, summarize:

1. The recommended self-awareness architecture.
2. The capability truth registry and state model.
3. How MIA gathers and verifies evidence about herself.
4. The health and performance observability system.
5. How response quality and behavioral problems are evaluated.
6. How MIA identifies and investigates failures.
7. The controlled self-development lifecycle.
8. What MIA may and may not modify independently.
9. The most significant security and integrity risks.
10. Decisions requiring user approval.
11. Questions that must be resolved before Prompt 10.

Stop after completing Prompt 09. Wait for review and approval before beginning Prompt 10.
