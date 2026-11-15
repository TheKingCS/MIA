SUPPLEMENTAL DIRECTIVE — MIA OS FINAL ARCHITECTURE QUALITY, EVIDENCE & IMPLEMENTATION STANDARDS

This directive supplements Prompt 17. It does not replace, weaken, or override its requirements.

Its purpose is to ensure that the final MIA OS blueprint is accurate, practical, complete, and suitable for implementation by a small development operation relying heavily on AI-assisted engineering.

1. Evidence Must Take Priority Over Previous Conclusions

Do not trust a previous architectural document simply because Claude produced it.

Do not trust a previous repository audit simply because it appears comprehensive.

Reverify important claims against the actual repository, source code, configuration, tests, documentation, and current technical references.

For every important claim, identify its evidence source.

Use these distinctions:

- Verified directly in source code.
- Verified through successful execution or testing.
- Supported by official technical documentation.
- Inferred from available evidence.
- Assumed but unverified.
- Proposed for future implementation.

Never present an inference as a verified fact.

Never present planned functionality as an existing capability.

If evidence is unavailable, explicitly say so.

2. Preserve the Existing MIA Project

The existing MIA repository is the foundation of this initiative, not disposable prototype material.

Before recommending replacement or rewriting any subsystem:

1. Identify its current implementation.
2. Determine what works.
3. Identify its dependencies.
4. Evaluate its maintainability.
5. Compare reuse, adaptation, replacement, and retirement.
6. Explain the migration cost and risks.
7. Identify how existing user data and functionality will be preserved.
8. Define a rollback strategy.

Prefer incremental evolution over unnecessary rewrites.

A replacement must have a demonstrable technical advantage.

Do not sacrifice functioning capabilities merely to achieve architectural purity.

3. Separate the Long-Term Vision from the First Build

MIA is intended to grow into a substantial intelligent operating environment.

However, the first implementation must not attempt to deliver every future capability.

Classify every major capability into:

- Foundation: required before meaningful implementation can proceed.
- MVP: required for the first usable MIA OS release.
- Early expansion: appropriate for subsequent releases.
- Long-term vision: important but not required initially.
- Experimental: requires further research or hardware validation.
- Deferred: deliberately excluded from the current roadmap.

Do not confuse architectural support for a future capability with implementing that capability now.

Design for extensibility without building unnecessary infrastructure prematurely.

4. Every Implementation Work Package Must Be Executable

A roadmap entry is not an implementation plan unless a developer can understand exactly what to do.

Every work package must include:

- Unique work package ID.
- Objective.
- User-facing or technical requirement IDs.
- Existing components affected.
- Files, modules, or subsystems expected to change, where known.
- Dependencies and prerequisites.
- Detailed implementation tasks.
- Expected deliverables.
- Security considerations.
- Failure and rollback considerations.
- Unit tests.
- Integration tests.
- Acceptance criteria.
- Definition of done.
- Required human approval.
- Recommended implementation agent or specialist.

Where exact file paths cannot yet be known, specify the repository inspection needed to determine them. Do not invent paths.

Work packages must be small enough to implement, review, test, and merge independently wherever practical.

5. Establish a Real Source of Architectural Truth

Create a clear hierarchy for all MIA OS documentation.

At minimum:

1. Final master implementation blueprint.
2. Approved architecture decision log.
3. Requirements and traceability register.
4. Domain architecture specifications.
5. Implementation roadmap and work packages.
6. Supporting research and technical references.
7. Historical and superseded documentation.

Explain which document governs when two documents disagree.

Assign versions and dates to authoritative documents.

Establish a consistent method for recording changes.

Do not allow an old recommendation to remain indistinguishable from a current approved decision.

6. Strengthen the AI-Assisted Development Process

MIA OS will be developed substantially with AI coding assistants.

Design the engineering process around that reality.

Establish explicit responsibilities:

Claude Code

- Primary implementation agent.
- Repository exploration.
- Feature development.
- Architecture-aware coding.
- Documentation updates.
- Test execution.

Codex

