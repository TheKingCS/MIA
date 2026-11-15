PROMPT 06 — HARDWARE, PLATFORM & TECHNOLOGY EVALUATION

Mission

Act as a senior hardware systems architect, Linux platform engineer, embedded systems engineer, AI hardware specialist, and technology researcher.

Your mission is to produce a comprehensive hardware and platform evaluation for MIA OS.

Prompts 00–05 established the vision, existing MIA ecosystem, feature ecosystem, application framework, system requirements, and proposed core operating system architecture.

Now determine what physical hardware MIA OS should support, what hardware capabilities it should leverage, which technologies should form its platform foundation, and how the system should scale across different device classes.

This is not simply a list of recommended computer components.

MIA is intended to become a persistent intelligent environment spanning desktop computers, mobile devices, smart glasses, embedded systems, and future wearable interfaces. Its hardware architecture must support that vision without requiring every device to run the same operating system or possess the same computational capabilities.

The result must be a technically defensible hardware and platform strategy that supports the immediate implementation of MIA OS while preserving long-term extensibility.

Planning and evaluation only. Do not begin implementation.

---

1. Review Previous Work and Establish the Baseline

Before evaluating hardware:

1. Review the outputs of Prompts 00–05.
2. Review the existing MIA repository and its documented hardware integrations.
3. Identify hardware requirements already established by the feature ecosystem and system requirements.
4. Identify hardware assumptions made in the core architecture.
5. Identify dependencies between hardware decisions and software architecture.
6. Identify unresolved hardware questions that could materially affect the OS design.

Use the existing repository and documented evidence wherever possible.

Do not assume that historical hardware plans are still current. Verify actual hardware availability, ownership, compatibility, and implementation status.

Create a hardware baseline that distinguishes:

- Confirmed hardware currently available.
- Hardware currently being used for MIA development.
- Hardware planned for near-term acquisition.
- Experimental hardware integrations.
- Long-term hardware concepts.
- Hardware that is merely an example or possibility.

Do not represent a planned device as an existing working integration.

---

2. Hardware Architecture Philosophy

Evaluate hardware according to the following principles.

2.1 Hardware independence

MIA OS should not depend on one specific computer manufacturer, GPU vendor, processor architecture, or AI accelerator.

Establish a hardware abstraction strategy that allows MIA to operate across compatible systems.

2.2 Capability-aware operation

MIA should understand the capabilities and limitations of the hardware currently available to it.

For example:

- Available CPU resources.
- Available RAM.
- GPU capabilities.
- Dedicated AI acceleration.
- Storage capacity and performance.
- Network connectivity.
- Battery and power constraints.
- Thermal limitations.
- Connected peripherals.
- Available cameras, microphones, displays, and speakers.

MIA should adapt its behavior to the capabilities of each device.

2.3 Local-first intelligence

Hardware should support increasingly capable local AI operation.

However, not every device needs to run large language models locally.

Determine which devices should:

- Run models locally.
- Execute lightweight inference.
- Act as an interface endpoint.
- Delegate computation to another trusted MIA device.
- Use cloud intelligence when appropriate.

2.4 Upgradeability

Hardware decisions should support incremental upgrades.

Avoid architectures that require replacing the entire system whenever a more capable processor, GPU, accelerator, or storage device becomes available.

2.5 Cost effectiveness

Distinguish between:

- Required hardware.
- Recommended hardware.
- Optional performance upgrades.
- Experimental hardware.
- Future aspirational hardware.

Do not recommend expensive hardware unless its capabilities justify the cost.

---

3. Primary Desktop and Workstation Hardware

Evaluate the requirements for MIA OS's primary computing environment.

Investigate:

- Desktop computers.
- Workstations.
- Laptops.
- Mini PCs.
- Small-form-factor systems.
- Custom-built computers.
- Virtual machines and test environments.

Determine suitable hardware configurations for several capability tiers.

At minimum, evaluate:

1. Minimum viable MIA OS system.
2. Recommended everyday MIA OS system.
3. AI-capable development workstation.
4. High-performance local AI workstation.
5. Future expandable workstation.

For each configuration, establish:

- CPU architecture and recommended processor characteristics.
- Core and thread requirements.
- RAM capacity.
- GPU requirements.
- Dedicated VRAM requirements.
- Storage capacity and performance.
- Network requirements.
- Power consumption.
- Cooling requirements.
- Upgradeability.
- Expected MIA capabilities.
- Limitations and compromises.

