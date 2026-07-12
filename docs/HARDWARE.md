# M.I.A. Hardware Guide

This document tracks concrete hardware recommendations and known
constraints for building M.I.A. Core on a Raspberry Pi 5. Update it as
parts are chosen/tested — it should stay the source of truth for "what
hardware does this software assume exists."

## Core platform

- **Raspberry Pi 5** (8GB recommended — the AI HAT+ 2 has its own
  dedicated RAM, but 8GB on the Pi itself gives headroom for the GUI,
  sensor polling, and multiple modules running at once)
- **Raspberry Pi Active Cooler** — required under the AI HAT+ 2 per
  Raspberry Pi's own hardware assembly instructions; plan enclosure
  height around this stack

## AI acceleration

**Recommended: Raspberry Pi AI HAT+ 2** (Hailo-10H accelerator, ~$130)

- 40 TOPS (INT4) inference performance
- **8GB of dedicated onboard LPDDR4X RAM**, separate from the Pi's
  system memory — this is the deciding factor: local LLM/VLM inference
  doesn't compete with the Pi's own RAM for the GUI and other modules
- Explicitly positioned by Hailo for local voice-to-action agents and
  smart search/captioning over a fixed dataset — a strong match for
  "conversational assistant that explains how to use the device"
- Realistic model size on this hardware: 1–7B parameter models,
  LoRA-fine-tunable for a device-specific personality/knowledge set.
  This is not cloud-LLM-class general reasoning — plan the Assistant's
  scope accordingly (device help, survival reference lookup, structured
  Q&A) rather than open-ended conversation
- Setup path: Hailo's `hailo-ollama` runtime + a local frontend (Open
  WebUI is the reference example in Hailo's own docs; M.I.A.'s
  Assistant module will eventually talk to this backend directly
  instead)

**Known constraint — plan storage around this:** the AI HAT+ 2 and any
NVMe M.2 storage HAT both require the Pi 5's single PCIe interface.
They **cannot both run at full speed simultaneously** without an
unofficial PCIe-switch board, which the Pi community reports as
unreliable (detection failures, boot issues) for this exact combination.
Do not build the primary storage path around NVMe if the AI HAT+ 2 is
installed — see Storage below.

## Storage

**Recommended split, not a single drive:**

- **Boot/OS: high-endurance microSD, 512GB–1TB** (e.g. SanDisk High
  Endurance, Samsung PRO Endurance). Keeps the OS and application code
  on a card rated for continuous read/write cycles.
- **Bulk data: USB 3.0 SSD, 1–4TB**, mounted separately for the
  Reference Library, maps, media, backups, and anything write-heavy
  (journal, logs, sensor data, voice memos). USB doesn't contend with
  the AI HAT+ 2 for PCIe lanes, and a USB SSD is trivially portable —
  it's also the natural fit for the "dock to a computer" goal, since the
  same drive can be pulled and mounted on a desktop directly.

This split also means an SD card failure (the classic Pi failure mode)
doesn't take your reference library or journal with it — only the OS,
which is reinstallable from the M.I.A. repo.

## Voice interface

**Recommended: physical push-to-talk button, not always-listening.**

- A single momentary GPIO button, wired as a hardware interrupt (not
  polled), for near-zero idle power draw and instant response
- Avoids wake-word false triggers and the extra always-on compute/power
  budget of continuous audio processing — both matter for a
  battery-powered field device
- Pairs a basic USB or I2S microphone with the Pi 5's headphone jack or
  a small I2S DAC/amp for TTS output

**STT/TTS engine (decided, docs/ROADMAP.md milestone 5.3):** Vosk
(speech-to-text) + Piper (text-to-speech), both offline and CPU-only —
see core/voice_manager.py's docstring for why over whisper.cpp/other
alternatives. Requires the system `libportaudio2` package (via apt or
equivalent) on the actual device for mic capture/playback
(`sounddevice`'s Linux wheel does not bundle PortAudio, unlike its
Windows/macOS wheels) — add this to the Pi image setup steps, since
`deploy/install_kiosk.sh` deliberately doesn't install system packages.
Model files themselves are fetched by `deploy/download_voice_models.sh`
into `voice_models/` (gitignored).

## Boot & kiosk

- Autologin + a systemd service launching M.I.A. directly in a minimal
  Wayland/X session (kiosk mode) — no desktop shell visible. Covered in
  `docs/ROADMAP.md` Phase v0.2.

## Docking

- USB-C to a computer for file transfer / extended use, per the
  project's stated goal. Gadget-mode (Pi 5 presenting as a USB mass
  storage or network device) is the simplest first implementation;
  a full networked client is a possible v2+ direction, not required now.

## Open questions to revisit as hardware is acquired

- Exact mic/speaker hardware once voice interface is actually built
- GPS module choice for Navigation (many options; defer until that
  phase)
- LoRa/SDR/radio hardware for Communications — defer until that phase,
  since protocol choice (Meshtastic vs. custom) affects the hardware pick
- Battery/UPS HAT choice for Power section — needs to report real
  telemetry (voltage/current), not just presence, so pick one with a
  documented I2C interface
