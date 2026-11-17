# MIA OS: desktop and workstation hardware (Prompt 06 §3)

*Claude (Opus), 2026-11-17. Planning only. Builds on the profiles in `MIA_OS_DEVICE_AND_HARDWARE_REQUIREMENTS.md` §2
(Prompt 04), which stay; this adds the five configurations the prompt asks for and the PC as built.*

## 1. Five configurations

Model sizes are 4-bit (Q4_K_M) as Ollama ships them. "Measured" numbers are the reference PC's on Windows; Linux is
re-measured in PoC 1.

| | 1. Minimum viable | 2. Recommended everyday | 3. AI development workstation | 4. High-performance local AI | 5. Expandable |
|---|---|---|---|---|---|
| Who | MIA OS without local models (a spare machine, a VM) | a person using MIA every day | **Zac's PC as built** | specialists and reviewers loaded together, larger models | grows by adding parts and nodes |
| Processor | 4 cores x86-64 | 6 to 8 cores | Ryzen 7 9800X3D, 8 cores | 8 to 16 cores | a desktop board (ATX), 8+ cores |
| Memory | 8 GB | 16 to 32 GB | 32 GB DDR5-6400 | 64 to 128 GB (or 128 GB unified) | 4 slots, 64 GB+ |
| Graphics | none (models from another node) | 12 to 16 GB VRAM | RX 7900 XTX 24 GB | 48 GB+ VRAM in one place, or a second node | 2 full slots, 1200 W supply |
| Storage | 128 GB SSD | 1 TB NVMe | 1 TB NVMe (tight) | 2 to 4 TB NVMe | 2+ M.2 slots |
| Models it runs | none locally; asks a node | 3B and 14B | up to 32B, one at a time | 70B dense, 120B MoE, two 32B at once | — |
| Network | 1 GbE or Wi-Fi | 1 GbE | 2.5 GbE | 2.5 GbE | 2.5 to 10 GbE |
| Status | REQ-HW-005 (provisional) | recommended | **verified** | a recommendation (Q-64) | for a future build |

**How 4 is reached from 3:** not inside this PC (one slot, two memory slots, both full). Either a second machine
(a 128 GB unified-memory mini PC, `docs/HARDWARE.md`) beside it, or a future rebuild on an ATX board with two
full-length slots. DEC-0202 prefers the second machine: it adds a node without touching a working PC.

## 2. The PC's real constraints

| Constraint | Effect | What to do |
|---|---|---|
| One graphics slot | one 24 GB card; a 32B model and its reviewer can't both be loaded | a model node (DEC-0202); or swap for a larger single card (small gain) |
| Two memory slots, both full | 64 GB means replacing both sticks | wait for prices (`docs/HARDWARE.md`) |
| 1 TB drive, 524 GB free on Windows | models, packs, snapshots and test machines compete; dual boot halves it | a 2 to 4 TB drive (Q-65) |
| SMT appears off | 8 threads instead of 16 for builds and tests | check the BIOS setting (no cost) |
| Case and power supply unknown | a larger card can't be judged | Q-63 |

## 3. Requirements

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-HW-007 | MIA OS shall run its MVP on configuration 3 (the reference PC) with no hardware added. | Must | MVP | PC | New | M: the PER table on the image (PoC 1, then 14) | DEC-0201 → 06 |
| REQ-HW-008 | MIA OS shall install on configuration 1 and serve its models from another node it's paired with. | Should | R1 | PC | New | M: a VM with no GPU asking the PC | DEC-0202 → 12 |
| REQ-HW-009 | Before recommending hardware, MIA shall read what the device has (slots, memory, power where readable) and never recommend what can't be fitted. | Must | R1 | PC | New (this prompt's own mistake, corrected 2026-11-17) | T: a capability record with one slot gets no "add a card" advice | DEC-0203 → 06 |

## 4. Sources

The PC's own readings (`MIA_OS_HARDWARE_AND_PLATFORM_STRATEGY.md` §2); Gigabyte's A620I AX is Mini-ITX with one
PCIe x16 slot and two DIMM slots (the board's product page; confirm against the manual for M.2 count, Q-63).
