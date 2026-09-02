# MIA Homestead — Day-One Hardware Readiness

User request (2026-09-02): "brainstorm what else this needs to be the
best version of itself on day 1 of putting it to hardware." Grounded in
actually re-reading `docs/PILOT_VS_SCALE.md`, `docs/SAFETY_SPEC.md`,
`docs/DEVICE_SETUP_GUIDE.md`, and `firmware/safety_mcu/README.md`
first, not brainstormed blind — those docs already have a real,
well-reasoned "what the pilot is for" priority list (`PILOT_VS_SCALE.md`
§"What the pilot is FOR"). This doc doesn't repeat that list; it names
what's missing *from* it, split by whether it's a real software gap
closeable now vs. something that genuinely needs hardware/a human
decision first.

## Real software gaps — closeable now, no hardware needed

### 1. Critical alerts are silently inert — no config file exists for them

`SAFETY_SPEC.md`'s alerting escalation requires "immediate push
notification/SMS to primary + secondary contact" for anything
critical. `core/notifications.py`'s `NotificationConfig` dataclass
already implements this correctly (SMTP email + carrier-gateway SMS,
no vendor lock-in) — but `main.py` constructs it as
`NotificationConfig()` with **zero arguments**, so every field
defaults to an empty string, every single run, with no way to set real
values short of hand-editing `main.py`'s source. Every other
configurable subsystem in this project (`config/location.yaml`,
`config/irrigation_schedules.yaml`, `config/mia_home_sync.yaml`, the
device role configs) follows the same "config IS the source of truth"
convention; notifications is the one exception, and it's the one that
matters most on day 1 — a critical alert with nowhere real to go is
functionally the same as no alert at all.

