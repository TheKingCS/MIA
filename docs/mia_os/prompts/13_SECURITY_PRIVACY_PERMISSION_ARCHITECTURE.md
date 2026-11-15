PROMPT 13 — SECURITY, PRIVACY & PERMISSION ARCHITECTURE

Mission

Act as a principal cybersecurity architect, operating-system security engineer, privacy engineer, identity and access management architect, application security specialist, AI safety engineer, and distributed systems security researcher.

Your mission is to design the comprehensive security, privacy, identity, permission, authorization, and trust architecture for MIA OS.

Prompts 00–12 have established the overall MIA vision, existing project, feature ecosystem, application framework, system requirements, Linux foundation, hardware strategy, intelligence infrastructure, autonomy system, self-awareness, desktop experience, visual identity, and distributed device architecture.

Now establish how every part of that ecosystem is protected.

MIA will eventually have access to sensitive information and potentially significant control over the user's digital and physical environment.

It must be capable of being intelligent, proactive, persistent, and useful without becoming an unrestricted system administrator or an uncontrolled autonomous actor.

Security must be foundational to the architecture, not an additional feature added after implementation.

The objective is to make MIA powerful without making it dangerously permissive.

This is a planning, research, and architecture exercise only. Do not begin implementation.

---

1. Review Existing Architecture and Security Posture

Review Prompts 00–12 and inspect the existing MIA repository.

Audit the current implementation of:

- Authentication.
- User accounts.
- Session management.
- API authentication.
- Authorization.
- Device registration.
- Device pairing.
- Network communication.
- Tailscale integration.
- Local server access.
- Database permissions.
- Memory storage.
- File access.
- Application permissions.
- AI provider integrations.
- API keys and secrets.
- Environment variables.
- Logging.
- Data retention.
- Backups.
- Encryption.
- Android permissions.
- Browser permissions.
- Smart-home integrations.
- Embedded device integrations.
- Agent execution.
- Shell and command execution.
- File operations.
- Application installation.
- Updates.
- Remote access.
- Existing approval mechanisms.

Inspect source code, configuration, dependencies, documentation, tests, and actual permission boundaries.

Identify security assumptions that are not enforced by code.

Classify findings as:

- Verified secure control.
- Implemented but insufficiently tested.
- Partially implemented.
- Experimental.
- Documented only.
- Planned.
- Unverified.
- Vulnerable.
- Deprecated.
- Broken.

Do not treat documentation as proof that a security mechanism works.

For significant findings, identify the supporting source files, functions, configurations, or tests.

Do not expose secrets, credentials, private keys, tokens, or sensitive personal information in reports.

Preserve existing functionality and identify reusable security infrastructure.

---

2. Core Security Philosophy

Establish the foundational security principles.

2.1 User ownership and control

The user retains ultimate authority over personal data, device access, permissions, and consequential actions.

MIA must not silently expand its own privileges.

2.2 Least privilege

Every service, application, agent, device, model integration, and process receives only the permissions necessary for its responsibilities.

2.3 Explicit authorization

Intelligence is not authorization.

An AI model deciding that an action would be useful does not make that action permissible.

2.4 Separation of intelligence and execution

Preserve the architecture established in earlier prompts:

- Intelligence interprets and reasons.
- Agents plan and coordinate.
- Authorization evaluates permission.
- Deterministic services validate and execute.
- Security controls enforce boundaries.
- Audit systems record relevant activity.

AI-generated instructions must never bypass the authorization layer.

2.5 Defense in depth

No single security mechanism should be responsible for protecting the entire ecosystem.

Use layered controls so that failure in one area does not automatically compromise everything.

2.6 Privacy by design

Collect, retain, transmit, and expose only information necessary for an authorized purpose.

2.7 Secure degradation

If authentication, authorization, or a required security service becomes unavailable, sensitive operations must fail safely.

2.8 Verifiable security

Distinguish between intended security, implemented controls, tested controls, and independently verified controls.

---

3. Threat Modeling and Risk Assessment

Develop a comprehensive threat model.

Identify:

- Assets.
- Threat actors.
- Entry points.
- Trust boundaries.
- Attack surfaces.
- Vulnerabilities.
- Potential impact.
- Likelihood.
- Mitigations.
- Residual risk.

Consider threats involving:

- Physical device theft.
- Lost phones.
- Compromised computers.
- Malicious applications.
- Malicious plugins.
- Malicious AI outputs.
- Prompt injection.
- Indirect prompt injection.
- Compromised model providers.
- Malicious documents.
- Malicious websites.
- Untrusted files.
- Supply-chain compromise.
- Credential theft.
- API abuse.
- Network interception.
- Insider access.
- Unauthorized household users.
- Remote attackers.
- Compromised embedded devices.
- Rogue agents.
- Unauthorized privilege escalation.
- Data exfiltration.
- Destructive file operations.
- Unauthorized physical device control.