- Independent code review.
- Architecture challenge.
- Security review.
- Test and implementation verification.
- Identification of unsupported claims and regressions.

ChatGPT

- Architecture planning and reasoning.
- Requirements clarification.
- Prompt and workflow design.
- Independent evaluation of proposed decisions and implementation results.

These are proposed workflow responsibilities, not a requirement to use only these tools. Preserve the ability to change providers and agents.

Define:

- How coding agents receive requirements.
- How they access authoritative architecture.
- How they identify permitted changes.
- How they avoid conflicting simultaneous modifications.
- How they handle untrusted repository content.
- How they protect secrets and credentials.
- How they execute tests.
- How they report failures.
- How independent review is performed.
- Who authorizes merges and releases.

No AI agent may approve its own consequential changes.

AI-generated code must not bypass normal security, testing, review, or authorization requirements.

7. Include Operational and Ownership Costs

Evaluate MIA as a system that must be operated for years, not merely compiled once.

Consider:

- Local hardware requirements.
- Electricity and cooling.
- Cloud inference costs.
- Model storage.
- Network and remote-access dependencies.
- Backup storage.
- Software licensing.
- Security maintenance.
- Distribution updates.
- Device replacement.
- Monitoring.
- Recovery procedures.
- Long-term maintainability.

Identify recurring costs separately from one-time development costs.

Do not assume unlimited cloud access, unlimited local compute, or permanent availability of any particular model provider.

Prioritize provider independence and the ability to operate essential functionality locally.

8. Define Real-World Acceptance Testing

Architecture diagrams and theoretical workflows are not sufficient proof of readiness.

Establish tests that demonstrate the system actually works.

At minimum, require:

- Clean development environment setup.
- Reproducible build from a clean checkout.
- Booting a test image in a virtual machine.
- MIA-first startup.
- Conventional desktop access.
- MIA Core failure and recovery.
- Local intelligence operation without internet.
- Cloud-provider unavailability.
- Permission enforcement.
- Application installation and removal.
- Update failure and rollback.
- Backup and restoration.
- Device disconnection and reconnection.
- Android integration.
- Hardware compatibility checks.
- Security testing.
- Performance testing.

Distinguish tests that can be performed in virtual machines from those requiring actual hardware.

Do not declare a feature verified until its defined test has passed.

9. Establish Explicit User Approval Boundaries

Claude is responsible for technical recommendations, not unilateral ownership of the MIA vision.

Preserve the distinction between:

- Established user decisions.
- Technical decisions already approved.
- New technical recommendations.
- Decisions requiring user approval.
- Unresolved investigations.

Do not silently change established goals.

If a foundational decision appears technically impractical, present the evidence, alternatives, consequences, and recommendation for review.

Do not interpret a technically preferred alternative as automatically approved.

10. Perform a Final Skeptical Review

Before declaring Prompt 17 complete, conduct a final review using the following questions:

- Have we designed anything that does not need to exist?
- Are we duplicating functionality already available in Linux?
- Are we building custom infrastructure without sufficient justification?
- Are we making the initial release unnecessarily complicated?
- Can one developer realistically maintain this architecture?
- Can we reproduce a working build?
- Can we recover when MIA itself fails?
- Can we migrate existing MIA functionality without losing it?
- Can we operate without a cloud provider?
- Can we replace models without rebuilding MIA?
- Can we add applications and devices without redesigning the system?
- Can every consequential action be independently authorized?
- Can we prove that the implemented system satisfies its requirements?
- Can we explain exactly what should be built first?

If the answer to any important question is no, identify the problem and resolve it or record it as a blocker.

Final instruction

The goal is not to produce the largest possible collection of architecture documents.

The goal is to produce the smallest coherent, secure, extensible, and maintainable foundation capable of growing into the complete MIA vision.

Do not optimize the plan for impressive terminology, architectural complexity, or theoretical completeness.

Optimize it for successful implementation, everyday usefulness, reliability, user ownership, and long-term evolution.

The final recommendation must tell us not only what MIA OS should become, but exactly how to begin building it without damaging what we have already created.