Evaluate Intel, AMD, and ARM platforms where relevant.

Evaluate both integrated and dedicated graphics.

Do not assume that the most powerful configuration is necessarily the best starting point.

---

4. CPU Architecture and Processing Strategy

Investigate:

- x86-64.
- ARM64.
- Other architectures only when they offer a meaningful advantage.

Evaluate compatibility with:

- Linux distributions.
- Kernel support.
- Drivers.
- Desktop environments.
- AI inference frameworks.
- Existing MIA software.
- Development tooling.
- Virtualization.
- Containerization.

Determine whether MIA OS should initially prioritize x86-64 while maintaining a clear path toward ARM64.

Investigate CPU scheduling, performance and efficiency cores, instruction-set acceleration, virtualization extensions, and hardware security capabilities.

Explain which CPU characteristics matter most for MIA workloads.

---

5. GPU, Graphics and AI Acceleration

This is a major area of investigation.

Evaluate:

GPU platforms

- NVIDIA.
- AMD.
- Intel.
- Integrated graphics.
- Other viable acceleration platforms.

Investigate:

- Linux driver maturity.
- Open-source versus proprietary drivers.
- Vulkan.
- CUDA.
- ROCm.
- OpenCL.
- DirectML only where relevant to cross-platform compatibility.
- GPU compute support.
- Video encoding and decoding.
- Multi-monitor support.
- Wayland compatibility.
- AI inference compatibility.

Dedicated AI acceleration

Evaluate:

- NVIDIA GPU inference.
- AMD GPU inference.
- Intel AI acceleration.
- Neural processing units.
- AI accelerator cards.
- PCIe accelerators.
- USB accelerators.
- Embedded AI modules.
- Future accelerator technologies.

Compare performance, software maturity, memory capacity, power consumption, cost, and development complexity.

MIA-specific requirements

Determine how MIA should discover and manage available acceleration resources.

Consider:

- GPU availability.
- Dedicated VRAM.
- Shared system memory.
- Multiple GPUs.
- Concurrent workloads.
- Model placement.
- Inference scheduling.
- Thermal constraints.
- Power limitations.
- Resource contention between desktop applications and AI workloads.

MIA should not assume that an AI accelerator is automatically useful simply because it advertises a high TOPS rating.

Evaluate actual supported workloads, software frameworks, memory limitations, and real-world performance.

---

6. Memory and Storage Requirements

Evaluate system memory requirements for:

- Linux and the graphical environment.
- MIA Core.
- Local inference.
- Multimodal processing.
- Application workloads.
- Virtual machines.
- Containers.
- Persistent memory systems.
- Caching and background processing.

Establish realistic RAM tiers.

Evaluate:

- DDR4.
- DDR5.
- LPDDR.
- ECC memory where appropriate.
- Unified memory architectures.
- GPU memory.
- Memory bandwidth.

Investigate storage technologies:

- SATA SSD.
- NVMe SSD.
- PCIe generations.
- HDD storage.
- External SSDs.
- Network-attached storage.

Establish a storage strategy for:

- Operating system.
- MIA Core.
- Applications.
- Models.
- User files.
- Long-term memory.
- Conversation history.
- Logs and diagnostics.
- Backups.
- Recovery images.
- Development environments.

Determine which data should remain on fast storage and which can be moved to slower or external storage.

Consider storage encryption, health monitoring, endurance, redundancy, and backup requirements.

Do not confuse storage capacity with backup protection.

---

7. Mobile Hardware and Android Integration

MIA's mobile experience is an important part of the larger ecosystem.

Evaluate Android as a mobile endpoint and determine the appropriate relationship between Android and MIA OS.

Investigate:

- Android architecture.
- Android application integration.
- Background execution restrictions.
- Foreground services.
- Microphone and camera permissions.
- Notifications.
- Bluetooth.
- Wi-Fi.
- Local network discovery.
- USB connectivity.
- Accessibility APIs.
- Device sensors.
- Battery management.
- Offline functionality.
- Secure communication with the primary MIA system.

Determine which MIA capabilities should run directly on Android and which should delegate to the primary MIA system.

Evaluate whether Android should be treated as:

- A companion interface.
- An independent MIA endpoint.
- A local inference device.
- A remote control and monitoring device.
- A combination of these roles.

Preserve the existing Android implementation wherever practical.

Do not assume MIA OS should replace Android on the user's phone.

---

8. Smart Glasses, Wearables and Spatial Hardware

Evaluate the hardware requirements for MIA's future wearable and spatial interfaces.