Include realistic attack scenarios.

For each major threat, explain:

1. Attack objective.
2. Required access.
3. Attack path.
4. Potential consequences.
5. Existing protections.
6. Proposed protections.
7. Detection mechanisms.
8. Recovery strategy.
9. Residual risk.

Prioritize risks using a consistent methodology.

Do not claim that any architecture can eliminate all risk.

Identify which threats require external infrastructure, operational procedures, or user behavior to mitigate.

---

4. Security Architecture and Trust Boundaries

Design the overall MIA security architecture.

Identify the security boundaries between:

- Linux kernel.
- Operating-system services.
- MIA Core.
- AI inference services.
- AI provider integrations.
- Memory services.
- Application framework.
- Native applications.
- Web applications.
- Plugins and extensions.
- Agents.
- Device runtimes.
- Android endpoints.
- Smart-glasses endpoints.
- Embedded controllers.
- Cloud services.
- External APIs.
- User accounts.

Define which components are trusted, conditionally trusted, or untrusted.

Establish how data and commands cross each boundary.

Evaluate:

- Process isolation.
- User separation.
- Service accounts.
- Sandboxing.
- Containers.
- Linux namespaces.
- Seccomp.
- AppArmor.
- SELinux.
- Capabilities.
- Systemd service restrictions.
- Filesystem permissions.
- Network isolation.

Determine which technologies are appropriate for each layer.

Do not assume containers alone provide sufficient isolation.

Identify where stronger isolation is necessary.

---

5. Identity and Authentication Architecture

Design a unified identity system.

Support:

- Primary user.
- Additional household users.
- Shared household devices.
- Personal devices.
- Service identities.
- Application identities.
- Agent identities.
- Device identities.
- External integrations.

Evaluate:

- Local authentication.
- Passwords.
- Passkeys.
- WebAuthn.
- Hardware security keys.
- Biometrics.
- Multi-factor authentication.
- Device certificates.
- Mutual TLS.
- Session tokens.
- Refresh tokens.
- Short-lived credentials.

Define authentication flows for:

1. Initial operating-system setup.
2. User login.
3. Device enrollment.
4. Device pairing.
5. Remote access.
6. Application access.
7. Agent execution.
8. Administrative operations.
9. Credential recovery.
10. Device replacement.

Biometrics should authenticate access through an appropriate trusted platform mechanism; do not treat biometric information as something MIA should collect or store unnecessarily.

Distinguish authentication from authorization.

A successfully authenticated user or device does not automatically have permission to perform every operation.

---

6. Authorization and Permission Architecture

This is one of the most important sections.

Design a centralized, enforceable authorization framework.

Evaluate:

- Role-based access control (RBAC).
- Attribute-based access control (ABAC).
- Capability-based security.
- Policy-based authorization.
- Contextual authorization.
- Explicit consent.

Determine whether a hybrid approach is appropriate.

Define permissions across:

- Users.
- Applications.
- Services.
- Agents.
- Devices.
- Data categories.
- Files.
- APIs.
- Physical systems.
- Administrative operations.

Create a consistent permission vocabulary.

At minimum, investigate:

- Discover.
- View.
- Read.
- Create.
- Modify.
- Delete.
- Execute.
- Share.
- Export.
- Install.
- Configure.
- Administer.
- Delegate.
- Approve.
- Revoke.

Define permission inheritance and prevent accidental privilege expansion.

Establish how permissions are granted, inspected, modified, expired, and revoked.

A permission should have:

- Identity of the principal.
- Target resource.
- Permitted operation.
- Scope.
- Conditions.
- Duration.
- Granting authority.
- Audit information.
- Revocation state.

Define how MIA checks authorization immediately before execution rather than relying on an old approval or cached assumption.

---

7. Action Risk Classification and Approval Framework

Develop a formal action-risk classification system.

MIA must distinguish between harmless actions and actions that can have significant consequences.

Establish risk categories such as:

- Informational.
- Read-only.
- Reversible low-impact.
- Sensitive.
- Consequential.
- Irreversible or safety-critical.

Define examples for each category.

Consider:

- Opening applications.
- Searching files.
- Reading documents.
- Creating drafts.
- Editing files.
- Sending messages.
- Publishing information.
- Purchasing goods.
- Transferring money.
- Modifying system settings.
- Installing software.
- Running shell commands.
- Deleting data.
- Changing user permissions.
- Unlocking doors.
- Operating machinery.
- Changing greenhouse conditions.
- Controlling irrigation or electrical equipment.

