# MIA Hardware Guide

This document tracks concrete hardware recommendations and known
constraints for building MIA Core on a Raspberry Pi 5. Update it as
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
  WebUI is the reference example in Hailo's own docs; MIA's
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
which is reinstallable from the MIA repo.

## Voice interface

**Recommended: physical push-to-talk button, not always-listening.**

- A single momentary button, wired as a hardware interrupt (not
  polled), for near-zero idle power draw and instant response —
  **placement decided 2026-07-15: on the Receiver** (see "Modular
  Backpack" below), the reachable spot given where it's actually worn.
  Wired through the Receiver's own Pico/RP2040 (see "Modular Backpack"
  below, decided 2026-07-19) rather than a raw GPIO run all the way
  back to the Pi's own header, alongside the display/LED/vibration
  motor also landing on that same MCU
- Avoids wake-word false triggers and the extra always-on compute/power
  budget of continuous audio processing — both matter for a
  battery-powered field device
- **2026-07-15 update**: the mic/audio-output pairing recommendation
  above (I2S DAC/amp) assumed they'd sit right next to the Pi's own
  GPIO header — no longer true now that the mic and audio output (a
  headphone jack as of 2026-07-19, see "Modular Backpack" below) live
  in the physically remote Receiver module. USB is the better fit for
  this actual arrangement, same reasoning as the Receiver's camera
  connection: I2S needs a short direct wiring run, USB tolerates the
  longer cable a chest/strap-to-side-of-pack connection actually
  requires.

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

- Autologin + a systemd service launching MIA directly in a minimal
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

Added by the wearable-companion vision update (`docs/VISION.md`) — now
part of the Receiver module, see "Modular Backpack / physical form
factor" below for the concrete two-part physical architecture this
lives in. Two real jobs for the camera specifically, likely different
priorities:

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
has. An IMU/accelerometer may also be worth pairing with GPS for pace/
motion data during GPS-denied stretches (tree cover, etc.) — open
question, not decided.

**2026-07-19: module family decided — u-blox M9N or M10, exact
breakout board still open.** Real motivation surfaced while testing
voice-command robustness for the wearable: `add_waypoint`'s only way
to place a waypoint today is the user speaking exact latitude/longitude,
which isn't practical in the field — a real GPS fix is what makes a
future "save a waypoint here" voice command actually work. Chose
multi-constellation M9N/M10 over the cheaper, GPS-only NEO-6M
specifically because of this rig's own tree-cover concern (a hiking/
field device under canopy needs GLONASS/Galileo/BeiDou reception, not
just GPS, to get a reliable fix) — worth the extra cost/power draw over
NEO-6M for that reason. **Power draw explicitly accepted, with a
concrete fallback already decided**: if the M9N/M10's draw turns out to
strain the Compute Block's power budget once the Battery/UPS HAT is
chosen (still an open question below), the plan is to double the
battery capacity rather than downgrade the GPS module — noted here so
that trade-off isn't relitigated once real power numbers come in.
**2026-07-19: IMU pairing decided — a separate IMU chip alongside the
M9N/M10, not an integrated GPS+IMU module.** u-blox does make combined
dead-reckoning parts (NEO-M8U, ZED-F9R), evaluated and deliberately
passed over:
- **NEO-M8U** is built on the older M8 GNSS core, a real step back from
  M9N/M10's concurrent multi-constellation/jamming-resistance
  improvements — the exact properties M9N/M10 was chosen for. An
  integrated IMU isn't worth quietly giving back the canopy performance
  this rig specifically needs.
- **ZED-F9R** (dual-frequency, automotive/robotics-grade) would likely
  match or beat M9N/M10 under canopy, but at several times the cost and
  integration complexity aimed at self-driving-car-class use cases —
  real overkill for a hiking wearable.

Keeping M9N/M10 and adding a separate, inexpensive IMU breakout (e.g.
an MPU-6050 or BNO055/BNO085-class part — exact one still open) keeps
the already-decided canopy performance intact and stays far cheaper
than F9R, at the cost of one extra I2C part and doing sensor fusion in
software (on the Pi) rather than in the GPS module's own firmware.
Still open: the exact GPS breakout board (SparkFun vs. Adafruit vs.
other) and the exact IMU part.

**2026-07-15: physical placement decided — the Compute Block, not the
Receiver.** The user's own call. Practically this also means the GPS
antenna sits at pack-side height, not up at chest/shoulder height —
worth keeping in mind once a specific module is chosen, since GPS
antenna placement/orientation and sky visibility affect fix quality;
revisit if pack-side placement turns out to give meaningfully worse
signal than chest-height would have.

## Modular Backpack / physical form factor