Include:

- Smart glasses.
- Camera-equipped glasses.
- Display-equipped glasses.
- Audio glasses.
- AR headsets.
- VR headsets.
- Wearable displays.
- Wrist-worn devices.
- Smart rings.
- Future neural or brain-computer interfaces.

Evaluate:

- Display capabilities.
- Field of view.
- Camera availability.
- Microphone quality.
- Speaker and audio output.
- Battery capacity.
- Wireless communication.
- On-device processing.
- Latency.
- Thermal limitations.
- Weight and comfort.
- Privacy indicators.
- SDK and developer access.
- Platform restrictions.

Investigate how MIA should adapt interfaces to different display and input capabilities.

A glasses endpoint should not need to run the full MIA operating system.

Consider the phone or primary computer acting as the computational host while the wearable acts as an interface and sensor endpoint.

Evaluate the current and potential capabilities of the user's smart-glasses platform, but verify the actual available SDKs and APIs before making assumptions.

Include the Zeta Astralis concept as a possible future wearable display project, not as an established hardware requirement.

---

9. Embedded Systems and Homestead Hardware

MIA is intended to eventually interact with physical environments, smart homes, agriculture systems, and embedded devices.

Evaluate:

- Raspberry Pi platforms.
- Raspberry Pi 5.
- Raspberry Pi AI HAT+ and AI HAT+ 2.
- Other embedded AI boards.
- NVIDIA Jetson platforms.
- ESP32.
- Arduino-compatible microcontrollers.
- Microcontrollers with wireless connectivity.
- Industrial control hardware.
- Sensor networks.
- Smart relays and actuators.
- Cameras.
- Environmental monitoring equipment.

Investigate the appropriate division of responsibilities between:

- MIA OS.
- MIA Core.
- Embedded Linux devices.
- Microcontroller firmware.
- Smart-home protocols.
- Local automation services.

Evaluate:

- GPIO.
- I2C.
- SPI.
- UART.
- USB.
- Ethernet.
- Wi-Fi.
- Bluetooth.
- Zigbee.
- Z-Wave.
- Matter.
- MQTT.
- Modbus where relevant.

Determine how MIA could eventually monitor and coordinate:

- Greenhouses.
- Aquaponics systems.
- Irrigation.
- Water systems.
- Environmental sensors.
- Lighting.
- Climate control.
- Cameras.
- Workshop equipment.
- Smart-home devices.

Do not design the entire smart-home or agricultural automation system here. Establish hardware and platform compatibility requirements and identify the appropriate software responsibilities.

Physical safety and hardware protection must remain independent of AI reasoning.

Critical equipment should have deterministic safeguards, safe defaults, and manual overrides.

---

10. Peripheral and Device Compatibility

Evaluate the hardware integration requirements for:

- Keyboards.
- Mice.
- Touchscreens.
- Styluses.
- Game controllers.
- Cameras.
- Microphones.
- Speakers.
- Headphones.
- Bluetooth devices.
- Printers.
- Scanners.
- External displays.
- USB devices.
- Storage devices.
- Smart-home interfaces.
- Audio interfaces.
- MIDI controllers.

Investigate Linux compatibility and relevant subsystems.

Include:

- PipeWire.
- ALSA.
- BlueZ.
- udev.
- libinput.
- USB device management.
- Camera support.
- Display hotplugging.
- Power management.

Determine how MIA should discover connected devices, understand their capabilities, and make them available to applications and intelligent services.

---

11. Networking and Distributed Hardware

Evaluate the network infrastructure required for a distributed MIA environment.

Investigate:

- Ethernet.
- Wi-Fi.
- Bluetooth.
- Local network discovery.
- IPv4 and IPv6.
- VPN connectivity.
- Tailscale.
- Secure remote access.
- Peer-to-peer communication.
- Local device-to-device communication.
- Network segmentation.
- Offline operation.

Determine how MIA devices should discover and communicate with one another.

Consider a future environment containing:

- Primary MIA workstation.
- Android phone.
- Smart glasses.
- Raspberry Pi devices.
- Home automation hardware.
- Embedded sensors.
- Remote MIA endpoints.

Evaluate whether computation should be centralized, distributed, or dynamically allocated according to availability and workload.

Define the hardware requirements for reliable distributed operation.

Do not allow network availability to become a single point of failure for basic device functionality.

---

12. Virtualization, Containers and Hardware Isolation

Evaluate the role of:

- KVM.
- QEMU.
- libvirt.
- Docker.
- Podman.
- LXC.
- systemd-nspawn.
- Hardware passthrough.
- GPU passthrough.
- Virtual test machines.
- Sandboxed application environments.

Determine how MIA OS should support development, testing, application isolation, and experimental environments.

Evaluate the performance and compatibility implications of virtualization on the target hardware.

Identify which technologies should be used for production services versus development and testing.

---

13. Power, Thermal Management and Reliability

MIA should be aware of the physical limitations of the devices it manages.

Investigate:

- CPU temperature monitoring.
- GPU temperature monitoring.
- Fan control.
- Power profiles.
- Battery health.
- Charging behavior.
- Thermal throttling.
- Power consumption.
- UPS support.
- Power-loss behavior.
- Hardware health monitoring.

Determine how hardware telemetry should be exposed to MIA.

MIA may recommend resource adjustments or performance changes, but it must not override hardware protection mechanisms or safety controls.

Establish sensible behavior for:

- Overheating.
- Low battery.
- Memory pressure.
- Storage exhaustion.
- Failing storage.
- Network loss.
- Hardware disconnection.
- Accelerator failure.
- Unexpected power loss.

---

14. Hardware Discovery and Capability Registry

Design the requirements for a unified hardware discovery and capability registry.

MIA should be able to understand the hardware available to it without relying on unsupported assumptions.

Investigate how the system can discover and represent:

- CPU.
- RAM.
- GPU.
- AI accelerators.
- Storage.
- Network interfaces.
- Cameras.
- Microphones.
- Speakers.
- Displays.
- Sensors.
- Peripherals.
- Power capabilities.
- Connected MIA devices.

For each discovered component, consider:

- Device identity.
- Manufacturer and model.
- Hardware capabilities.
- Driver status.
- Compatibility.
- Availability.
- Health.
- Performance characteristics.
- Power requirements.
- Security considerations.
- Supported operations.

Determine which information can be discovered automatically, which requires user confirmation, and which must remain explicitly unknown.

The capability registry must distinguish between:

- Hardware detected.
- Driver available.
- Device operational.
- Capability supported.
- Capability tested.
- Capability currently available.

Detection alone must never be interpreted as proof that a capability works.

---

15. Hardware Resource Coordination

Investigate how MIA OS should allocate and coordinate available hardware resources.

Consider:

- CPU scheduling.
- GPU scheduling.
- AI inference workloads.
- Memory allocation.
- Storage I/O.
- Network bandwidth.
- Power budgets.
- Thermal limits.
- Background services.
- Foreground applications.
- Time-sensitive tasks.

Determine which responsibilities belong to Linux and its existing resource-management systems versus MIA's higher-level orchestration layer.

MIA should be able to understand resource availability and make intelligent workload-placement recommendations.

However, MIA must not replace the operating system's deterministic process scheduler or bypass resource and security limits.

Evaluate the possibility of moving AI workloads between devices when beneficial.

For example:

- A phone handles voice capture.
- A workstation performs heavier inference.
- A Raspberry Pi manages local sensor collection.
- Cloud models handle tasks that exceed available local resources.

Establish the technical requirements for this behavior.

---

16. Hardware Compatibility and Support Matrix

Create a comprehensive compatibility matrix.

Include:

- Hardware class.
- CPU architecture.
- Graphics architecture.
- AI acceleration.
- Linux support.
- Driver maturity.
- MIA compatibility.
- Performance tier.
- Known limitations.
- Development priority.
- Recommended role in the ecosystem.

Distinguish between hardware that MIA OS should officially support and hardware that may work through general Linux compatibility.

Define a realistic initial hardware support target.

Avoid promising universal compatibility.

---

17. Technology Evaluation and Selection

Evaluate the technologies relevant to the hardware platform.

For every major recommendation, include:

1. Technology name.
2. Primary purpose.
3. Alternatives.
4. Advantages.
5. Disadvantages.
6. Linux compatibility.
7. Hardware compatibility.
8. Development complexity.
9. Maintenance implications.
10. Performance implications.
11. Security considerations.
12. Cost implications where relevant.
13. Recommendation.
14. Evidence and source documentation.

Use a consistent comparison methodology.

Distinguish between:

- Recommended for initial implementation.
- Recommended for future expansion.
- Optional.
- Experimental.
- Not recommended.
- Requires further investigation.

Do not choose technologies based solely on popularity or marketing claims.

---

18. Hardware Roadmap

Create a staged hardware roadmap.