For each category, define:

- Whether execution can be automatic.
- Whether prior standing authorization is acceptable.
- Whether immediate confirmation is required.
- Whether stronger authentication is necessary.
- Whether the action must be prohibited.
- Whether execution must be limited by deterministic safety rules.

Approval must be meaningful and specific.

A vague approval such as "take care of everything" must not silently authorize unrelated high-impact actions.

---

8. Approval, Consent and Delegated Authority

Design the approval infrastructure.

Define:

- Approval requests.
- Approval interfaces.
- Approval expiration.
- Approval scope.
- Approval identity.
- Approval context.
- Revocation.
- Reauthentication.
- Standing permissions.
- Delegated permissions.
- Emergency restrictions.

An approval should clearly communicate:

- What MIA intends to do.
- Which resources will be affected.
- Why the action is needed.
- What consequences are expected.
- Whether the action is reversible.
- Which permissions are being used.
- Whether external systems are involved.

Investigate how approval works across devices.

For example, MIA may prepare an operation on the PC but request confirmation through the phone.

Establish how the system verifies that the approval is genuine and applies only to the intended operation.

Prevent:

- Approval replay.
- Approval reuse.
- Approval substitution.
- Approval expiration bypass.
- Unauthorized delegation.
- Scope expansion after approval.

Define which actions require stronger confirmation or cannot be delegated.

---

9. AI-Specific Security and Prompt Injection Defense

Design security controls specifically for AI systems.

Investigate:

- Direct prompt injection.
- Indirect prompt injection.
- Malicious web content.
- Malicious documents.
- Malicious tool outputs.
- Instruction hierarchy.
- Context contamination.
- Memory poisoning.
- Retrieval poisoning.
- Data exfiltration.
- Tool misuse.
- Unauthorized command generation.
- Agent manipulation.
- Multi-agent trust failures.

Treat external content as data, not as trusted instructions.

An email, webpage, document, image, or tool result must not acquire authority merely because an AI model reads it.

Define how the system distinguishes:

- User instructions.
- System policies.
- Developer-defined constraints.
- Trusted configuration.
- Untrusted external content.
- Model-generated suggestions.

Establish security validation between AI reasoning and deterministic execution.

AI-generated commands must be:

1. Parsed.
2. Validated.
3. Checked against policy.
4. Authorized.
5. Restricted to approved interfaces.
6. Executed through controlled services.
7. Audited.

Do not allow models to bypass controls by generating alternate shell commands, invoking unapproved tools, or communicating directly with privileged services.

Investigate independent validation and review mechanisms for high-risk operations.

Define how MIA detects uncertainty and refuses unsafe operations.

---

10. Agent and Autonomous Execution Security

Integrate Prompt 08's agent architecture.

Every agent must have an explicit identity, scope, and permission boundary.

Define:

- Agent identity.
- Agent authentication.
- Tool permissions.
- Resource permissions.
- Delegation.
- Execution limits.
- Task expiration.
- Isolation.
- Audit.
- Revocation.
- Failure handling.

Agents must not inherit unrestricted permissions from MIA Core.

Determine how agents request additional permissions.

Prevent privilege escalation through:

- Agent-to-agent delegation.
- Nested workflows.
- Tool chaining.
- Model-generated instructions.
- Cross-device execution.
- Persistent background jobs.

Define how authorization is preserved throughout long-running tasks.

If a user's permission is revoked while a task is running, determine whether the task must stop, pause, or safely complete.

---

11. Operating System and Privilege Security

Design Linux-level security.

Evaluate:

- Root account handling.
- Privilege separation.
- sudo and polkit.
- systemd service users.
- Linux capabilities.
- Namespaces.
- Seccomp.
- AppArmor.
- SELinux.
- Filesystem permissions.
- Mount restrictions.
- Secure boot.
- Kernel updates.
- Module signing.
- Process isolation.
- Resource limits.

MIA must not run as root simply because it is the central assistant.

Identify the minimum privileges needed by each service.

Define how privileged system operations are performed through narrow, controlled interfaces.

Separate:

- Ordinary user operations.
- MIA service operations.
- Administrative operations.
- Operating-system maintenance.
- Hardware control.

Ensure AI models cannot directly acquire operating-system privileges.

---

12. Application, Plugin and Extension Security

Integrate Prompt 03's application framework.

Design a permission and isolation model for:

- Native applications.
- Web applications.
- Plugins.
- Extensions.
- Third-party integrations.
- Background services.
- Downloaded applications.
- User-created automations.

Investigate:

- Sandboxing.
- Application signing.
- Package provenance.
- Dependency verification.
- Permissions manifests.
- Runtime isolation.
- Network access restrictions.
- File access restrictions.
- Update integrity.
- Extension review.
- Revocation.

Define how applications request access to:

- Camera.
- Microphone.
- Location.
- Contacts.
- Files.
- Calendar.
- Memory.
- Network.
- Home devices.
- External accounts.

Prevent applications from obtaining permissions simply because MIA itself has access.

MIA should not act as an unrestricted permission broker for untrusted applications.

---

13. Distributed Device Security

Integrate Prompt 12.

Design security across the device ecosystem.

Address:

- Device enrollment.
- Device certificates.
- Secure pairing.
- Mutual authentication.
- Device trust.
- Secure communication.
- Key rotation.
- Remote access.
- Device revocation.
- Lost-device handling.
- Device replacement.
- Offline authorization.
- Stale credentials.
- Compromised endpoints.

A device must not gain access to every MIA resource merely by joining the local network.

Establish distinct trust levels for:

- Primary workstation.
- Personal phone.
- Smart glasses.
- Household displays.
- Embedded controllers.
- Guest devices.
- External cloud services.

Define how authorization behaves when devices are offline.

Ensure stale permissions cannot persist indefinitely without appropriate expiration or revalidation.

---

14. Data Classification and Privacy Architecture

Create a comprehensive data classification system.

Consider categories such as:

- Public.
- General personal.
- Private.
- Sensitive.
- Highly sensitive.
- Restricted system data.
- Security credentials.

Define how these categories apply to:

- Conversations.
- Memory.
- Files.
- Photos.
- Audio.
- Video.
- Location.
- Financial records.
- Health-related records.
- Communications.
- Credentials.
- Device telemetry.
- Household information.
- Business information.
- AI model inputs and outputs.

Determine which data can be:

- Stored locally.
- Replicated to trusted devices.
- Sent to cloud providers.
- Included in model context.
- Logged.
- Backed up.
- Exported.
- Shared with other users.

Use data minimization.

Do not collect information merely because it might become useful later.

Establish clear rules for sensitive data access and disclosure.

---

15. Memory Privacy, Ownership and User Control

Integrate Prompt 07's memory architecture.

Design privacy controls for every memory category.

The user must be able to understand:

- What MIA remembers.
- Where information is stored.
- Why it was stored.
- Which devices have copies.
- Which applications can access it.
- Whether it was shared with an external model provider.
- How it can be corrected.
- How it can be exported.
- How it can be deleted.

Define:

- Memory access policies.
- Memory provenance.
- Retention.
- Expiration.
- Correction.
- Deletion.
- Replication.
- Encryption.
- Backup behavior.
- Shared memory boundaries.

Distinguish between deleting a memory record and deleting every replica or derived copy.

Define how deletions propagate across devices and backups.

Establish reasonable policies for information that cannot be immediately removed from immutable backups or third-party systems.

Prevent unauthorized memory access through prompt injection, tool misuse, or overly broad context assembly.

---

16. Encryption and Cryptographic Architecture

Develop an encryption strategy.

Evaluate:

- Encryption at rest.
- Encryption in transit.
- End-to-end encryption where appropriate.
- Database encryption.
- Filesystem encryption.
- Device encryption.
- Key derivation.
- Key storage.
- Key rotation.
- Certificate management.
- Recovery keys.
- Hardware-backed security.

Consider established cryptographic standards and maintained implementations.

Do not invent cryptographic algorithms.

Define which components own encryption and key management responsibilities.

Establish how encryption works across:

- PC.
- Android.
- Smart glasses.
- Embedded devices.
- Local networks.
- Remote connections.
- Backups.
- Cloud services.

Determine which information must remain inaccessible to external model providers.

Identify tradeoffs between end-to-end encryption, server-side processing, search, and synchronization.

---

17. Secrets, Credentials and External Integrations

Design secure secrets management.

Protect:

- AI provider API keys.
- Database credentials.
- OAuth tokens.
- Refresh tokens.
- Device certificates.
- Private keys.
- Service credentials.
- Home automation tokens.
- External application credentials.

Evaluate appropriate secure storage mechanisms for Linux and Android.

Define:

- Secret creation.
- Storage.
- Access.
- Rotation.
- Revocation.
- Expiration.
- Recovery.
- Audit.
- Environment isolation.

Secrets must not appear in:

- Source code.
- Git history.
- Logs.
- Model prompts unnecessarily.
- Error messages.
- Diagnostic exports.
- Screenshots.
- Public documentation.

Define how external integrations obtain only the credentials they require.

---

18. Voice, Camera, Sensors and Physical Privacy

