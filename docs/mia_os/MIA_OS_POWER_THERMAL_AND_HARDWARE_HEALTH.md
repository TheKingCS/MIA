# MIA OS: power, heat and hardware health (Prompt 06 §13)

*Claude (Opus), 2026-11-17. Planning only. Resource rules: Prompt 05's resource management §4.*

## 1. What's watched, and from where (Linux's own sources)

| Signal | Source on Linux | MIA's response |
|---|---|---|
| GPU temperature, power, fan, memory use | amdgpu's hwmon in sysfs; `rocm-smi`/`amd-smi` | defer background model work when hot (homeostasis) |
| CPU temperature | k10temp | defer builds |
| Drive health | SMART (smartmontools), NVMe health log | warn on wear or errors; back up first |
| Memory errors | none on consumer DDR5 without ECC | — |
| Power events | UPower; a UPS through NUT | on battery: finish the write, pause model work, shut down cleanly at a threshold |
| Updates and restarts | the image's update timer (Prompt 14) | never during a long job; Windows today restarted mid-bench (2026-11-17) |

## 2. Recommendations

- **A UPS** (about $150 to $250) with USB so NUT can tell MIA: long overnight work (Night School, the bench) survives
  a blip and ends cleanly on a real outage.
- **The power supply** isn't known (Q-63). The 7900 XTX draws up to about 355 W with spikes; the build has been
  stable under the bench, which is evidence it's adequate for this card.
- **Heat in a small case:** a Mini-ITX case with a 355 W card is the place heat would show first. MIA logs GPU
  temperature during long jobs and eases off before throttling (measure on the image).

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-HW-024 | MIA shall pause background model work when the GPU or CPU passes a temperature threshold, and resume when it cools, logging both. | Should | R1 | PC | Partial (homeostasis eases off by load) | T: a simulated hwmon reading | DEC-0204, → 14 |
| REQ-HW-025 | With a UPS reporting battery, MIA shall stop starting long work and shut the PC down cleanly before the battery runs out. | Should | R1 | PC | New | M: NUT's test mode | → 14 |
| REQ-HW-026 | Drive wear or errors from SMART shall reach him through the communication gate with a backup offered. | Must | R1 | PC | New | T | → 14 |