At minimum, distinguish:

Stage A — Initial MIA OS Development

The minimum hardware needed to build, test, and operate the first MIA OS implementation.

Stage B — Everyday MIA OS

Hardware that supports reliable daily operation and normal MIA workloads.

Stage C — Local AI Expansion

Hardware that enables increasingly capable local inference and multimodal processing.

Stage D — Distributed MIA Environment

Hardware that supports Android, smart glasses, embedded systems, and local device coordination.

Stage E — Advanced MIA Environment

Long-term capabilities involving advanced spatial interfaces, wearable computing, specialized accelerators, and additional hardware platforms.

For every stage, specify:

- Objectives.
- Hardware requirements.
- Dependencies.
- Estimated cost ranges where defensible.
- Capabilities unlocked.
- Risks.
- Upgrade paths.
- Exit criteria.

Avoid turning this into a shopping list. Focus on the platform capabilities each stage enables.

---

19. Hardware Failure and Degraded Operation

Evaluate how MIA should behave when hardware becomes unavailable or fails.

Examples:

- GPU failure.
- AI accelerator failure.
- Storage degradation.
- Network disconnection.
- Camera failure.
- Microphone failure.
- Battery limitations.
- Overheating.
- Peripheral disconnection.
- Embedded device failure.

Define graceful degradation.

MIA should preserve essential functions wherever possible rather than assuming every hardware component is permanently available.

Identify which failures can be recovered automatically and which require user intervention.

---

20. Required Architecture Diagrams

Produce diagrams showing:

1. Primary workstation hardware architecture.
2. CPU, GPU, and AI acceleration relationships.
3. Hardware discovery and capability registry.
4. Hardware resource coordination.
5. Android and workstation relationship.
6. Smart-glasses and spatial endpoint architecture.
7. Embedded and homestead hardware architecture.
8. Distributed MIA device network.
9. Hardware abstraction layers.
10. Hardware failure and degraded-operation pathways.

Use Mermaid diagrams where appropriate.

Every diagram must include a written explanation.

---

21. Research and Evidence Requirements

Use current, reliable technical documentation.

Prioritize:

- Official Linux kernel documentation.
- Official distribution documentation.
- Official hardware manufacturer specifications.
- Official driver documentation.
- Official framework documentation.
- Official Android developer documentation.
- Official Raspberry Pi documentation.
- Official NVIDIA, AMD, and Intel technical documentation.
- Official embedded platform documentation.
- Relevant hardware standards and specifications.
- Reproducible benchmarks and credible technical testing.

For AI hardware, distinguish between advertised theoretical performance and measured performance on relevant workloads.

Record sources and access dates for important technology recommendations.

Do not invent benchmark results, compatibility claims, prices, or hardware specifications.

If information cannot be verified, label it as unverified.

---

22. Required Deliverables

Create the following documentation:

1. "MIA_OS_HARDWARE_AND_PLATFORM_STRATEGY.md"
2. "MIA_OS_DESKTOP_HARDWARE_REQUIREMENTS.md"
3. "MIA_OS_CPU_AND_ARCHITECTURE_EVALUATION.md"
4. "MIA_OS_GPU_AND_AI_ACCELERATION_STRATEGY.md"
5. "MIA_OS_MEMORY_AND_STORAGE_REQUIREMENTS.md"
6. "MIA_OS_ANDROID_HARDWARE_INTEGRATION.md"
7. "MIA_OS_WEARABLE_AND_SPATIAL_HARDWARE.md"
8. "MIA_OS_EMBEDDED_AND_HOMESTEAD_HARDWARE.md"
9. "MIA_OS_PERIPHERAL_COMPATIBILITY.md"
10. "MIA_OS_NETWORK_AND_DISTRIBUTED_HARDWARE.md"
11. "MIA_OS_VIRTUALIZATION_AND_ISOLATION.md"
12. "MIA_OS_POWER_THERMAL_AND_HARDWARE_HEALTH.md"
13. "MIA_OS_HARDWARE_DISCOVERY_AND_CAPABILITY_REGISTRY.md"
14. "MIA_OS_HARDWARE_RESOURCE_COORDINATION.md"
15. "MIA_OS_HARDWARE_COMPATIBILITY_MATRIX.md"
16. "MIA_OS_HARDWARE_TECHNOLOGY_EVALUATION.md"
17. "MIA_OS_HARDWARE_ROADMAP.md"
18. "MIA_OS_HARDWARE_FAILURE_AND_DEGRADED_OPERATION.md"
19. "MIA_OS_HARDWARE_ARCHITECTURE_DIAGRAMS.md"
20. "MIA_OS_HARDWARE_ACCEPTANCE_CRITERIA.md"
21. "MIA_OS_HARDWARE_OPEN_QUESTIONS.md"