MIA will eventually operate through microphones, cameras, displays, and environmental sensors.

Design privacy controls for these capabilities.

Investigate:

- Microphone activation.
- Camera activation.
- Recording.
- Audio processing.
- Video processing.
- Sensor access.
- Location access.
- Ambient monitoring.
- Wake-word detection.
- Continuous conversation.
- Local processing.
- Cloud processing.

Establish visible and understandable sensor states.

Users must be able to tell when a device is:

- Not listening.
- Listening locally.
- Recording.
- Processing audio.
- Streaming audio.
- Using a camera.
- Transmitting sensor data.
- Muted.
- Unavailable.

Define physical privacy controls where appropriate.

Determine how permissions differ between personal devices and shared household devices.

Avoid recording or transmitting bystanders' information without appropriate safeguards.

---

19. Household Users and Shared Privacy

Integrate the multi-user requirements from earlier prompts.

Design privacy and authorization for shared environments.

Distinguish:

- Personal accounts.
- Shared household accounts or spaces.
- Shared devices.
- Personal devices.
- Private conversations.
- Shared calendars.
- Shared tasks.
- Shared home information.
- Personal memories.
- Household memories.

Define how one household member's private information is protected from another.

A shared dashboard must not automatically expose every user's private information.

Establish ownership, consent, access, and revocation rules.

Consider guest access and temporary household permissions.

---

20. Physical Device and Smart-Home Safety

Give special attention to physical-world operations.

MIA may eventually coordinate:

- Door locks.
- Cameras.
- Lighting.
- Heating.
- Cooling.
- Electrical devices.
- Irrigation.
- Pumps.
- Aquaponics.
- Greenhouse ventilation.
- Motors.
- Relays.
- Agricultural equipment.

Define safety boundaries.

Investigate:

- Deterministic control.
- Hardware interlocks.
- Safe operating ranges.
- Emergency stop mechanisms.
- Fail-safe defaults.
- Sensor validation.
- Actuator feedback.
- Rate limits.
- Command expiration.
- Manual override.
- Loss-of-network behavior.

AI must never be the sole safety mechanism for hazardous physical operations.

For safety-critical equipment, deterministic controllers and hardware-level protections must remain authoritative.

Define which operations MIA may observe, recommend, prepare, or execute.

---

21. Secure Logging, Auditing and Accountability

Design a comprehensive security audit architecture.

Record relevant events such as:

- Authentication.
- Failed authentication.
- Permission grants.
- Permission changes.
- Permission revocation.
- Approval requests.
- Approval decisions.
- Sensitive data access.
- External data transmission.
- Device enrollment.
- Device revocation.
- Agent execution.
- Privileged operations.
- Application installation.
- Configuration changes.
- Physical device commands.
- Security incidents.

Define:

- Event schemas.
- Timestamps.
- Actor identity.
- Target resource.
- Action.
- Authorization decision.
- Approval reference.
- Result.
- Correlation ID.
- Retention.
- Integrity protection.

Logs must not unnecessarily contain secrets or sensitive content.

Determine how logs are protected against unauthorized modification or deletion.

The user should be able to inspect important actions performed by MIA.

---

22. Security Monitoring, Detection and Incident Response

Design security monitoring.

Investigate:

- Suspicious logins.
- Unusual device behavior.
- Unexpected permission changes.
- Repeated authentication failures.
- Unexpected outbound connections.
- Abnormal data access.
- Privilege escalation.
- Compromised credentials.
- Agent behavior anomalies.
- Unusual physical device commands.

Define alert severity and response procedures.

Establish incident response stages:

1. Detection.
2. Classification.
3. Containment.
4. Investigation.
5. Recovery.
6. Credential rotation.
7. Validation.
8. Post-incident review.

Determine which responses can be automatic and which require user authorization.

Automatic containment may include temporarily isolating a suspicious endpoint, but destructive or irreversible remediation must be carefully controlled.

---

23. Secure Updates and Software Supply Chain

Design security requirements for the software supply chain.

Investigate:

- Secure boot.
- Signed packages.
- Package provenance.
- Dependency integrity.
- Build provenance.
- Software bills of materials.
- Vulnerability scanning.
- Code signing.
- Update verification.
- Rollback protection.
- Repository security.
- Third-party components.

Determine how MIA verifies that software and updates come from trusted sources.

Address the risks of:

- Compromised dependencies.
- Malicious packages.
- Compromised build systems.
- Malicious updates.
- Stale vulnerabilities.
- Unverified AI-generated code.

Coordinate detailed update and recovery implementation with Prompts 14 and 15.

---

24. Backup, Recovery and Data Protection

