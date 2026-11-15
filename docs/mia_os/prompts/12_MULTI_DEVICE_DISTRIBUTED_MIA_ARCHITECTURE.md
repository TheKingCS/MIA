PROMPT 12 — MULTI-DEVICE & DISTRIBUTED MIA ARCHITECTURE

Mission

Act as a principal distributed systems architect, edge computing engineer, cross-platform systems architect, device integration specialist, synchronization engineer, and AI infrastructure architect.

Your mission is to design the complete multi-device and distributed architecture for MIA.

Prompts 00–11 have established the MIA OS vision, existing ecosystem, application framework, operating system architecture, hardware strategy, intelligence infrastructure, autonomy system, self-awareness architecture, desktop experience, and visual identity.

Now determine how all of these capabilities operate as one coherent system across multiple devices, operating environments, networks, and hardware classes.

MIA must not become a collection of unrelated applications that happen to share a name.

The user should experience one persistent MIA identity across devices, with continuity of relevant context, memory, conversations, projects, applications, capabilities, and authorized activities.

However, this does not mean every device must run identical software or possess identical capabilities.

A desktop, Android phone, smart-glasses endpoint, Raspberry Pi, and future wearable may have fundamentally different responsibilities.

Design an architecture that allows them to cooperate while respecting their hardware limitations, operating environments, security boundaries, and network conditions.

Planning, architecture research, and technical evaluation only. Do not begin implementation.

---

1. Review Previous Architecture and Existing Device Ecosystem

Review Prompts 00–11 and inspect the existing MIA repository.

Audit the actual current implementation of:

- PC and desktop components.
- Web application.
- Android application.
- Local MIA server.
- Network communication.
- Tailscale integration.
- Voice interaction.
- Model inference endpoints.
- Memory services.
- Database architecture.
- Smart-glasses interface.
- Device discovery.
- Home automation.
- Raspberry Pi integrations.
- Embedded hardware integrations.
- Existing APIs.
- Authentication.
- Synchronization.
- Background services.
- Existing device registration mechanisms.

Historical project context includes:

- A PC-centered development environment.
- An Android application with hold-to-talk functionality.
- A local MIA server historically using port 8765.
- Tailscale connectivity.
- Local model inference using Ollama.
- Vosk and Piper voice components.
- Smart-glasses interface concepts.
- Raspberry Pi 5 and AI HAT+ 2 experimentation.
- Future wearable and spatial interface concepts.
- Zeta Astralis, a proposed forearm-worn MIA endpoint.

These are historical reference points, not verified current implementation facts.

Inspect the repository and establish what actually exists.

Classify each capability as:

- Verified operational.
- Implemented but not fully tested.
- Partially implemented.
- Experimental.
- Documented only.
- Planned.
- Proposed.
- Unverified.
- Deprecated.
- Broken.

Identify reusable infrastructure, missing components, architectural limitations, and migration requirements.

Do not rebuild functioning components without a documented technical justification.

---

2. Core Multi-Device Philosophy

Establish the foundational principles.

2.1 One MIA identity

MIA must retain a consistent identity across devices.

The following should not become independent copies:

- MIA identity.
- User preferences.
- Personality.
- Memory architecture.
- Intelligence infrastructure.
- Authorized capabilities.
- Project context.
- Relevant conversation history.
- Mission and workflow state.

Devices may maintain local caches and device-specific state, but they must participate in a coherent overall system.

2.2 Different devices, different responsibilities

Not every device needs the same runtime or software stack.

A device should only host the services and capabilities appropriate to its hardware and operating environment.

2.3 Local-first operation

Devices should remain useful when internet connectivity is unavailable.

Determine which capabilities can operate:

- Entirely locally.
- Through a local network.
- Through another trusted MIA device.
- Through a cloud provider.
- In degraded offline mode.

2.4 Intelligent distribution

MIA should coordinate computing resources across available devices.

For example:

- A workstation handles demanding inference.
- A phone provides portable interaction and local processing.
- Smart glasses provide visual and audio interaction.
- A Raspberry Pi operates home or greenhouse services.
- Embedded controllers execute deterministic hardware operations.

These are possible deployment patterns, not fixed assumptions.

2.5 Device independence

Losing one device must not destroy MIA's identity, memory, or essential capabilities.

The architecture must support device replacement, recovery, migration, and secure revocation.

---

3. Unified MIA Distributed Architecture

Design the complete distributed system.