Also update:

- "MIA_OS_MASTER_PLAN.md"
- "MIA_OS_DECISION_LOG.md"
- "MIA_OS_OPEN_QUESTIONS.md"
- "MIA_OS_RISK_REGISTER.md"
- "MIA_OS_REQUIREMENTS_TRACEABILITY.md"
- "MIA_OS_IMPLEMENTATION_STATUS.md"

Ensure all documents agree with the previous architecture and requirements.

---

23. Decision Records and Traceability

Create formal decision records for major hardware and platform decisions.

Each decision must include:

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
- Conditions that would justify revisiting the decision.

Maintain traceability between hardware decisions, system requirements, architecture components, and future implementation phases.

Do not silently turn an experimental recommendation into an approved architectural decision.

---

24. Acceptance Criteria

This prompt is complete only when:

- The existing MIA hardware baseline has been verified.
- Hardware requirements are grounded in the actual MIA ecosystem.
- Desktop and workstation configurations have been evaluated.
- CPU architecture options have been compared.
- GPU and AI acceleration strategies have been evaluated.
- Memory and storage requirements have been established.
- Android integration requirements are documented.
- Smart-glasses and wearable hardware requirements are documented.
- Embedded and homestead hardware requirements are documented.
- Networking and distributed hardware requirements are established.
- Hardware discovery and capability registry requirements are defined.
- Resource coordination responsibilities are separated correctly between Linux and MIA.
- Compatibility and support matrices are complete.
- A staged hardware roadmap exists.
- Failure and degraded-operation behavior is documented.
- Technology recommendations have credible evidence.
- All major decisions are traceable.
- All deliverables are consistent with Prompts 00–05.
- Open questions and risks are explicitly documented.

---

25. Boundaries With Future Prompts

Do not duplicate the detailed scope of future prompts.

- Prompt 07 handles MIA intelligence infrastructure, model routing, memory, inference services, and local/cloud intelligence.
- Prompt 08 handles agent runtime, autonomy, planning, and action execution.
- Prompt 09 handles self-awareness, inspection, diagnostics, and controlled self-development.
- Prompt 10 handles the desktop experience and primary interface.
- Prompt 11 handles visual identity, themes, and spatial interface design.
- Prompt 12 handles the complete multi-device and distributed MIA architecture.
- Prompt 13 handles security, privacy, identity, and permission architecture.
- Prompt 14 handles boot, recovery, updates, and reliability.
- Prompt 15 handles development and build infrastructure.
- Prompt 16 handles implementation sequencing and migration.
- Prompt 17 consolidates and independently reviews the complete master plan.

This prompt establishes the hardware capabilities, compatibility requirements, and platform constraints that those later prompts must respect.

---

26. Planning Restrictions

This is an architecture research and planning exercise.

Do not:

- Install an operating system.
- Modify the existing MIA repository.
- Change system configurations.
- Purchase hardware.
- Run destructive commands.
- Replace existing components.
- Begin implementation.
- Treat speculative hardware as an approved requirement.

You may inspect existing repository documentation and run non-destructive diagnostic commands when necessary to verify hardware information.

Clearly distinguish verified findings from recommendations and assumptions.

If essential information is unavailable, document the gap rather than inventing an answer.

---

27. Final Objective

The final result should establish a coherent hardware strategy for MIA OS.

I want MIA to be able to grow from a practical desktop operating environment into a distributed intelligent ecosystem spanning my computer, phone, glasses, home, workshop, greenhouse, embedded devices, and future hardware.

The system should take advantage of powerful hardware when available without becoming dependent on expensive or specialized components.

It should recognize what hardware it has, understand what that hardware can do, allocate resources intelligently, and continue operating gracefully when individual components become unavailable.

Most importantly, hardware decisions must support the larger vision of MIA as an AI-native computing environment rather than constraining MIA to a conventional desktop operating system with an assistant attached.

Produce a technically rigorous, evidence-based, internally consistent hardware and platform strategy.

When finished, summarize the most consequential hardware decisions, identify anything that requires my approval, and provide the questions that must be resolved before proceeding.

Stop after completing Prompt 06. Wait for review and approval before beginning Prompt 07.
