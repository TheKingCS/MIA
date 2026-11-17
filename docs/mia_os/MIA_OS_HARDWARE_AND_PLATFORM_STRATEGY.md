# MIA OS: hardware and platform strategy (Prompt 06)

*Claude (Opus), 2026-11-17, on Zac's go ("we should be working on the OS dev plan"). Planning only: nothing was
installed, bought or reconfigured. The prompt is kept verbatim in `prompts/06_HARDWARE_PLATFORM_TECHNOLOGY_EVALUATION.md`.
Twenty documents sit beside this one (section 9); this one is where to start. **Verified** means read from the PC
itself or measured; **recommended** and **assumed** are marked as such.*

## 1. The headline

1. **The reference PC is enough for MIA OS's first version** and needs no purchase to start. Every MVP workload
   was measured on it (Windows); the Linux image with its graphics stack is built and boots in a test machine (PoC 2);
   one test remains, the graphics card under Fedora (PoC 1, a USB stick).
2. **The PC can't grow inside.** It is a Mini-ITX build (Gigabyte A620I AX): one graphics slot, two memory slots
   (both full), one graphics card. So MIA grows by **adding machines on the network, not cards in the box**: the
   next AI hardware is a second, model-serving machine, and the design treats every device as a node with its own
   capability record from the start (DEC-0202).