Identify the responsibilities and boundaries of:

1. MIA Core.
2. Device runtimes.
3. Intelligence infrastructure.
4. Memory infrastructure.
5. Synchronization services.
6. Communication services.
7. Device registry.
8. Identity and authentication.
9. Capability registry.
10. Task and workflow coordination.
11. Event infrastructure.
12. Local execution services.
13. Remote execution services.
14. Cloud integrations.
15. Security and authorization.
16. Observability and health monitoring.

Determine which services should be:

- Centralized.
- Distributed.
- Replicated.
- Device-local.
- Cloud-hosted.
- Dynamically assigned.

Avoid assuming that every device must connect to one permanently running central server.

Evaluate hub-and-spoke, peer-to-peer, federated, and hybrid distributed architectures.

Explain the tradeoffs in:

- Reliability.
- Latency.
- Security.
- Synchronization.
- Maintenance.
- Offline operation.
- Resource consumption.
- Complexity.

Recommend an architecture appropriate for MIA's current scale that can grow without requiring a complete redesign.

---

4. Device Classes and Runtime Architecture

Define a device classification system.

At minimum, investigate:

4.1 Primary PC and Workstation

The primary full MIA OS environment.

Responsibilities may include:

- Full MIA desktop.
- Core system services.
- Local model inference.
- Memory services.
- Development environment.
- Multi-model council.
- Agent orchestration.
- Storage.
- Application hosting.
- Device coordination.

Determine which services should run locally and which can move to other devices.

4.2 Android Phone

The portable MIA endpoint.

Responsibilities may include:

- Conversational interaction.
- Voice input and output.
- Notifications.
- Camera.
- Sensor integration.
- Portable applications.
- Device control.
- Local memory cache.
- Offline interaction.
- Remote access to trusted computing resources.

Determine Android-specific constraints involving:

- Background execution.
- Battery optimization.
- Permissions.
- Local storage.
- Network access.
- Audio.
- Camera.
- Notifications.
- Process lifecycle.
- App standby.

Do not assume an Android application can operate like an unrestricted Linux background service.

4.3 Smart Glasses

A lightweight visual and audio endpoint.

Responsibilities may include:

- MIA presence.
- Voice interaction.
- Notifications.
- Contextual information.
- Short-form responses.
- Camera input where supported.
- Navigation.
- Spatial interaction where supported.

Investigate actual hardware and SDK capabilities.

Do not assume unrestricted display access, camera access, background operation, or third-party application control.

4.4 Raspberry Pi and Home Computing Nodes

Investigate Raspberry Pi and comparable hardware.

Potential responsibilities include:

- Local MIA endpoints.
- Home automation.
- Greenhouse monitoring.
- Environmental sensors.
- Local databases.
- Voice endpoints.
- Camera monitoring.
- Local networking.
- Lightweight model inference.
- Device coordination.

Evaluate Raspberry Pi 5 and AI HAT+ 2 alongside alternatives such as NVIDIA Jetson and other appropriate edge platforms.

Verify real capabilities rather than relying on advertised AI TOPS alone.

4.5 Embedded Controllers

Investigate ESP32, Arduino-class hardware, microcontrollers, and industrial controllers.

Establish which operations belong on deterministic embedded controllers rather than an AI runtime.

Examples include:

- Sensor collection.
- Relay control.
- Environmental monitoring.
- Motor control.
- Irrigation.
- Lighting.
- Temperature control.
- Safety interlocks.

AI may recommend or coordinate actions, but safety-critical control must remain deterministic and appropriately protected.

4.6 Future Wearables and Spatial Devices

Consider:

- Smartwatches.
- AR displays.
- Spatial computing headsets.
- Zeta Astralis.
- Future wearable computing devices.
- Future neural interfaces.

Classify these as current, technically feasible future, speculative, or dependent on hardware that does not yet exist.

Do not let speculative hardware dictate the present architecture.

---

5. Device Runtime and MIA Endpoint Architecture

Design a reusable MIA device runtime.

Determine what common functionality each supported device should implement.

Consider:

- Device identity.
- Authentication.
- Communication.
- Capability discovery.
- Local state.
- Event handling.
- Synchronization.
- Permission enforcement.
- Health reporting.
- Updates.
- Logging.
- Resource monitoring.
- Connection management.

Establish a minimal endpoint architecture and optional runtime modules.

A device should not need the full MIA intelligence infrastructure to participate in the MIA ecosystem.

