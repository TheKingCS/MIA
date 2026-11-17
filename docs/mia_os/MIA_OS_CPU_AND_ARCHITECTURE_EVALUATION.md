# MIA OS: processor architectures (Prompt 06 §4)

*Claude (Opus), 2026-11-17. Planning only.*

## 1. Recommendation

**x86-64 for the PC and any model node; ARM64 (aarch64) for the Pi nodes and the phone; RISC-V watched, not
targeted.** MIA's engine is Python and runs on all three already (the phone through Chaquopy on ARM64, the Linux CI
on x86-64); what differs per architecture is the model runner and the drivers, not MIA.

## 2. Comparison

| | x86-64 (AMD Zen 5) | ARM64 desktop/server | ARM64 Raspberry Pi 5 | RISC-V |
|---|---|---|---|---|
| Where in MIA | the PC (verified); a model node | none owned | homestead node, MIA Core later | none |
| Linux support | complete; Fedora's primary | good (Fedora aarch64) | Raspberry Pi OS first; Fedora works with caveats | early |
| GPU compute | ROCm and Vulkan for the RX 7900 XTX | vendor-specific | none (the Hailo NPU on the HAT) | none useful |
| MIA's engine | runs (Windows today, Linux CI) | would run | runs headless (MIA Core) | untested |
| Image build | bootc, Fedora Kinoite (PoC 2 green) | bootc builds aarch64 too | Raspberry Pi OS image, not bootc (Prompt 14) | — |
| Risk | low | no hardware to test on | the Pi's own OS lags Fedora; MIA Core must stay small | ecosystem immaturity |

## 3. Notes

- **The 9800X3D's 3D V-Cache** helps compilation and tests more than inference; inference is the GPU's.
- **8 cores reported as 8 logical processors:** SMT appears off (strategy §2). Turning it on is a BIOS switch;
  measure the suite's time before and after.
- **Model nodes:** a Ryzen AI Max+ 395 is x86-64 with RDNA 3.5 graphics and 128 GB unified memory, so the same
  image, the same ROCm and Vulkan paths and the same MIA code apply. An Apple or Nvidia ARM box would mean a second
  inference stack; not recommended (DEC-0202).

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-HW-010 | MIA's engine shall stay architecture-neutral Python; anything architecture-specific (model runners, drivers) sits behind the capability registry. | Must | MVP | All | Exists (engine), New (registry) | T: the suite on x86-64 CI and the phone's ARM64 build | DEC-0203 → 06 |
