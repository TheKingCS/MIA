# MIA OS: graphics and AI acceleration (Prompt 06 §5)

*Claude (Opus), 2026-11-17. Planning only. Model routing and inference services are Prompt 07's; this sets what the
hardware can do and the paths to it.*

## 1. The card: Radeon RX 7900 XTX, 24 GB (verified)

| Path | On Windows today | On Fedora (MIA OS) | Evidence |
|---|---|---|---|
| ROCm (HIP) | Ollama's ROCm build; measured (PER table) | Fedora 45's ROCm 7.2.x and `ollama-rocm` 0.24; gfx1100 is on AMD's supported list | PoC 2 built the image with them; **PoC 1 (running it) waits on a USB stick** |
| Vulkan | available | Mesa RADV, in the image | PoC 2 |
| Display | 4K 240 Hz | KWin on amdgpu, mainline | standard |

**What fits in 24 GB** (4-bit): one 32B model with a normal context (about 20 GB), or a 14B and a 7B together, or
the 3B everyday model alongside a 14B. Two 32B models don't fit, which is why a specialist and its reviewer swap
today (the swap costs seconds per load).

**The integrated graphics** (the 9800X3D's Radeon) drives the second monitor. It shares system memory. It can also
run a small model through Vulkan if the card is busy; measure before relying on it (Prompt 07).

## 2. Accelerators across the device family

| Device | Accelerator | What it runs | Status |
|---|---|---|---|
| PC | RX 7900 XTX | everything up to 32B | verified |
| Model node (proposed) | Ryzen AI Max+ 395: RDNA 3.5 GPU on 128 GB unified memory, plus an NPU | 70B dense slowly (5 to 7 tokens/s), 120B MoE well (about 31 to 34), several models loaded at once | recommended, DEC-0202 |
| Pi 5 + AI HAT+ 2 | Hailo-10H, 8 GB, 40 TOPS INT4 | 1B to 3B models (vendor: 30 to 50 tokens/s for 1B; independent tests single digits to about 8) | planned; measure on arrival |
| Phone (Galaxy A54) | Exynos CPU (no NPU path used) | 0.5B to 1.5B locally | measured (`docs/PHONE_MODEL_TEST.md`) |
| Glasses | none for MIA | nothing; cards and input only | by design |

**NPUs on the PC:** the 9800X3D has none. Ryzen AI NPUs (on the model node) need AMD's XDNA driver, mainline in
recent kernels; whether Ollama or llama.cpp use it is Prompt 07's question.

## 3. Strategy

1. **One model job per GPU at a time** (DEC-0204): conversation first, then specialists, then background work.
2. **Never require a specific vendor.** ROCm is the fast path on AMD; Vulkan is the portable fallback (llama.cpp
   and Ollama both support it); CPU is the last resort. A capability record says which paths a device has.
3. **Grow by nodes** (DEC-0202): the next accelerator is a second machine, not a second card.
4. **Measure every claim** on MIA's own bench before a model or device is trusted (DEC-0197, DEC-0200).

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-HW-011 | Each device shall expose which acceleration paths it has (ROCm, Vulkan, CUDA, NPU, CPU) and how much memory each has, and model placement shall use only those. | Must | R1 | All | New | T: a fake registry with no ROCm gets a Vulkan or CPU placement | DEC-0203, → 07 |
| REQ-HW-012 | With the GPU unavailable, MIA shall answer with a smaller model on the CPU or another node, and say so. | Must | MVP | PC | Exists (FW-12: the smaller model answers and says it ran on the processor; measured by unloading the driver at MV-01) | M: unload the driver in a VM | DEC-0204, REQ-HW-004 → 06 |

## 4. Sources

AMD ROCm Linux system requirements (gfx1100); Fedora packages for ollama-rocm and rocm (F44: 7.1, F45: 7.2);
PoC 2's build log; Hailo-10H reviews (CNX Software, Hardware Corner); Strix Halo measurements (compute-market,
terminalbytes); `docs/PHONE_MODEL_TEST.md`.