For example, a glasses endpoint might require only communication, authentication, voice, display, and interaction services.

Define how device-specific runtimes communicate with MIA Core.

Evaluate native applications, shared libraries, APIs, lightweight agents, and other appropriate approaches.

---

6. Device Identity, Registration and Trust

Design the device identity architecture.

Every participating device should have a unique identity.

Investigate:

- Device registration.
- Initial pairing.
- Device authentication.
- Device certificates.
- Key management.
- Trusted-device lists.
- Device ownership.
- Device roles.
- User association.
- Device revocation.
- Device replacement.
- Lost-device recovery.

Define the lifecycle:

1. Device discovered.
2. Device pairing initiated.
3. User authorization.
4. Device identity established.
5. Capabilities registered.
6. Device becomes operational.
7. Trust periodically evaluated.
8. Device disconnected, revoked, or retired.

Determine how a device proves its identity without relying solely on network location.

Do not equate being connected to a home network or Tailscale network with being authorized to perform every MIA operation.

Coordinate with Prompt 13 for the comprehensive security architecture.

---

7. Device Discovery and Capability Registry

Design a unified device discovery system.

MIA should understand which devices exist, which are available, and what they can actually do.

Define a device registry containing:

- Device identity.
- Device type.
- Hardware model.
- Operating system.
- Runtime version.
- Network status.
- Last-seen timestamp.
- Available resources.
- Supported capabilities.
- Active services.
- Trust state.
- Health state.
- Power state.
- Location or logical environment, when permitted.
- Current workload.

Distinguish between:

- Capability advertised.
- Capability detected.
- Capability supported by the runtime.
- Capability operational.
- Capability authorized.
- Capability available now.
- Capability tested successfully.

Do not allow MIA to claim that a device can perform an operation merely because the hardware theoretically supports it.

Design capability discovery, verification, updates, and expiration.

---

8. Distributed Intelligence and Model Execution

Connect the intelligence architecture from Prompt 07 to the distributed device architecture.

Determine how MIA selects where inference should happen.

Investigate:

- Workstation inference.
- Phone inference.
- Edge-device inference.
- Cloud inference.
- Remote model servers.
- Specialized accelerators.
- Multi-model councils.
- Model caching.
- Model deployment.
- Model transfer.
- Resource contention.

Establish a model-placement and execution policy considering:

- Hardware compatibility.
- RAM.
- VRAM.
- CPU.
- NPU.
- Latency.
- Network quality.
- Privacy.
- Cost.
- Battery.
- Thermal limits.
- Model availability.
- Task requirements.

A device must not receive an inference workload that exceeds its capabilities.

Determine how inference jobs are scheduled, interrupted, retried, moved, or abandoned.

Establish the difference between moving a task to another device and transferring a running model session.

Do not assume arbitrary model execution can migrate seamlessly between different hardware architectures.

---

9. Distributed Memory and Context Synchronization

This is one of the most important architectural areas.

Design how MIA maintains coherent memory and context across devices.

Investigate:

- Central memory services.
- Local memory caches.
- Encrypted device storage.
- Conversation synchronization.
- Episodic memory.
- Semantic memory.
- Procedural memory.
- User preferences.
- Project context.
- Workspace state.
- Mission state.
- Device-specific context.
- Shared household information.

Determine which information should:

- Exist centrally.
- Exist locally.
- Be replicated.
- Be cached temporarily.
- Remain device-specific.
- Never leave a device without explicit permission.

Establish synchronization rules for:

- New records.
- Updates.
- Corrections.
- Deletions.
- Conflicts.
- Duplicate records.
- Offline changes.
- Reconnection.
- Device replacement.

Evaluate synchronization technologies and conflict-resolution approaches.

Consider event-based synchronization, version vectors, logical clocks, CRDTs, and other appropriate mechanisms.

Do not apply complex distributed consistency techniques where simpler mechanisms are sufficient.

Preserve provenance and source attribution.

A device must not silently overwrite newer or more authoritative memory with stale information.

Define how memory remains consistent while allowing local offline operation.

---

10. Distributed Communication Architecture

Design the communication infrastructure.

Evaluate:

- HTTP APIs.
- REST.
- WebSockets.
- gRPC.
- QUIC.
- MQTT.
- Message queues.
- Event buses.
- Local IPC.
- Peer-to-peer communication.
- Push notifications.
- Device-to-device communication.