Establish security requirements for backups and recovery.

Investigate:

- Backup encryption.
- Backup authentication.
- Access restrictions.
- Recovery credentials.
- Backup integrity.
- Retention.
- Restore verification.
- Device replacement.
- Disaster recovery.
- Ransomware resistance.

Define how backups preserve user ownership and privacy.

Prevent compromised devices from silently overwriting trusted backups.

Distinguish between backup availability and authorization to restore data.

Coordinate detailed backup and recovery design with Prompt 14.

---

25. Security Testing and Verification

Establish a comprehensive security testing strategy.

Include:

- Threat-model reviews.
- Static analysis.
- Dependency scanning.
- Dynamic analysis.
- Penetration testing.
- API security testing.
- Authentication testing.
- Authorization testing.
- Privilege escalation testing.
- Sandbox escape testing.
- Prompt injection testing.
- Agent abuse testing.
- Data leakage testing.
- Device security testing.
- Network security testing.
- Synchronization security testing.
- Recovery testing.
- Hardware integration testing.

Develop adversarial test scenarios.

Test that:

- Agents cannot exceed permissions.
- AI outputs cannot bypass authorization.
- Untrusted documents cannot issue system instructions.
- Applications cannot access unauthorized files.
- Compromised devices can be revoked.
- Stale approvals cannot be reused.
- Sensitive information is not unintentionally sent to cloud models.
- Physical controls remain protected during network failures.

Define severity classifications and release-blocking vulnerabilities.

Do not claim security has been verified merely because tests pass.

---

26. Security Technology Evaluation

Evaluate appropriate technologies and standards.

Consider:

- Linux security mechanisms.
- AppArmor.
- SELinux.
- systemd sandboxing.
- Seccomp.
- Polkit.
- PAM.
- WebAuthn.
- Passkeys.
- Mutual TLS.
- OAuth 2.0.
- OpenID Connect.
- Hardware-backed key storage.
- TPM 2.0.
- Android Keystore.
- Full-disk encryption.
- Vault-style secrets management.
- Open Policy Agent.
- Cedar.
- SELinux policy tooling.
- Software bills of materials.
- Sigstore.
- SLSA.
- OpenTelemetry security practices.

These are research candidates, not predetermined requirements.

For each recommendation, document:

1. Purpose.
2. Architecture layer.
3. Alternatives.
4. Compatibility.
5. Advantages.
6. Limitations.
7. Operational complexity.
8. Security implications.
9. Maintenance requirements.
10. Recommendation.
11. Supporting evidence.

Prefer established, maintained, well-documented standards and implementations.

Do not introduce excessive security infrastructure that the initial MIA deployment cannot reasonably maintain.

---

27. Required Security Architecture Diagrams

Produce diagrams showing:

1. Complete MIA security architecture.
2. System trust boundaries.
3. Identity and authentication.
4. Authorization evaluation.
5. Permission lifecycle.
6. Action-risk and approval flow.
7. AI prompt injection defense.
8. Agent security and delegation.
9. Linux privilege separation.
10. Application sandboxing.
11. Distributed device trust.
12. Data classification and privacy.
13. Memory privacy and deletion.
14. Encryption and key management.
15. Secrets management.
16. Sensor and physical privacy.
17. Household user separation.
18. Physical-device safety boundaries.
19. Security audit and monitoring.
20. Incident response.
21. Secure software supply chain.
22. Backup security.
23. End-to-end authorized operation.

Explain each diagram and identify the security controls enforced at every boundary.

---

28. Required End-to-End Security Scenarios

Analyze at least these scenarios.

Scenario A — Malicious Webpage

MIA reads a webpage containing instructions attempting to extract private memory or execute commands.

Explain how the content is isolated and prevented from gaining authority.

Scenario B — Malicious Document

A document contains embedded instructions attempting to manipulate an agent.

Explain how ingestion, context handling, and tool execution remain protected.

Scenario C — Unauthorized File Access

An application requests access to private user files.

Show permission evaluation, denial, and audit behavior.

Scenario D — High-Impact Operation

MIA prepares a financial, communication, or system-changing action.

Show risk classification, approval, authorization, execution, and auditing.

Scenario E — Lost Phone

The user's phone is stolen.

Show device revocation, credential protection, remote access restrictions, and recovery.

Scenario F — Compromised Embedded Device

A greenhouse controller becomes compromised.

Show isolation and prevention of access to unrelated MIA resources.

Scenario G — Agent Privilege Escalation

One agent attempts to delegate a task to another agent with greater privileges.

Show how authorization prevents privilege escalation.

Scenario H — Cloud Model Privacy

MIA needs a cloud model for a task involving sensitive information.