**2026-07-15: the physical architecture is now concretely defined as
two separate wearable units, not one block with strap-mounted
peripherals** (an evolution of the 2026-07-14 wearable-companion
vision, per the user's own explicit description):

1. **Compute Block ("Core")** — one physical enclosure holding
   everything from "Core platform"/"AI acceleration"/"Storage" above in
   a single unit: the Pi 5, the AI HAT+ 2, the battery/UPS HAT (power
   source), and the storage devices. **Mounted to the side of the
   backpack**, not the strap — this is the heaviest, bulkiest part of
   the rig, and side-of-pack placement (like a hiking pack's accessory
   pocket) is both a better weight-distribution point and physically
   protects the most expensive/critical hardware, versus putting it
   somewhere it'd take a direct hit or snag.
2. **Receiver** — a separate, remote module bundling the camera, mic,
   and (2026-07-19: revised, see below) a headphone jack together as
   *one* physical unit. **Worn on the backpack strap or chest-mounted**
   (like an action-camera chest harness) — deliberately close to the
   user's own eyes/ears/mouth, not down at pack-body height, since its
   whole job is sensing the user's environment and voice, not just
   being near the compute.

**2026-07-19: audio output changed from an open speaker to a headphone
jack, staying on the Receiver (not moved to the Compute Block).** Two
real reasons: privacy/reliability (an open speaker broadcasts MIA's
replies to everyone nearby and has to compete with wind/ambient noise
outdoors; earbuds are private and heard reliably), and it actually
solves the "no wearable 3-in-1 device" problem found while researching
the camera+mic+speaker combo — a speaker needs its own driver/cone
(what pushed every speaker-inclusive product to desk-puck scale, 3.5"+
and 100g+), while a headphone jack just needs a jack + a small
headphone-amp chip, a completely different size class that a real
camera+mic+headphone-jack wearable combo can plausibly fit. Staying on
the Receiver rather than the Compute Block specifically because the
Receiver already needs a cable run back to the Compute Block (camera/
mic/button/LED/vibration/display) and already sits close to the ears —
putting the jack there means a few-inch cable to the ear and the long
pack-to-chest run stays a single cable carrying everything digitally.
Moving it to the Compute Block would have meant an entire second cable
run the full pack-to-head distance, working against the whole reason
the Receiver is chest-mounted in the first place.

**2026-07-15: the Receiver's component list grew, and two previously-open
placement questions are now decided** (both the user's own explicit
call):
- **Push-to-talk button → on the Receiver**, not the Compute Block —
  makes sense given it's worn at chest/strap height, the actually
  reachable spot.
- **A small, energy-efficient status display** on the Receiver, showing
  battery level and GPS status. "Energy-efficient" here points pretty
  clearly at **e-paper/e-ink** over OLED/LCD — it draws power only when
  the image changes and holds it at zero power in between, which fits a
  status readout that only needs to update every so often far better
  than a display that's continuously powered to stay lit. The trade-off
  is refresh speed (not a concern here) and no continuous video, which
  this use case doesn't need anyway. **2026-07-19: specific part
  chosen — a 2.13" monochrome Waveshare e-Paper module** (250×122,
  SPI, well-supported CircuitPython/MicroPython drivers for the
  Pico/RP2040). Monochrome over color: this only ever shows battery %/
  GPS status text/icons, and color e-paper adds slower refresh and more
  complex driving for no real benefit here. 2.13" over the smaller
  1.54" class: meaningfully better at-a-glance readability worn at
  chest height, worth the small size/weight increase.
- **A recording-indicator LED** — lights while the camera/mic are
  actively capturing. Worth noting this isn't just a nice-to-have: a
  camera+mic worn on someone's body is exactly the kind of device where
  a visible "this is recording" signal matters for the people around
  the user too, not only the user themselves — keep it genuinely
  reliable (tied to actual capture state, not just "powered on") rather
  than cosmetic. Any basic 3mm/5mm LED driven off the Pico/RP2040 works
  — no real part decision here, just wiring discipline.
- **A vibration motor** on the Receiver for notifications.
  **2026-07-19: decided — a simple ERM motor**, not LRA. LRA (phone-
  quality, crisp/distinct pulses via a TI DRV2605L driver) was the
  fancier option on the table, but ERM keeps this to one fewer part (no
  separate haptic driver chip needed, just PWM or basic on/off through
  a transistor) for a notification buzzer that doesn't need nuanced
  distinct-feel patterns.