Define which communication patterns suit:

- Interactive conversations.
- Streaming audio.
- Video.
- Model inference.
- Device commands.
- Sensor telemetry.
- Background synchronization.
- Notifications.
- Workflow coordination.
- Large file transfers.

Establish communication contracts, message schemas, versioning, retry behavior, timeouts, and failure handling.

Avoid unnecessary protocol proliferation.

Recommend a practical communication stack with clearly justified exceptions.

---

11. Local Network, Remote Access and Connectivity

Design the network architecture.

Support:

- Local Wi-Fi.
- Ethernet.
- Mobile data.
- Bluetooth.
- USB.
- Personal hotspots.
- VPN.
- Tailscale.
- Remote networks.
- Intermittent connectivity.
- Offline environments.

Evaluate Tailscale and alternatives for secure remote access.

Determine how devices discover each other on local networks without depending entirely on cloud infrastructure.

Consider:

- DNS.
- mDNS.
- Service discovery.
- Network segmentation.
- NAT traversal.
- Relay services.
- Peer-to-peer connections.
- Firewall policies.
- Network transitions.

Distinguish local network discovery from device authentication.

Determine how the architecture behaves when:

- Internet access disappears.
- The local router fails.
- A device changes networks.
- A VPN becomes unavailable.
- A device reconnects after an extended offline period.

---

12. Offline-First Operation and Graceful Degradation

Define the offline operating model.

MIA should remain useful when:

- Internet is unavailable.
- Cloud providers are unavailable.
- The primary PC is powered off.
- A phone is disconnected.
- A remote server is unreachable.
- A device has limited battery.
- Synchronization is delayed.

Create an offline capability matrix.

For each important capability, identify:

- Required services.
- Required devices.
- Local dependencies.
- Network dependencies.
- Offline availability.
- Degraded behavior.
- Recovery behavior.

Determine which devices can temporarily operate independently.

Define how MIA communicates reduced capability without pretending a service is operational.

Establish reconnection and synchronization behavior.

---

13. Distributed Applications and Workload Coordination

Connect the application framework from Prompt 03 to the distributed architecture.

Determine how applications operate across devices.

Investigate:

- Device-specific applications.
- Shared application identity.
- Remote application access.
- Application state synchronization.
- Cross-device handoff.
- Deep links.
- Remote execution.
- Background services.
- Application capability requirements.

For example, a greenhouse application may display on a phone while collecting sensor data from a Raspberry Pi and coordinating with a workstation-hosted MIA intelligence service.

Define how these components cooperate without creating multiple incompatible versions of the same application.

Establish application portability rules.

Do not assume desktop applications can run directly on Android or smart glasses.

Define how shared capabilities can be exposed through different device-specific interfaces.

---

14. Cross-Device Conversation and Session Continuity

Design conversational continuity.

A user should be able to begin interacting with MIA on one device and continue on another where appropriate.

Investigate:

- Conversation identity.
- Session synchronization.
- Context transfer.
- Active conversation state.
- Voice-session handoff.
- Pending responses.
- Interruptions.
- Streaming.
- Device switching.
- Session recovery.

For example:

A user begins a conversation with MIA on their PC, continues it through their phone, and later receives a relevant update through smart glasses.

Define what transfers and what remains device-specific.

Avoid duplicating conversations or losing important context.

Distinguish between continuing a conversation and transferring an active real-time voice session, since these have different technical requirements.

---

15. Distributed Autonomy and Agent Execution

Connect Prompt 08's autonomy architecture to the device ecosystem.

Determine where agents execute and how they coordinate across devices.

Investigate:

- Central orchestration.
- Local agents.
- Remote agents.
- Device-specific agents.
- Background workers.
- Workflow scheduling.
- Task delegation.
- Agent availability.
- Resource-aware execution.
- Task persistence.
- Task recovery.
- Agent communication.

A task may require several devices.

For example:

1. A user requests greenhouse monitoring.
2. A Raspberry Pi collects environmental data.
3. A local service evaluates thresholds.
4. MIA interprets the situation.
5. An authorized workflow prepares an action.
6. The appropriate controller executes the permitted operation.
7. MIA reports the result.

Define how tasks remain safe and consistent across device boundaries.

Authorization must remain valid when actions are delegated.

A device or agent must not gain authority simply because another trusted device requested work.

---

16. Home, Homestead and Environmental Systems

Give special attention to the home and homestead ecosystem.