Show data classification, minimization, routing policy, and user consent requirements.

Scenario I — Shared Household Device

One household member attempts to access another person's private conversation through a shared dashboard.

Show identity and data separation.

Scenario J — Physical Safety

MIA receives an unsafe greenhouse or equipment command.

Show deterministic validation, hardware interlocks, rejection, and audit.

Scenario K — Approval Replay

An old approval is reused to authorize a different operation.

Show how the system prevents it.

Scenario L — Security Service Failure

The authorization service becomes unavailable while MIA is attempting a sensitive operation.

Show fail-safe behavior.

For each scenario, identify:

- Threat.
- Attack path.
- Trust boundaries.
- Controls.
- Expected behavior.
- Audit events.
- Recovery.
- Residual risk.

---

29. Required Deliverables

Create:

1. "MIA_OS_SECURITY_ARCHITECTURE.md"
2. "MIA_OS_THREAT_MODEL.md"
3. "MIA_OS_SECURITY_TRUST_BOUNDARIES.md"
4. "MIA_OS_IDENTITY_AND_AUTHENTICATION.md"
5. "MIA_OS_AUTHORIZATION_AND_PERMISSION_FRAMEWORK.md"
6. "MIA_OS_ACTION_RISK_AND_APPROVAL_FRAMEWORK.md"
7. "MIA_OS_CONSENT_AND_DELEGATED_AUTHORITY.md"
8. "MIA_OS_AI_SECURITY_AND_PROMPT_INJECTION_DEFENSE.md"
9. "MIA_OS_AGENT_SECURITY_AND_EXECUTION_BOUNDARIES.md"
10. "MIA_OS_LINUX_PRIVILEGE_AND_SYSTEM_SECURITY.md"
11. "MIA_OS_APPLICATION_AND_PLUGIN_SECURITY.md"
12. "MIA_OS_DISTRIBUTED_DEVICE_SECURITY.md"
13. "MIA_OS_DATA_CLASSIFICATION_AND_PRIVACY.md"
14. "MIA_OS_MEMORY_PRIVACY_AND_USER_CONTROL.md"
15. "MIA_OS_ENCRYPTION_AND_KEY_MANAGEMENT.md"
16. "MIA_OS_SECRETS_AND_CREDENTIAL_MANAGEMENT.md"
17. "MIA_OS_SENSOR_AND_PHYSICAL_PRIVACY.md"
18. "MIA_OS_HOUSEHOLD_PRIVACY_AND_ACCESS_CONTROL.md"
19. "MIA_OS_PHYSICAL_DEVICE_SAFETY_ARCHITECTURE.md"
20. "MIA_OS_SECURITY_AUDIT_AND_ACCOUNTABILITY.md"
21. "MIA_OS_SECURITY_MONITORING_AND_INCIDENT_RESPONSE.md"
22. "MIA_OS_SECURE_SUPPLY_CHAIN_REQUIREMENTS.md"
23. "MIA_OS_BACKUP_AND_DATA_PROTECTION_REQUIREMENTS.md"
24. "MIA_OS_SECURITY_TESTING_AND_VERIFICATION.md"
25. "MIA_OS_SECURITY_TECHNOLOGY_EVALUATION.md"
26. "MIA_OS_SECURITY_ARCHITECTURE_DIAGRAMS.md"
27. "MIA_OS_SECURITY_SCENARIO_ANALYSIS.md"
28. "MIA_OS_SECURITY_ACCEPTANCE_CRITERIA.md"
29. "MIA_OS_SECURITY_OPEN_QUESTIONS.md"
30. "MIA_OS_SECURITY_RISK_REGISTER.md"

Also update:

- "MIA_OS_MASTER_PLAN.md"
- "MIA_OS_DECISION_LOG.md"
- "MIA_OS_OPEN_QUESTIONS.md"
- "MIA_OS_RISK_REGISTER.md"
- "MIA_OS_REQUIREMENTS_TRACEABILITY.md"
- "MIA_OS_IMPLEMENTATION_STATUS.md"
- "MIA_OS_CORE_ARCHITECTURE.md"
- "MIA_OS_INTELLIGENCE_ARCHITECTURE.md"
- "MIA_OS_AUTONOMY_AND_AGENT_ARCHITECTURE.md"
- "MIA_OS_SELF_AWARENESS_ARCHITECTURE.md"
- "MIA_OS_DISTRIBUTED_ARCHITECTURE.md"
- "MIA_OS_MEMORY_INFRASTRUCTURE.md"
- "MIA_OS_APPLICATION_FRAMEWORK.md"
- "MIA_OS_DEVICE_CAPABILITY_MATRIX.md"

