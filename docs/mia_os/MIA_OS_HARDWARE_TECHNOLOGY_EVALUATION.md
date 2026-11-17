# MIA OS: hardware technology evaluation and decision records (Prompt 06 §17, §23)

*Claude (Opus), 2026-11-17. Planning only. Each technology in the prompt's fourteen fields, compressed into a table
where they repeat; the decision records follow. Nothing here is approved until Zac says so (DEC-0201 to 0205 are
PROPOSED).*

## 1. Technologies

| Technology | Purpose | Alternatives | For | Against | Linux | Recommendation |
|---|---|---|---|---|---|---|
| ROCm | GPU compute on AMD | Vulkan, CUDA | fastest path on the 7900 XTX; in Fedora | version churn; card support lists change | Fedora 44/45 packages | **Use**, with Vulkan as fallback |
| Vulkan (llama.cpp/Ollama) | portable GPU compute | ROCm | works on any modern GPU, in Mesa | slower than ROCm on AMD for some models | mainline | **Keep as fallback** |
| Ollama | model runner | llama.cpp server, vLLM | in use; Fedora package with ROCm | one model queue, limited batching | packaged | **Keep** (Prompt 07 revisits) |
| vLLM | high-throughput serving | Ollama | batching for many agents | heavy; ROCm support narrower on consumer cards | pip/containers | **Watch** for the Workroom |
| A second model node (Strix Halo, 128 GB) | scale-out inference | a bigger card, a rebuild | adds capacity without touching the PC; holds several models | about $3,300 to $4,350 now; slow on dense 70B | x86-64, same image | **Recommend when the bench or Workroom shows the need** (Q-64) |
| A bigger single card (R9700 32 GB) | more VRAM in the PC | a node | same box | only +8 GB; card length and supply unknown | supported | **Not recommended alone** |
| A 2 to 4 TB NVMe | room for models, packs, snapshots | — | removes a real limit cheaply | — | mainline | **Recommend** (Q-65) |
| 64 GB DDR5 | headroom | — | VMs, browser agents | both sticks replaced; prices high | — | **Defer** |
| KVM/QEMU | test machines | VirtualBox | mainline; used in CI | needs AMD-V on | mainline | **Use** |
| NUT + a USB UPS | power events | none | clean shutdowns | cost | packaged | **Recommend** |
| smartmontools | drive health | — | standard | — | packaged | **Use** |
| Hailo-10H | Pi's local model | Pi CPU | 10x faster than the Pi's CPU | small models only; its own runtime | vendor packages | **Use for MIA Core's small model only** |
| Meta Wearables Device Access Toolkit | the glasses | Meta's web path | in use | developer preview, may change | Android side | **Keep; parity guards it** |
| Meshtastic LoRa | off-grid messages | — | no internet needed | low bandwidth | serial | **Use** for the homestead |

Evidence for each is cited in the topic document (GPU, memory, embedded, wearables) and `docs/HARDWARE.md`.

## 2. Rejected

| Option | Why |
|---|---|
| A second graphics card in this PC | one PCIe x16 slot (verified); impossible without a rebuild |
| GPU passthrough to VMs | one consumer card; no SR-IOV; breaks the host's models |
| Nvidia for MIA OS | a second compute stack to maintain beside ROCm; nothing needs it |
| MIA OS on the phone | the phone stays Android (DEC-0205) |
| Hardware needing a vendor cloud | violates local-first (E3) |

## 3. Decision records

### DEC-0201: the reference PC as built is MIA OS's first target
- Context: Prompt 06 asks for the workstation baseline; the PC was read on 2026-11-17.
- Requirements: REQ-HW-001, 002, 007.
- Options: buy before starting; start on the PC as built.
- Evidence: every MVP workload measured on it; the image builds and boots (PoC 2).
- Selected: start on the PC as built; no purchase required for the MVP.
- Rejected: hardware first (nothing measured needs it yet).
- Consequences: 32B is the largest model; specialists and reviewers swap on the card.
- Risks: PoC 1 fails on Fedora (then Ubuntu, DEC-0189's fallback).
- Reversibility: full.
- Revisit when: PoC 1 fails, or the bench/Workroom shows a measured shortfall.

### DEC-0202: grow by nodes, not cards
- Context: the PC has one graphics slot and two full memory slots.
- Requirements: REQ-HW-008, 021, 022; DEC-0197, DEC-0199.
- Options: a second machine for models; a bigger single card; a rebuild on an ATX board.
- Evidence: the board (verified); Strix Halo measurements (5 to 7 tokens/s dense 70B, 31 to 34 MoE 120B).
- Selected: every device is a node with a capability record; the next AI hardware is a model-serving node.
- Rejected: a bigger card alone (+8 GB); a rebuild now (disrupts a working PC).
- Consequences: Prompt 12's distributed design must treat inference as a remote service from day one.
- Risks: network latency (small on 2.5 GbE); a second machine to keep updated (same image).
- Reversibility: full (a node can be removed).
- Revisit when: a rebuild is planned anyway, or a single card with 48 GB+ becomes affordable.
- Status: PROPOSED, experimental until W1 and the bench measure the need.

### DEC-0203: the capability registry reads only Linux's own sources
- Context: MIA must know its hardware without driving it (Prompt 05).
- Requirements: REQ-HW-009, 011, 019, 027, 028; REQ-DEV-005.
- Options: MIA probes devices; MIA reads Linux's sources; a third-party inventory agent.
- Selected: a reader in the runtime builds one record per device from sysfs, udev, D-Bus services and read-only
  helper operations, each field with its source.
- Rejected: probing (duplicates Linux, risks touching hardware); third-party agents (another service, telemetry).
- Risks: a source changes format (each reader is tested against fixtures).
- Reversibility: full. Revisit when: a source is missing on a target device.

### DEC-0204: Linux schedules, MIA places models and decides what waits
- Context: one GPU, many model users (conversation, specialists, Workroom, Night School).
- Requirements: REQ-HW-012, 024, 029, 030.
- Options: let every caller hit the runner; MIA queues and orders.
- Selected: cgroups and the kernel do scheduling; MIA orders model jobs, one per GPU at a time, conversation first.
- Rejected: free-for-all (a bench stalls a conversation, measured on Windows).
- Risks: a queue bug blocks everything (a watchdog and a fall-through to direct calls).
- Reversibility: full. Revisit when: a runner with real batching (vLLM) is adopted.

### DEC-0205: the device family's tiers
- Context: the prompt asks to separate current, feasible and speculative hardware.
- Selected: **current**: the PC, the phone (Android with MIA's app), the glasses through the phone, the homestead's
  Pi node and safety controller; **next**: a model node, the Pi running MIA Core; **later**: a laptop, a smart
  display, the truck; **speculative**: MIA's own glasses or hardware. Nothing depends on a later or speculative device.
- Revisit when: Zac buys or plans one of them (Q-66).