Design how MIA integrates with:

- Smart home devices.
- Home automation controllers.
- Greenhouse systems.
- Aquaponics.
- Environmental sensors.
- Irrigation.
- Lighting.
- Climate control.
- Cameras.
- Energy monitoring.
- Embedded controllers.
- Local network infrastructure.

Evaluate appropriate protocols and technologies:

- MQTT.
- Matter.
- Zigbee.
- Z-Wave.
- Bluetooth.
- Modbus.
- ESPHome.
- Home Assistant.
- Direct device APIs.

Do not assume one protocol will cover every use case.

Determine which functions should operate locally even when MIA's primary intelligence services are offline.

Safety-critical control must remain deterministic, bounded, and independently protected.

AI must not become the only mechanism preventing dangerous physical operations.

---

17. Data Synchronization and Consistency

Develop a comprehensive synchronization strategy.

Define:

- Authoritative data ownership.
- Local caches.
- Replication.
- Event ordering.
- Conflict resolution.
- Versioning.
- Tombstones.
- Data retention.
- Deletion propagation.
- Integrity validation.
- Retry behavior.
- Backpressure.
- Bandwidth limits.

Establish different consistency requirements for different information types.

For example:

- Preferences may tolerate delayed synchronization.
- Conversations should preserve order.
- Device telemetry may be time-series data.
- Safety-related device commands require explicit execution confirmation.
- Memory corrections and deletions must not be silently reversed by stale replicas.

Define what happens when two devices modify the same record while offline.

Document where eventual consistency is acceptable and where stronger guarantees are required.

---

18. Device Resource and Power Coordination

Design resource-aware distributed operation.

MIA should understand device constraints.

Investigate:

- CPU utilization.
- GPU utilization.
- Memory pressure.
- Storage.
- Network bandwidth.
- Battery.
- Thermal conditions.
- Power state.
- Active workload.
- Device availability.

Determine how resource information influences:

- Model routing.
- Background jobs.
- Synchronization.
- Media processing.
- Agent scheduling.
- Updates.
- Workload migration.

Avoid draining phone batteries or overheating small embedded devices for unnecessary workloads.

Define workload priority, interruption, and resource limits.

Preserve deterministic operating-system resource management.

MIA may coordinate workload placement but must not bypass system resource controls.

---

19. Device Updates, Versioning and Compatibility

Design the distributed versioning model.

Investigate:

- Device runtime versions.
- API compatibility.
- Protocol versions.
- Application versions.
- Model versions.
- Schema migrations.
- Capability versions.
- Update channels.
- Compatibility negotiation.
- Deprecation.
- Rollback.

Determine how devices with different update schedules remain compatible.

A phone may not update at the same time as a PC or embedded controller.

Define minimum supported versions and graceful handling of older endpoints.

Coordinate with Prompt 14 for operating-system updates and Prompt 15 for build and release infrastructure.

---

20. Distributed Observability and Diagnostics

Design system-wide observability.

MIA should be able to understand the state of the distributed environment.

Investigate:

- Device health.
- Service health.
- Connectivity.
- Synchronization status.
- Resource usage.
- Model availability.
- Task execution.
- Application status.
- Error propagation.
- Event history.
- Device logs.

Define a unified view showing:

- Connected devices.
- Offline devices.
- Degraded devices.
- Active services.
- Active workloads.
- Pending synchronization.
- Failed operations.
- Security warnings.

Establish correlation identifiers and distributed tracing.

MIA must distinguish observed status from inferred status.

A device that has not responded must be marked unreachable or unknown, not automatically declared broken.

Coordinate with Prompt 09's self-awareness and inspection architecture.

---

21. Distributed Security and Privacy Boundaries

Establish distributed security requirements.

Investigate:

- Device authentication.
- Mutual authentication.
- Encryption in transit.
- Encryption at rest.
- Key storage.
- Device trust.
- Remote access.
- Authorization delegation.
- Session management.
- Revocation.
- Data minimization.
- Local privacy.
- Secure pairing.
- Network isolation.

Consider what happens if:

- A phone is lost.
- A workstation is compromised.
- A smart-glasses endpoint is stolen.
- An embedded device is exposed to an untrusted network.
- A device retains stale authorization.
- A remote connection is intercepted.

Define security boundaries between devices.

Do not assume that access to one MIA device grants access to every other device.

Prompt 13 will establish the comprehensive security architecture. This prompt must identify distributed security requirements and architectural constraints without duplicating the full threat model.