Maintain consistency with Prompts 00–12.

---

30. Formal Decisions and Traceability

Create formal architecture decision records for major security decisions.

Each decision must include:

- Decision ID.
- Decision title.
- Context.
- Security requirements affected.
- Threats addressed.
- Options evaluated.
- Evidence.
- Selected approach.
- Alternatives rejected.
- Consequences.
- Risks.
- Reversibility.
- Conditions for reconsideration.

Maintain traceability between security controls and:

- System requirements.
- Linux architecture.
- Applications.
- Intelligence infrastructure.
- Memory.
- Agents.
- Devices.
- Communication.
- Synchronization.
- Physical systems.
- User experiences.
- Testing requirements.

Clearly identify decisions requiring user approval.

Distinguish mandatory security requirements from recommendations and optional enhancements.

---

31. Acceptance Criteria

Prompt 13 is complete only when:

- The existing security posture has been audited.
- A comprehensive threat model exists.
- Trust boundaries are defined.
- Identity and authentication architecture is established.
- Authorization is separate from AI reasoning.
- A centralized permission framework is specified.
- Action-risk categories are defined.
- Approval and consent workflows are designed.
- AI-specific attacks are addressed.
- Agent privileges and delegation are controlled.
- Linux privilege boundaries are defined.
- Application and plugin isolation is specified.
- Distributed device security is established.
- Data classification and privacy rules are documented.
- Memory ownership and deletion requirements are defined.
- Encryption and key management are specified.
- Secrets management is addressed.
- Sensor and physical privacy are covered.
- Household privacy boundaries are defined.
- Physical device safety architecture is established.
- Audit and incident response are designed.
- Software supply-chain security is addressed.
- Backup security requirements are established.
- Security testing requirements are defined.
- End-to-end attack scenarios are analyzed.
- Major technology decisions have supporting evidence.
- Diagrams and deliverables are complete.
- Risks and open questions are documented.
- Requirements are traceable.
- The architecture remains consistent with Prompts 00–12.

---

32. Boundaries With Future Prompts

Do not duplicate the detailed scope of later prompts.

- Prompt 14 establishes boot, recovery, updates, and reliability.
- Prompt 15 establishes development environment, build infrastructure, CI/CD, and release engineering.
- Prompt 16 establishes implementation phases, sequencing, and migration.
- Prompt 17 consolidates the complete plan and performs independent technical review.

This prompt defines the security requirements and architecture those later systems must satisfy.

Coordinate with them rather than independently designing duplicate infrastructure.

---

33. Planning Restrictions

This is a research, security audit, and architecture planning exercise.

Do not:

- Implement security controls.
- Modify authentication systems.
- Rotate existing credentials.
- Change firewall rules.
- Change network configuration.
- Install security software.
- Change user permissions.
- Modify operating-system security settings.
- Replace existing encryption.
- Change database access.
- Revoke devices.
- Deploy new security infrastructure.
- Perform destructive penetration tests.
- Attempt unauthorized access to external systems.

Non-destructive inspection and authorized testing of the existing development environment are permitted.

Never reproduce secrets or sensitive personal data in documentation.

Preserve existing functionality.

Do not claim that a security control is implemented or effective without evidence.

---

34. Final Objective

The final architecture must establish a security model that allows MIA to become increasingly capable without becoming increasingly dangerous.

The user must retain control over:

- Personal information.
- Memory.
- Files.
- Applications.
- Devices.
- External accounts.
- Permissions.
- Financial operations.
- Communications.
- System administration.
- Physical equipment.
- Delegated actions.

MIA should be able to operate proactively within explicitly established boundaries.

It should understand its permissions, explain why an operation is allowed or denied, request approval when necessary, and provide an auditable record of consequential activity.

Security must be enforced independently of model behavior.

No AI model, agent, application, plugin, or device should be able to bypass the authorization architecture through alternate execution paths.

Produce a comprehensive, technically rigorous, evidence-based security and privacy architecture.

When finished, summarize:

1. The recommended security architecture.
2. The identity and authentication model.
3. The authorization and permission model.
4. The action-risk and approval framework.
5. AI-specific security protections.
6. Agent and delegated execution boundaries.
7. Linux and application isolation.
8. Distributed device security.
9. Data classification and privacy.
10. Memory ownership and user control.
11. Encryption and secrets management.
12. Sensor and physical privacy.
13. Household privacy.
14. Physical-device safety.
15. Audit, monitoring, and incident response.
16. The most significant security risks.
17. Decisions requiring user approval.
18. Questions that must be resolved before Prompt 14.

Stop after completing Prompt 13. Wait for review and approval before beginning Prompt 14.
