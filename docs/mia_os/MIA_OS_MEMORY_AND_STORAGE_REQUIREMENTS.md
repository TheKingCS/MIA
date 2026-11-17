# MIA OS: memory and storage (Prompt 06 §6)

*Claude (Opus), 2026-11-17. Planning only. The filesystem layout is Prompt 05's (DEC-0193); this sets the budgets.*

## 1. Memory on the PC (32 GB, verified)

| Use | Typical | Notes |
|---|---|---|
| Fedora with KDE | 2 to 3 GB | measured on similar systems; re-measure on the image |
| MIA runtime and web surfaces | 1 to 2 GB | the runtime came up with 95 services in PoC 4 |
| Her browser (Edge or Chromium, a few tabs) | 1 to 3 GB | more with Workroom agents (about 0.3 to 0.5 GB each) |
| Test machines (PoCs, the lab's checks) | 4 to 8 GB each | one at a time |
| Model spill to system memory | 0 when a model fits the card | a 70B can't run here usefully |
| Integrated graphics (second monitor) | a few hundred MB | taken from system memory |

**Verdict:** 32 GB is enough for the MVP. It gets tight with a test machine, several browser agents and a build at
once; 64 GB (two new sticks) is the remedy, deferred for price (`docs/HARDWARE.md`).

## 2. Storage (1 TB NVMe, 524 GB free, verified)

| Holds | Size | Where (DEC-0193) |
|---|---|---|
| The MIA OS image and two rollback deployments | 15 to 25 GB | /usr, /ostree |
| Models (today's set: 3B to 32B, nine models) | about 110 GB | /var/lib/ollama |
| His data (records, vault, photos) | grows; tens of GB | ~/ (his home) |
| Offline packs (Kiwix, the Forge's) | 10 to 100+ GB | /var or a data volume |
| Snapshots (Btrfs) | 10 to 20% of what changes | the same volume |
| Test machines and the lab's worktrees | 20 to 60 GB | /var |
| Windows, while dual-booting | its current ~400 GB | its own partition |

**Verdict:** on one 1 TB drive, dual boot with today's Windows use leaves under 500 GB for Fedora, models and packs.
That works for the MVP and fills within months. A second NVMe drive (2 to 4 TB) given to Fedora removes the problem
and keeps Windows untouched (Q-65).

## 3. Other devices

| Device | Memory | Storage |
|---|---|---|
| Phone (Galaxy A54) | 8 GB (measured models to 1.5B) | the app's records; models 0.4 to 1 GB |
| Pi 5 node | 8 GB; the HAT+ 2 has its own 8 GB | NVMe on the Pi's PCIe, or a high-endurance card; records sync to the PC |
| ESP32 controller | its own, firmware only | none of MIA's |

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-HW-013 | MIA shall show how its disk is used (models, packs, snapshots, records) and warn before any one would push free space under 10%, offering what can be removed. | Must | R1 | PC | Partial (backups check space) | T | DEC-0193, → 14 |
| REQ-HW-014 | Models and packs shall be removable and re-fetchable without touching his records; his records never share a deletion path with them. | Must | MVP | PC | New | T | DEC-0193 → 06 |