---

22. Device Replacement, Recovery and Lifecycle

Design the complete device lifecycle.

Investigate:

- Initial setup.
- Registration.
- Configuration.
- Normal operation.
- Temporary disconnection.
- Maintenance.
- Update.
- Replacement.
- Loss.
- Theft.
- Revocation.
- Retirement.
- Data migration.
- Factory reset.

Determine how a replacement device can recover appropriate MIA state without inheriting unnecessary permissions or exposing personal information.

Define what happens to locally cached data when a device is retired or revoked.

Ensure that the loss of one endpoint does not compromise the entire MIA ecosystem.

Coordinate with Prompt 14 for comprehensive recovery and backup behavior.

---

23. Hardware and Device Support Matrix

Create a practical device support matrix.

Include:

- Current development PC.
- Future workstation.
- Android phone.
- Current smart glasses.
- Raspberry Pi 5.
- AI HAT+ 2.
- Jetson-class edge devices.
- ESP32.
- Arduino-class controllers.
- Smart displays.
- Future wearable devices.
- Zeta Astralis.
- Spatial computing devices.

For each, identify:

- Operating environment.
- MIA runtime.
- Primary responsibilities.
- Available compute.
- AI capabilities.
- Storage.
- Network connectivity.
- Sensor access.
- Display capabilities.
- Power constraints.
- Offline functionality.
- Security considerations.
- Development maturity.
- Recommended role.

Do not assume every device is currently available or supported.

Separate present hardware from future candidates.

---

24. Distributed Architecture Diagrams

Produce diagrams showing:

1. Complete distributed MIA architecture.
2. Device class architecture.
3. MIA Core and endpoint runtime boundaries.
4. Device identity and registration lifecycle.
5. Device discovery and capability registry.
6. Distributed intelligence and model routing.
7. Distributed memory architecture.
8. Communication and event infrastructure.
9. Local and remote network architecture.
10. Offline operation and reconnection.
11. Distributed application architecture.
12. Cross-device conversation continuity.
13. Distributed agent execution.
14. Home and homestead integration.
15. Synchronization and conflict resolution.
16. Resource and power coordination.
17. Distributed updates and version compatibility.
18. Observability and diagnostics.
19. Device revocation and replacement.
20. Complete end-to-end example workflow.

Use Mermaid where appropriate and explain every diagram.

---

25. End-to-End Architecture Scenarios

Validate the proposed architecture using realistic scenarios.

At minimum, document these:

Scenario A — PC to Phone Conversation

A user starts a conversation on the desktop and continues on Android.

Show session continuity, context transfer, authentication, and failure behavior.

Scenario B — Smart Glasses Interaction

A user interacts with MIA through smart glasses while the phone or workstation provides additional processing.

Show endpoint communication, device capabilities, permissions, and latency considerations.

Scenario C — Offline Phone Operation

The phone loses internet and access to the workstation.

Show what MIA can still do locally and how it synchronizes after reconnection.

Scenario D — Greenhouse Monitoring

A Raspberry Pi collects environmental data while MIA interprets it and presents relevant information on the phone and desktop.

Show data flow, deterministic services, and device responsibilities.

Scenario E — Distributed AI Task

A demanding reasoning task is routed to a capable workstation while the user interacts from a phone.

Show resource discovery, scheduling, communication, and result delivery.

Scenario F — Device Loss

The user's phone is lost.

Show revocation, protection of local data, recovery, and replacement-device enrollment.

Scenario G — Primary PC Unavailable

The workstation is powered off.

Show how the remaining devices operate and which capabilities become unavailable.

Scenario H — Conflicting Offline Changes

Two devices modify the same information while disconnected.

Show conflict detection, resolution, provenance, and recovery.

Scenario I — Multi-Device Mission

MIA coordinates a task involving a PC, phone, and embedded device.

Show task ownership, authorization, execution confirmation, and audit history.

Scenario J — Network Failure

The home network or internet connection becomes unavailable.

Show local services, device discovery, degraded behavior, and recovery.

Each scenario must identify:

- Participating devices.
- Services involved.
- Communication path.
- Data movement.
- Security boundaries.
- Failure modes.
- Expected user experience.

---

26. Technology Evaluation and Research

Evaluate appropriate technologies for:

- Cross-device communication.
- Device identity.
- Synchronization.
- Distributed state.
- Event infrastructure.
- Service discovery.
- Remote access.
- Edge computing.
- Device runtimes.
- Mobile integration.
- Embedded communication.
- Distributed tracing.
- Workload coordination.

Consider appropriate technologies such as:

- Tailscale.
- WireGuard.
- MQTT.
- Matter.
- Home Assistant.
- gRPC.
- WebSockets.
- HTTP APIs.
- QUIC.
- NATS.
- Redis Streams.
- PostgreSQL.
- SQLite.
- CRDT libraries.
- Version vectors.
- OpenTelemetry.
- systemd.
- Containers.
- Android services.
- Lightweight Linux runtimes.

Do not treat these technologies as interchangeable.

For each major recommendation, document:

1. Technology.
2. Purpose.
3. Alternatives.
4. Advantages.
5. Limitations.
6. Platform compatibility.
7. Performance implications.
8. Security implications.
9. Operational complexity.
10. Maintenance requirements.
11. Recommendation.
12. Supporting evidence.

Prefer official documentation, maintained projects, technical specifications, and reproducible testing.

Do not introduce distributed infrastructure merely because it is fashionable.

Favor the simplest architecture that satisfies the actual requirements.

---

27. Required Deliverables

Create the following documents:

1. "MIA_OS_DISTRIBUTED_ARCHITECTURE.md"
2. "MIA_OS_MULTI_DEVICE_STRATEGY.md"
3. "MIA_OS_DEVICE_CLASS_AND_RUNTIME_ARCHITECTURE.md"
4. "MIA_OS_DEVICE_IDENTITY_AND_REGISTRATION.md"
5. "MIA_OS_DEVICE_DISCOVERY_AND_CAPABILITY_REGISTRY.md"
6. "MIA_OS_DISTRIBUTED_INTELLIGENCE_ARCHITECTURE.md"
7. "MIA_OS_DISTRIBUTED_MEMORY_AND_CONTEXT.md"
8. "MIA_OS_DEVICE_COMMUNICATION_ARCHITECTURE.md"
9. "MIA_OS_NETWORK_AND_REMOTE_ACCESS_ARCHITECTURE.md"
10. "MIA_OS_OFFLINE_FIRST_AND_DEGRADED_OPERATION.md"
11. "MIA_OS_DISTRIBUTED_APPLICATION_ARCHITECTURE.md"
12. "MIA_OS_CROSS_DEVICE_SESSION_CONTINUITY.md"
13. "MIA_OS_DISTRIBUTED_AGENT_EXECUTION.md"
14. "MIA_OS_HOME_AND_HOMESTEAD_DEVICE_INTEGRATION.md"
15. "MIA_OS_DATA_SYNCHRONIZATION_AND_CONSISTENCY.md"
16. "MIA_OS_DEVICE_RESOURCE_AND_POWER_COORDINATION.md"
17. "MIA_OS_DISTRIBUTED_VERSIONING_AND_COMPATIBILITY.md"
18. "MIA_OS_DISTRIBUTED_OBSERVABILITY.md"
19. "MIA_OS_DISTRIBUTED_SECURITY_REQUIREMENTS.md"
20. "MIA_OS_DEVICE_LIFECYCLE_AND_RECOVERY.md"
21. "MIA_OS_DEVICE_SUPPORT_MATRIX.md"
22. "MIA_OS_DISTRIBUTED_ARCHITECTURE_DIAGRAMS.md"
23. "MIA_OS_DISTRIBUTED_END_TO_END_SCENARIOS.md"
24. "MIA_OS_DISTRIBUTED_TECHNOLOGY_EVALUATION.md"
25. "MIA_OS_DISTRIBUTED_ACCEPTANCE_CRITERIA.md"
26. "MIA_OS_DISTRIBUTED_OPEN_QUESTIONS.md"

Also update:

- "MIA_OS_MASTER_PLAN.md"
- "MIA_OS_DECISION_LOG.md"
- "MIA_OS_OPEN_QUESTIONS.md"
- "MIA_OS_RISK_REGISTER.md"
- "MIA_OS_REQUIREMENTS_TRACEABILITY.md"
- "MIA_OS_IMPLEMENTATION_STATUS.md"
- "MIA_OS_HARDWARE_AND_PLATFORM_STRATEGY.md"
- "MIA_OS_INTELLIGENCE_ARCHITECTURE.md"
- "MIA_OS_MEMORY_INFRASTRUCTURE.md"
- "MIA_OS_DEVICE_CAPABILITY_MATRIX.md"
- "MIA_OS_APPLICATION_FRAMEWORK.md"
- "MIA_OS_DESKTOP_ARCHITECTURE.md"
- "MIA_OS_VISUAL_IDENTITY.md"

