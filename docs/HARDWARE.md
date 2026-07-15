# M.I.A. Hardware Guide

This document tracks concrete hardware recommendations and known
constraints for building M.I.A. Core on a Raspberry Pi 5. Update it as
parts are chosen/tested — it should stay the source of truth for "what
hardware does this software assume exists."

**2026-07-15: this document now also covers Project 2 ("Home Cloud"),
see its own section below** — its hardware started being sourced this
date, and `docs/VISION.md`'s new "Core/Home split" section is the
architectural decision this hardware exists to support: Core stays
fully offline-capable on its own; Home is where a genuinely bigger
model lives for deep reasoning and remote/streaming access. Read that
section first for *why* this split exists before treating either half
of this document as the whole picture.

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

**2026-07-15: realistic offline capability, decided (see `VISION.md`'s
"Core/Home split" for the full reasoning) — Core is scoped to keep,
not expand:**

- **Reliable offline on this hardware**: tool-calling/action execution
  (the full registry, `docs/ASSISTANT_CAPABILITIES.md`), conversational
  replies/personality/proactive behaviors, retrieval-grounded device
  help, voice in/out, persistent memory, and — plausibly, still
  unverified on real hardware — lightweight on-device image
  classification (species/plant ID), since Hailo NPUs' origin is vision
  inference, arguably a better fit for this chip than text generation.
- **Not reliable on this hardware, confirmed by this project's own
  2026-07-14 experiment** (`qwen2.5:7b` — right at this HAT's realistic
  ceiling — tested worse than the current 3B model on both accuracy and
  speed): deep, open-ended, multi-step reasoning, or robustly handling
  a long/rich system prompt. **Don't expect reaching the HAT's 7B
  ceiling to fix this project's already-documented prompt-fragility
  gotchas** (`docs/ROADMAP.md`) — that needs a different model size
  class entirely (13B+), which needs Project 2's hardware, not a bigger
  HAT. This is a physics/market ceiling for edge NPUs generally, not a
  gap specific to this part.

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
  storage or network device) is the simplest first implementation.
- **2026-07-15: a networked connection to Project 2 (Home) is now a
  planned direction, not just a "possible v2+" maybe** — see
  `VISION.md`'s "Core/Home split" and the new Project 2 section below.
  Physical USB-C docking (file/Expedition-data sync, already built,
  `core/expedition_sync.py`) and a networked link to Home for the
  reasoning hand-off are two different mechanisms serving two different
  needs — docking doesn't need to become networked for the hand-off to
  work, and the hand-off doesn't require physical docking either.

## Project 2: Home Cloud compute node (2026-07-15, hardware being sourced)

The other half of the Core/Home split decided in `VISION.md` — where
deep reasoning and the browser/app streaming access mode are meant to
live, per that document's own reasoning for why Core (Pi5+HAT) can't
do this itself. Software is entirely unbuilt; this section is the
hardware plan only.

**In progress**: CPU **AMD Ryzen 7 9800X3D** (Zen 5, strong single-
thread performance, runs cool for its class) + GPU **AMD Radeon RX
7900 XTX (24GB VRAM)**, being built by a family member as of
2026-07-15. 24GB is genuinely generous headroom for local LLM
inference — comfortably enough for a 30B-class quantized model, likely
more, which is exactly the size class `VISION.md` identifies as needed
to meaningfully outperform Core's 1–7B ceiling on prompt robustness.

**Real caveat, not a blocker: AMD means ROCm, not CUDA.** The 7900
XTX is one of ROCm's officially-supported targets (gfx1100) — unlike
older/unsupported AMD parts, this is a real, working path — but ROCm's
setup has historically been more hands-on than NVIDIA's CUDA path
(driver installation, occasionally an explicit GPU-target environment
variable). Budget real setup time the first time Ollama gets pointed
at this GPU; don't assume it's zero-friction the way the portable
Ollama-on-CPU install was for Core.

**Recommended OS: Ubuntu LTS**, not Windows — ROCm's Linux support is
more mature/better-documented, and it keeps this machine consistent
with the rest of this project's Linux-first tooling. Windows ROCm
support does exist if this machine needs to double as a general
desktop; that's a real trade-off to weigh, not a wrong choice, just not
the smoothest AI-specific path.

