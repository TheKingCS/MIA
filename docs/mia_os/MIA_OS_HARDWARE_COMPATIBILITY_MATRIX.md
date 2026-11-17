# MIA OS: hardware compatibility and support matrix (Prompt 06 §16)

*Claude (Opus), 2026-11-17. Planning only. Levels: **Verified** (run here), **Supported** (documented upstream,
to be verified), **Best effort** (should work, not tested), **Unsupported** (won't be worked around).*

## 1. Platforms

| Platform | MIA's role | Level | Evidence |
|---|---|---|---|
| Fedora Kinoite (bootc) x86-64 on the reference PC | MIA OS | Supported (VM verified; real hardware is PoC 1) | PoC 2 |
| Windows 11 on the reference PC | MIA today | Verified | daily use |
| Ubuntu 26.04 x86-64 | fallback base (DEC-0189) | Best effort | — |
| Android (Galaxy A54) | the phone app | Verified | `docs/PHONE_MODEL_TEST.md` |
| Raspberry Pi OS (Pi 5) | homestead node, MIA Core | Supported | homestead's own tests |
| Meta Ray-Ban Display (via the phone) | cards and input | Verified | the app |

## 2. Accelerators

| Hardware | ROCm | Vulkan | CUDA | Level for MIA |
|---|---|---|---|---|
| AMD RX 7900 XTX (gfx1100) | yes | yes | — | Verified (Windows); Supported (Fedora) |
| AMD Radeon AI PRO R9700, W7900 | yes | yes | — | Supported |
| AMD Ryzen AI Max+ 395 (RDNA 3.5) | yes (recent) | yes | — | Supported |
| Older AMD (RDNA 2) | partial | yes | — | Best effort (Vulkan) |
| Nvidia (RTX 30/40/50) | — | yes | yes | Best effort: would add a second stack to maintain |
| Intel Arc | — | yes | — | Best effort (Vulkan) |
| Hailo-10H (AI HAT+ 2) | — | — | — | Supported on the Pi, its own runtime |
| No GPU | — | — | — | Verified path: CPU or another node |

## 3. Peripherals and devices

| Kind | Requirement to be supported |
|---|---|
| Audio, cameras | USB class devices (UAC, UVC) or PipeWire-supported internal |
| Printers, scanners | IPP Everywhere / eSCL |
| Sensors | BLE with a published profile, I2C/1-Wire on the Pi, MQTT |
| Radios | Meshtastic devices over serial |
| Anything needing a vendor's cloud or a Windows-only driver | Unsupported |