**2026-07-19: decided — the Receiver gets its own small microcontroller,
a Pi Pico/RP2040.** This component list had grown big enough to raise a
real design question the original two-item Receiver didn't have:
whether every button/LED/vibration-motor/display should run raw GPIO
wires down the connector cable to the Pi, or consolidate locally
first. Going with the local-MCU route: the Pico handles the button,
LED, vibration motor, and e-paper display locally, then talks to the
Compute Block over one clean USB/serial link. Real advantages over raw
GPIO at a distance: fewer, more robust wires in the connector cable
instead of one pair per component (voltage drop and noise pickup get
worse the longer a raw GPIO run is), instant local response (the
recording LED doesn't wait on a round trip to the Pi to light up), and
the e-paper display's own refresh logic lives on the MCU instead of
the Pi. Accepted cost: real firmware work (MicroPython/CircuitPython
on the Pico is the natural choice given this project's own
Python-first bias) and one more component that can fail.

**2026-07-19: decided — USB is how the Receiver talks back to the
Compute Block.** They're physically separated by a real distance
(side-of-pack to chest/strap), so this needs an actual cable run, not
a short ribbon connector. A Pi-native CSI camera would normally be the
first choice for image quality/latency, but CSI ribbon cables are short
and fragile, a poor fit for a run of this length across a person's
body. USB is more robust over distance and lets camera+mic+headphone-jack
*and* the Pico's own USB/serial link (button/LED/vibration/display)
share a single cable/connector rather than a bundle of separate ones.
Still open: the actual connector/cable itself (type, strain relief,
routing along the pack and up to the chest/strap, weatherproofing) —
real industrial design not resolved here, same "tracked as its own
parallel track, revisit once a first physical prototype is underway"
status as before, just with the architecture now concrete enough to
prototype against instead of an open sketch.

**Solar charging (2026-07-15 addition)**: the Compute Block's power
source should be rechargeable from a solar panel charger, per the
user's explicit ask. This doesn't need special solar-specific circuitry
if the chosen battery/UPS HAT has a **standard USB-C PD charging
input** — most portable/camping solar panels (commonly 20–30W foldable
panels) output USB-C PD directly, so they can charge the same battery
pack a wall charger would, no separate solar charge controller needed.
This *added* a second real requirement to the Battery/UPS HAT choice
(documented I2C telemetry interface was the first) — both needed to
matter: I2C for `core/power_manager.py` to report real voltage/current,
and standard USB-C PD input so any common solar panel can charge it
directly.

**2026-07-19: Battery/UPS HAT decided — Waveshare UPS HAT (E).**
Verified via real current listings (including CNX Software's
independent coverage, not just the vendor page) rather than assumed
from memory, since Pi5-compatible UPS HATs are a newer, faster-moving
category than this document's other hardware picks: real I2C fuel
gauge (voltage/current/power/remaining capacity — exactly what
`core/power_manager.py` needs), USB-C **PD3.0** input up to 40W (a
genuine PD negotiation, not just a 5V-only USB-C port — satisfies the
solar-charging requirement directly), and 4×21700 Li cells for 5V/6A
output. The 4-cell 21700 format gives real headroom to grow capacity
if the M9N/M10 GPS module's power draw strains the budget, matching
the "double the battery" fallback already agreed to in the GPS section
above — swapping in higher-capacity 21700 cells or simply keeping all
4 populated is a direct, already-supported path to that, not a HAT
swap. SunFounder's PiPower 5 (5V/5A, USB-C PD 45W, I2C via an onboard
Cortex-M23 MCU) was a real close alternative, passed over only because
its battery format/capacity wasn't as clearly documented in what was
verified.

## Open questions to revisit as hardware is acquired

- Exact camera+mic module and headphone-jack breakout for the Receiver
  — architecture decided (camera+mic module, no speaker, a headphone
  jack instead — see "Modular Backpack" above), exact parts still open.
  A genuine combined camera+mic+headphone-jack device may now be
  plausible at wearable scale (unlike the camera+mic+speaker combo
  researched and rejected), worth a real search before falling back to
  a small camera+mic module (e.g. Arducam's mini UVC line) plus a
  separate small headphone-jack breakout.
- The Compute Block ↔ Receiver cable/connector itself (type, strain
  relief, routing, weatherproofing) — real industrial design, not
  software-resolvable. The link itself is decided (USB, carrying the
  Pico's button/LED/vibration/display/headphone-audio traffic and
  camera/mic), just not the physical connector/cable part.
- GPS module choice for Navigation — see the GPS section above.
  Placement (Compute Block), chipset family (u-blox M9N/M10), and IMU
  pairing (yes, a separate chip, not an integrated M8U/F9R) are all
  decided; the exact GPS breakout board and exact IMU part are still open.
- LoRa/SDR/radio hardware for Communications — defer until that phase,
  since protocol choice (Meshtastic vs. custom) affects the hardware pick
- Compute Block enclosure — side-of-backpack mounting hardware, and
  whether it needs a dedicated weatherproof case given AI HAT+2 needs
  its own Active Cooler airflow (see "Core platform" above)
- Project 2 (Home) — remaining parts (motherboard/RAM/storage/PSU/case/
  cooling), see the new section above; also revisit whether it should
  live on the home network only or need some form of secure remote
  reachability once the streaming access mode is actually designed
