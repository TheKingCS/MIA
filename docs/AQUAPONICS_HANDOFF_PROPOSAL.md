# The aquaponics greenhouse: build it with MIA, then hand it to her (DEC-0150, proposed)

Zac, 2026-11-08: "I need MIA just as deeply knowledgeable [as Trade Master] to walk through and execute the steps
for building out the aquaponics greenhouse. She will need to understand what technologies go into it, what she is
able to connect to and configure, and more. When it comes time to build this project out, I want to be able to
build it and essentially pass her to it, so that she can integrate and monitor everything she has set up for
monitoring."

Nothing is built yet. This is what exists, what's missing, and a first version to approve.

## 1. What exists: most of it is MIA Homestead

**MIA Homestead** (`homestead/`, merged on the `homestead-merge` branch and waiting on Zac's push OK, DEC-0145) is
the greenhouse node itself:

- **Two-tier safety:** a Pi is the brain and proposes; a separate ESP32 safety microcontroller (`firmware/safety_mcu`)
  is the final authority, and falls back to hard-coded safe states if it stops hearing from the Pi
  (`docs/SAFETY_SPEC.md`).
- **Modules:** an aquaponics cell, climate control, power monitoring, self-preservation (`modules/`), each declaring
  its capabilities and hardware needs. The live parts list (`docs/HARDWARE_BOM_LIVE.md`) and the features list
  (`docs/FEATURES_AND_CAPABILITIES.md`) regenerate from those declarations.
- **Drivers and simulation:** Atlas Scientific probe drivers, MCU serial, and a physics simulator to run without
  hardware. Its scenarios pass 242 of 245 on Windows (the 3 failures are rsync).
- **Device setup:** a labeled, color-coded, one-port-per-device convention and a setup helper that says what to plug
  in where (`docs/DEVICE_SETUP_GUIDE.md`).
- **Readiness:** what's ready for day one, and what still needs real hardware or a decision
  (`docs/DAY_ONE_READINESS.md`).
- **Experiments:** dosing-target experiments behind an approval queue.
- **Backup and auto-revert:** config backups that revert a change by themselves when critical alerts spike after it.
- **Its own assistant:** an aquaponics scientist answering from the live database.

**MIA's side already has:**

- **Snapshot ingestion** (`core/homestead_manager.py`): reads the node's summarized-state snapshots from a watched
  folder. Today a person drops the file in by hand.
- **The grow lab** (`core/grow_lab.py`): batches, water readings and experiments.
- **What's Next for the homestead** (`core/development_engine.py`): the greenhouse chain.
- **Trade Master** (DEC-0149): the hoop-house greenhouse job and the session that walks it.
- **The Homesteading specialist.**
- **Device detection** (`core/device_framework.py`): USB and serial.
- **The device fabric proposal** (DEC-0128): recognizing, talking to and securing your devices.

## 2. What's missing

1. **The build, step by step.** The plumbing and system build, the controller and sensor install, and
   commissioning (calibrating probes, cycling the biofilter, stocking fish) aren't Trade Master jobs yet.
2. **Her knowing the technology.** MIA, the main assistant, doesn't read the node's own registry yet. That
   registry holds what each module does, what hardware it needs, how it's wired, and what's proven versus not.
   Read as her knowledge, it would mean she never guesses which sensor or relay exists.
3. **The hand-over link.** The node runs no server, and its snapshots only reach MIA by hand. Nothing yet moves
   the node's state to MIA on its own.
4. **Monitoring in MIA.** Once the link exists, every sensor the node registers should become something MIA
   watches: readings into the grow lab, critical alerts through the gate as urgent, a daily line on how the system
   is doing.

## 3. Proposed first version

- **Three Trade Master jobs**, written to DEC-0149's standard from the node's own documents and published aquaponics
  sources. Each walks you through and asks for "checked" at the hold points (a leak test held, a probe calibrated,
  ammonia and nitrite at zero before fish):
  1. *Build the aquaponics system:* the fish tank, grow beds and sump; the plumbing (flow, siphons or a timed flood
     and drain, overflow protection); pump and aeration; a leak test before anything electrical goes near water.
  2. *Install the controller and sensors:* the Pi and the safety MCU on the node's labeled-port convention, probes
     and dosing pumps from the parts list, low-voltage wiring, and pumps and heaters on GFCI-protected circuits. Any
     new mains circuit follows the electrical stop rule and the permit.
  3. *Commission and cycle it:* calibrate each probe, run the node in simulation and then live, cycle the biofilter
     before fish (several weeks: ammonia and nitrite at zero, nitrate rising), then stock gradually.
- **The node's registry as MIA's knowledge.** After the merge, MIA reads the registry from the same repository:
  its capabilities, hardware, wiring and evidence, plus the generated features and parts list. "What can you
  connect to in the greenhouse?" or "which pump is the pH dosing?" is answered from it, with what's proven and
  what's unverified.
- **The hand-over:** "MIA, take over the greenhouse." The node exports its snapshot on a timer. MIA's PC fetches
  it over your home network or Tailscale and ingests it. MIA then:
  - adds every registered sensor and module as a monitor;
  - sends the node's critical alerts through the gate as urgent, and its warnings as timely;
  - puts the readings into the grow lab;
  - gives a daily line on the system ("pH 6.9, nitrate rising, all probes reporting").

  She says what she now watches, and what she can't yet (no data, unverified hardware).
- **Control stays with the node.** MIA monitors and proposes. The node's local loop and the safety MCU act. A
  change to dosing or targets goes through the node's own approval queue with your OK. MIA never drives a relay or
  a pump directly.

## 4. Questions for Zac

1. **The homestead push** (DEC-0145): yes, so the node's code lives in MIA's repository and she can read it?
   This first version needs it.
2. **Approve this first version** (section 3)? Recommended: yes.
3. **How MIA reaches the node:** (a) the snapshot dropped in by hand, as now; (b) MIA's PC fetches the node's
   snapshot every few minutes over your home network or Tailscale; (c) a live link to the node's dashboard.
   Recommended: (b) now, (c) later.
4. **Who acts:** MIA monitors and proposes, and the node with its safety MCU acts, as above? Recommended: yes.
5. **Pilot first:** build the pilot cell first, as the node's own `docs/PILOT_VS_SCALE.md` advises, then full
   scale? Recommended: yes.

## 5. Risks

- **Water and electricity together.** GFCI protection, a drip loop on every cord, and a leak test before power,
  all as hold points. Any new mains circuit follows the electrical stop rule and the permit.
- **Live animals.** A failed pump or aerator can kill fish within hours. That's why the safety MCU and its safe
  defaults are the final authority, and why the node's critical alerts reach you as urgent.
- **Two systems drifting apart.** MIA reads the node's own registry rather than keeping a copy, so what she knows
  is what the node declares.
- **Unproven hardware.** The node marks every capability proven or unverified, and MIA says which.