**Fix**: `config/notifications.yaml` (same null-safe pattern as
`location.yaml` — empty/missing = notifications stay inert, exactly
today's behavior, never guessed at), loaded into `NotificationConfig`
the same way `IrrigationScheduler.from_config()` already loads its
own. Testable now without a real SMTP account: config loading, the
dataclass construction, and the "no host configured = no-op, logged"
path are all real, verifiable code paths — only actual delivery needs
a real account, which is a day-1 human action either way.

### 2. No Pi-side serial transport to the MCU exists in code at all

`firmware/safety_mcu/README.md`'s own honest status: "no serial
transport exists yet to actually send this payload (no MCU hardware to
send it to)." Confirmed by reading `core/device_registry.py` — it
builds the real `pair_confirm` JSON payload
(`build_pair_confirm_payload()`, already scenario-proven with real DB
ids) but there's no `pyserial` import anywhere, no open-port/read/write
loop, nothing that would actually get that payload onto a wire. This
is exactly `PILOT_VS_SCALE.md`'s own Priority #3 ("run a real device
pairing") and Priority #1 (flashing/proving the firmware) — without
this, day 1 means improvising serial I/O under time pressure with a
real board already on the bench, instead of having it ready and
tested against a mock.

**Fix**: a small `drivers/mcu_serial.py` — open the port, send
`announce`/`pair_confirm`/actuator commands as line-delimited JSON per
`docs/MCU_PROTOCOL.md`, read responses, surface failures the same
honest way `drivers/atlas_scientific_driver.py` does for I2C. Testable
now against a mock serial port (`pyserial`'s own loopback/`socat`
virtual pty, or a fake object matching `pyserial`'s read/write
interface) — real hardware only needs to prove the physical link
works, not validate the protocol logic for the first time.

### 3. Firmware's `executePulse()` blocks the whole loop during a dose

Firmware README's own gap #2, restated because it's the one gap in
that list that's a pure code fix, not something gated on a real board:
`delay()` blocks for up to 3 seconds (current dosing limits) with
nothing else running — including, per that same README, responsiveness
to a physical emergency-stop input during that exact window. This is
directly in tension with `SAFETY_SPEC.md`'s manual-override
requirement ("independent of the Pi and any software state" — but not
independent of the firmware's own blocked main loop). Moving to a
`millis()`-based non-blocking state machine is verifiable via `pio
run` compiling clean and reasoning through the state transitions, same
"proves the code is valid, not that it's been run" standard the
firmware's own honest-status section already holds itself to.

### 4. The pilot's own BOM doesn't include the safety-spec-required override switch

`SAFETY_SPEC.md`: "Physical local override switch at the greenhouse
(kill dosing, force aeration on) independent of the Pi and any
software state." `docs/HARDWARE_BOM_FULL_TIERS.md` already prices this
for full scale (~$8–15, DPST toggle switch) under its own "Physical
safety kill switch" section, citing the same spec requirement — but
`PILOT_VS_SCALE.md`'s trimmed pilot shopping list never picked it up.
Since the pilot's explicitly stated purpose is proving "the whole
control/safety chain end to end," and this is a named part of that
chain in the spec the pilot is supposed to validate, its absence from
the actual pilot BOM is a real gap between the spec and the shopping
list, not a considered trim — unlike EC dosing or the watering MCU,
which `PILOT_VS_SCALE.md` explicitly and reasonably defers to phase 2.

**Fix**: add it to the pilot's real order-queue rows
(`seed_pilot_shopping_list()` in `drivers/simulator.py`) — cheap
($8–15), already sourced, just missing from the list that's supposed
to be complete.

## Real gaps — genuinely need hardware or a human decision, not more code

Naming these so nothing gets forgotten, not proposing to build around
them — `PILOT_VS_SCALE.md` and `SAFETY_SPEC.md` already correctly flag
most of this as gated:

- **Real dosing pulse magnitudes** (`physics_sim.py`'s
  `DOSE_EFFECT_PER_SECOND` placeholder) — `PILOT_VS_SCALE.md` Priority
  #2, needs the real pump running against real water.
- **Battery SOC thresholds** calibrated to actual battery capacity —
  `SAFETY_SPEC.md`'s own "Open items," needs a sized battery.
- **MCU-to-Pi heartbeat timeout** — `SAFETY_SPEC.md`'s own "Open
  items," 60s is a starting proposal, needs real serial latency to
  tune against.
- **Message checksum/CRC** — firmware README's gap #4, explicitly
  deferred until real serial noise on the actual cable run can be
  characterized; building this now would mean guessing at a number
  with nothing real to guess from.
- **`config/location.yaml`'s real coordinates** — currently null,
  needed for `core/weather_awareness.py` to activate at all; a
  five-minute human action once there's a real address, not a coding
  task.
- **A real SMTP account** — gap #1 above builds the wiring; an actual
  account (a free Gmail app password works, per
  `core/notifications.py`'s own docstring) is a day-1 human action
  either way.
- **Dosing limits synced to firmware, not hand-copied** — firmware
  README's gap #6, explicitly flagged as "extend the protocol if you
  want live sync, don't assume this happens automatically." A real
  future enhancement, not a day-1 blocker — hand-keeping them in sync
  for a single pilot MCU is a small, known, tolerable manual step;
  worth automating once there's more than one MCU to keep in sync by
  hand.

## Recommendation

Of the four closeable-now items, **#1 (notification config) and #4
(the override switch line item) are both small and directly
safety/operationally relevant** — worth doing regardless of what else
gets prioritized. **#2 (serial transport) is the biggest of the four**
and the one most worth front-loading, since it's squarely on the
critical path for `PILOT_VS_SCALE.md`'s own Priority #1 and #3 — better
to have it built and tested against a mock before a real board is on
the bench than to build it under time pressure once one is. **#3
(non-blocking pulse)** is real but lower urgency than it sounds: it
only matters once a physical override switch exists to actually be
blocked (see #4) — sequencing #4 before #3 makes #3's fix immediately
demonstrable end-to-end instead of provably-correct-in-isolation.