**Rest of the build** (not yet finalized — update this section once
parts are confirmed):
- Motherboard: AM5 socket (required for 9800X3D), PCIe 4.0/5.0 x16 slot
  for the GPU, confirm BIOS supports 9800X3D before assembly (some AM5
  boards needed a BIOS update for newer Ryzen chips).
- RAM: 32–64GB DDR5, dual-channel (matched kit, not a single stick).
- Storage: 1–2TB NVMe SSD (OS + Ollama model files — individual models
  can be tens of GB each).
- PSU: 850–1000W, 80+ Gold or better — the 7900 XTX has real transient
  power spikes even though sustained draw is lower; don't undersize
  this.
- Cooling: a solid air cooler is sufficient for the 9800X3D (no AIO
  needed); case airflow matters more for the GPU.
- Case: must physically fit the 7900 XTX (300mm+ in most versions).

**Not yet designed**: the actual Core→Home hand-off mechanism, and the
browser/app streaming interface — both flagged as unbuilt in
`VISION.md`'s "Core/Home split" section. This hardware existing doesn't
imply either is close to done.

## Camera (2026-07-14 addition, not yet chosen)

Added by the wearable-companion vision update (`docs/VISION.md`) —
strap-mounted, alongside the speaker/mic. Two real jobs, likely
different priorities:

- **Photo capture for Memories/trip recaps** — straightforward, any
  Pi-compatible camera module (CSI ribbon or USB UVC) works; the
  harder question is power/trigger design (manual button vs.
  automatic interval capture) given a battery-powered wearable rig,
  not the camera hardware itself.
- **On-device species/plant identification** — a real image-classification
  workload, meaningfully harder than this project's text tool-calling
  work so far. The AI HAT+2's Hailo-10H is a plausible fit for
  lightweight on-device classification (Hailo's own docs mention smart
  search/captioning), but running this fully offline in the field vs.
  "capture now, identify once docked to Home" is an open design
  question — see `VISION.md`'s critical-evaluation note. Don't assume
  live in-field identification is feasible until actually benchmarked
  on real HAT+2 hardware.

## GPS (priority raised 2026-07-14 — now load-bearing, not deferred)

Previously deferred as "many options, pick later." The Memories vision
(distance hiked, average pace, location-tagged logs on the maps) now
genuinely depends on continuous position data, not just the manual
waypoint-based distance calculator `core/waypoint_manager.py` already
has. Still no module chosen — evaluate once this becomes the active
milestone, but don't treat it as low-priority anymore. An IMU/accelerometer
may also be worth pairing with GPS for pace/motion data during
GPS-denied stretches (tree cover, etc.) — open question, not decided.

## Modular Backpack / physical form factor (2026-07-14 addition, not yet designed)

The end physical form, per the user's explicit vision: a wearable
backpack rig, not a device carried in a bag and pulled out. Camera,
speaker, and mic mounted to a strap; Pi5 + AI HAT+2 + battery mounted
to the pack body; plug-and-play expansion modules (the same spirit as
Field Kit's Connected Device Framework, but physical/mechanical rather
than USB/serial). This is real industrial/hardware design work — a
module connector standard, strap-mount hardware, weatherproofing,
weight distribution — tracked here as its own parallel track, the same
way Fleet/Communications hardware choices are deferred until a concrete
part gets chosen, not something resolved in software. Revisit once a
first physical prototype is underway.

## Open questions to revisit as hardware is acquired

- Exact mic/speaker hardware once voice interface is actually built
- GPS module choice for Navigation — see the GPS section above, now
  higher priority than previously noted
- Camera module choice — see the Camera section above
- LoRa/SDR/radio hardware for Communications — defer until that phase,
  since protocol choice (Meshtastic vs. custom) affects the hardware pick
- Battery/UPS HAT choice for Power section — needs to report real
  telemetry (voltage/current), not just presence, so pick one with a
  documented I2C interface — now doubly important given the same
  battery is expected to run camera/mic/speaker peripherals too
- Modular backpack connector standard / strap-mount hardware — see the
  new section above
- Project 2 (Home) — remaining parts (motherboard/RAM/storage/PSU/case/
  cooling), see the new section above; also revisit whether it should
  live on the home network only or need some form of secure remote
  reachability once the streaming access mode is actually designed