3. **Linux owns the hardware; MIA owns what it's used for.** Discovery reads Linux's own sources into a capability
   registry; scheduling, power and drivers stay Linux's; MIA decides which model runs where and what waits when the
   card is busy (DEC-0203, DEC-0204; consistent with Prompt 05's rule "MIA never drives hardware").
4. **Every device degrades to something useful.** No graphics card: a smaller model on the processor, or the other
   node's. No PC: the phone keeps its own records and model. No network: each device carries on alone and syncs later.
5. **Nothing speculative is a requirement.** Laptops, tablets, watches, smart displays, a truck computer and
   dedicated MIA hardware are named as later or speculative, and nothing depends on them.

## 2. The verified baseline (2026-11-17, read-only commands on the PC)

| Part | What it is | Source |
|---|---|---|
| Processor | AMD Ryzen 7 9800X3D, 8 cores, Zen 5 with 3D V-Cache, integrated Radeon graphics. **Windows reports 8 logical processors, not 16: simultaneous multithreading looks switched off in the BIOS** (worth checking: builds and tests would gain from it) | WMI |
| Motherboard | **Gigabyte A620I AX (Mini-ITX)**, BIOS F8c (2026-07-20); A620 chipset | WMI |
| Graphics | **AMD Radeon RX 7900 XTX, 24 GB** (RDNA 3, gfx1100), driver 32.0.23034.4; the processor's own Radeon graphics also active | WMI |
| Memory | **32 GB DDR5-6400** (2 x 16 GB Corsair CMH32GX5M2B6400C36); **both of the board's two slots used** | WMI |
| Storage | **1 TB Crucial P3 NVMe** (CT1000P3SSD8), one NTFS volume, 524 GB free | Storage cmdlets |
| Displays | ASUS XG27UCDMG, **3840 x 2160 at 240 Hz**, on the 7900 XTX; Samsung LS27D36x, 1920 x 1080 at 60 Hz, on the processor's graphics | WMI |
| Network | Realtek 2.5 GbE (connected), Realtek 8852CE Wi-Fi 6E (off), Bluetooth (on), Tailscale (connected) | NetAdapter |
| Operating system | Windows 11 Home, build 26200 | WMI |
| Local models | Ollama with qwen2.5 14B and 32B, qwen3 14B, qwen3-coder 30B, qwen2.5-vl 7B, llama3.2 3B, nomic-embed, gpt-oss 20B, mistral-small 24B | Ollama |
| Measured | 3B: 0.3 s an answer, 220 tokens/s; 14B: 0.9 s, 73 tokens/s; 30B class: 3.4 s, 14 tokens/s (Windows); the engineering bench per model in `work/eng_bench/` | `MIA_OS_NON_FUNCTIONAL_REQUIREMENTS.md`, the bench |
| Linux image (PoC 2) | Fedora 45 Kinoite as a bootc image builds with Ollama 0.24, ROCm 7.2.2 and Vulkan from Fedora's own packages; installs to a disk, boots, updates and rolls back in a VM | `MIA_OS_CORE_ARCHITECTURE_OPEN_QUESTIONS.md` |

**Not readable from software (gaps, Q-63):** the case and its card-length limit, the power supply's model and watts,
how many M.2 slots the board has free, and whether drive encryption is on (needs an administrator prompt).

**The other devices (from the repository's own records):** a Samsung Galaxy A54 phone (`docs/PHONE_MODEL_TEST.md`:
measured local models on it); Meta Ray-Ban Display glasses with the Neural Band, reached through the phone (the
Wearables Device Access Toolkit, `android-phone/`); the homestead's Raspberry Pi 5 node and ESP32 safety
microcontroller (`homestead/`, built and simulated, the node not yet installed); the Pi 5 with an AI HAT+ 2 planned
for MIA Core (`docs/HARDWARE.md`).

## 3. The philosophy (prompt §2)

| Principle | What it means here |
|---|---|
| Use strong hardware, never depend on it | Every capability has a path on lesser hardware (a smaller model, another node, a screen instead of voice); REQ-HW-004 |
| Grow by nodes | A capability record per device; work placed where it fits; adding a machine needs no redesign |
| Linux is the hardware layer | Drivers, power, scheduling, device access are Linux's; MIA reads and asks (Prompt 05 §1 of the hardware abstraction) |
| Measure, don't assume | Every number in a requirement comes from a measurement or is marked provisional; the bench and PER table are the method |
| Open and replaceable | Prefer hardware with mainline Linux drivers and open protocols (USB classes, Bluetooth LE, MQTT, Modbus); nothing that only works through a vendor's cloud |
| Safety below MIA | Anything physical (greenhouse, batteries, heaters) has its hard limits in its own controller; MIA adjusts within them (DEC-0185) |

## 4. Decisions proposed (full records in `MIA_OS_HARDWARE_TECHNOLOGY_EVALUATION.md` §3)

| DEC | Decision | Status |
|---|---|---|
| DEC-0201 | The reference PC as built is MIA OS's development machine and first target; no purchase is required for the MVP | PROPOSED |
| DEC-0202 | MIA's compute grows by adding nodes (a model-serving machine first), not cards; every device is a node with a capability record | PROPOSED, experimental until measured |
| DEC-0203 | A hardware capability registry fed only from Linux's own sources, published to MIA as read-only records | PROPOSED |
| DEC-0204 | Resource coordination: Linux schedules, MIA places models and decides what waits; one model job per GPU at a time, conversation first | PROPOSED |
| DEC-0205 | The device family's tiers: PC, phone, glasses, Pi nodes and homestead controllers now; everything else later or speculative, and never a dependency | PROPOSED |

## 5. What needs Zac (full list in `MIA_OS_HARDWARE_OPEN_QUESTIONS.md`)

- **Q-63:** the case, the power supply and the board's free M.2 slots (look, or a photo of the parts list).
- **Q-64:** approve "grow by nodes" and when a model-serving machine is wanted (it's the biggest hardware choice).
- **Q-65:** a 2 to 4 TB drive now (the one inexpensive upgrade that removes a real limit).
- **Q-66:** is a laptop or tablet in your plans? (Nothing assumes one.)
- **Q-67:** keep the second monitor on the processor's graphics? (It's fine; noted because it uses system memory.)
- **To do, not a question:** a USB stick (8 GB or more) for PoC 1, the graphics card under Fedora.

## 6. How it fits the earlier prompts

| Earlier decision | What Prompt 06 adds |
|---|---|
| DEC-0189 Fedora Atomic as a bootc image | The RX 7900 XTX is gfx1100, on AMD's supported list; Fedora 45 ships ROCm 7.2.x and ollama-rocm; PoC 1 still has to show it runs at Windows speed (REQ-HW-002) |
| DEC-0191 KDE's compositor on the PC | Two monitors on two different GPUs (dGPU and iGPU) is a case KWin handles; tested in PoC 3 |
| DEC-0193 Btrfs on LUKS2, models in /var | The 1 TB drive is the constraint: models in /var/lib/ollama, snapshots and test machines share it (Q-65) |
| DEC-0195 resources from systemd | The coordination split in `MIA_OS_HARDWARE_RESOURCE_COORDINATION.md` is built on it |
| DEC-0197 local specialists | The card holds one 32B model at a time; a second node is how a reviewer from another family stays loaded |
| DEC-0199 the Workroom | Parallel agents share one GPU; W1 measures how many before adding a node |

## 7. Boundaries

Model routing and inference services are Prompt 07's; the distributed architecture Prompt 12's; security and
encryption Prompt 13's; boot and updates Prompt 14's. This prompt sets the hardware facts and limits they work with.

## 8. Sources

Read 2026-11-17: AMD ROCm Linux system requirements (gfx1100 listed for the RX 7900 XTX), Fedora's package pages
(ollama-rocm 0.24 for Fedora 45; ROCm 7.1 in 44, 7.2 in 45), the Raspberry Pi AI HAT+ 2 reviews (Hailo-10H, 8 GB,
40 TOPS INT4; 1B models at single digits to tens of tokens a second), Meta Ray-Ban Display coverage (600 x 600 right-lens
display, Neural Band EMG input, the Wearables Device Access Toolkit and web paths in developer preview), and the
price sources in `docs/HARDWARE.md`. Each document lists the ones it rests on.

## 9. The documents

| Document | What it settles |
|---|---|
| `MIA_OS_DESKTOP_HARDWARE_REQUIREMENTS.md` | The five workstation profiles, minimum to expandable |
| `MIA_OS_CPU_AND_ARCHITECTURE_EVALUATION.md` | x86-64 first; ARM for Pis and phones; RISC-V watched |
| `MIA_OS_GPU_AND_AI_ACCELERATION_STRATEGY.md` | ROCm and Vulkan on AMD, what fits in 24 GB, NPUs and accelerators |
| `MIA_OS_MEMORY_AND_STORAGE_REQUIREMENTS.md` | Memory and disk budgets, the 1 TB limit |
| `MIA_OS_ANDROID_HARDWARE_INTEGRATION.md` | The phone's role and limits |
| `MIA_OS_WEARABLE_AND_SPATIAL_HARDWARE.md` | The glasses and what comes after |
| `MIA_OS_EMBEDDED_AND_HOMESTEAD_HARDWARE.md` | Pis, ESP32s, sensors, the safety controller |
| `MIA_OS_PERIPHERAL_COMPATIBILITY.md` | Monitors, audio, cameras, input, printers, USB |
| `MIA_OS_NETWORK_AND_DISTRIBUTED_HARDWARE.md` | Ethernet, Wi-Fi, Tailscale, LoRa, the node network |
| `MIA_OS_VIRTUALIZATION_AND_ISOLATION.md` | KVM, containers, the lab's isolation, the Workroom later |
| `MIA_OS_POWER_THERMAL_AND_HARDWARE_HEALTH.md` | Power, heat, SMART, the UPS |
| `MIA_OS_HARDWARE_DISCOVERY_AND_CAPABILITY_REGISTRY.md` | DEC-0203 in detail |
| `MIA_OS_HARDWARE_RESOURCE_COORDINATION.md` | DEC-0204 in detail |
| `MIA_OS_HARDWARE_COMPATIBILITY_MATRIX.md` | What runs on what, with support levels |
| `MIA_OS_HARDWARE_TECHNOLOGY_EVALUATION.md` | Each technology judged, and the decision records |
| `MIA_OS_HARDWARE_ROADMAP.md` | The stages, with what triggers each |
| `MIA_OS_HARDWARE_FAILURE_AND_DEGRADED_OPERATION.md` | What happens when each part fails |
| `MIA_OS_HARDWARE_ARCHITECTURE_DIAGRAMS.md` | The ten diagrams the prompt asks for |
| `MIA_OS_HARDWARE_ACCEPTANCE_CRITERIA.md` | How each requirement is checked |
| `MIA_OS_HARDWARE_OPEN_QUESTIONS.md` | Questions, gaps and the tests still to run |

## Across devices (Prompt 12, 2026-11-18)

Each machine's place among his devices (hub, full engine, endpoint, node, controller, sensor) is in `MIA_OS_DEVICE_CLASS_AND_RUNTIME_ARCHITECTURE.md`; the support level of each in `MIA_OS_DEVICE_SUPPORT_MATRIX.md`.

## Reliability (Prompt 14, 2026-11-18)

A UPS and an off-PC backup drive are the reliability purchases (Q-96, Q-97).