Maintain consistency with Prompts 00–11.

---

28. Decision Records and Traceability

Create formal decision records for major distributed architecture decisions.

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

- Device requirements.
- Hardware capabilities.
- Device runtimes.
- Intelligence services.
- Memory services.
- Communication.
- Synchronization.
- Applications.
- Autonomy.
- Security.
- Privacy.
- Reliability.
- Implementation phases.

Identify decisions that require user approval.

---

29. Acceptance Criteria

Prompt 12 is complete only when:

- Existing device integrations have been audited.
- A unified distributed MIA architecture is defined.
- One persistent MIA identity is maintained across devices.
- Device classes and responsibilities are established.
- Device runtime boundaries are specified.
- Device identity and registration are designed.
- Capability discovery is defined.
- Distributed inference is addressed.
- Memory and context synchronization are designed.
- Communication architecture is specified.
- Local and remote connectivity are addressed.
- Offline operation is defined.
- Distributed application behavior is established.
- Cross-device conversation continuity is designed.
- Distributed agent execution is addressed.
- Home and homestead integration is documented.
- Synchronization and conflict resolution are specified.
- Resource and power coordination are established.
- Version compatibility is addressed.
- Distributed observability is designed.
- Device lifecycle and replacement are addressed.
- Security requirements and boundaries are documented.
- The device support matrix is complete.
- All end-to-end scenarios are analyzed.
- Technology recommendations have supporting evidence.
- All diagrams and deliverables are complete.
- Risks and open questions are documented.
- The architecture remains consistent with Prompts 00–11.

---

30. Boundaries With Future Prompts

Do not duplicate the detailed scope of later prompts.

- Prompt 13 handles comprehensive security, privacy, identity, and permission architecture.
- Prompt 14 handles boot, recovery, updates, and reliability.
- Prompt 15 handles development environment and build infrastructure.
- Prompt 16 handles implementation sequencing and migration.
- Prompt 17 consolidates and independently reviews the complete master plan.

This prompt establishes the distributed architecture and identifies its security, reliability, and lifecycle requirements.

It does not finalize the complete security threat model or implementation roadmap.

---

31. Planning Restrictions

This is an architecture research and planning exercise.

Do not:

- Implement distributed services.
- Replace existing APIs.
- Migrate databases.
- Change device configurations.
- Deploy new networking infrastructure.
- Install new runtime dependencies.
- Change authentication mechanisms.
- Modify synchronization behavior.
- Deploy new device agents.
- Begin hardware fabrication.
- Begin implementation.

You may inspect source code, existing configuration, API contracts, documentation, hardware specifications, and non-destructive diagnostics.

Preserve existing work.

Verify current device capabilities and software status before making architectural assumptions.

---

32. Final Objective

The final architecture should make MIA one persistent, coherent system that can operate across multiple devices and environments.

The user should be able to:

- Interact with MIA from the PC, phone, and supported wearable devices.
- Continue relevant conversations across devices.
- Access consistent memory and project context.
- Use local capabilities without depending entirely on cloud services.
- Distribute demanding workloads to capable hardware.
- Coordinate home and homestead systems.
- Operate in degraded or offline environments.
- Replace devices without losing MIA's identity.
- Understand which devices and services are available.
- Maintain control over device permissions and delegated operations.

MIA should not require every device to be equally powerful or permanently connected.

Each device should contribute what it is best suited to provide while remaining part of one coordinated ecosystem.

Produce a technically rigorous, evidence-based, internally consistent distributed architecture.

When finished, summarize:

1. The recommended distributed architecture.
2. The role of MIA Core and individual device runtimes.
3. The responsibilities of the PC, phone, glasses, and embedded devices.
4. Device identity and capability discovery.
5. Distributed intelligence and model placement.
6. Memory and context synchronization.
7. Communication and networking.
8. Offline operation and graceful degradation.
9. Cross-device application and conversation continuity.
10. Home and homestead integration.
11. Distributed security requirements.
12. The most significant technical risks.
13. Decisions requiring user approval.
14. Questions that must be resolved before Prompt 13.

Stop after completing Prompt 12. Wait for review and approval before beginning Prompt 13.
