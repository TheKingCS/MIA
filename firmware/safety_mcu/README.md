# MIA Homestead — Safety MCU Firmware

Implements `docs/MCU_PROTOCOL.md` on an ESP32. This is the piece that
makes the two-tier safety architecture (Pi proposes, MCU is the final
authority) real in hardware rather than just a design document.

## Honest status

**This has not been compiled or run on real hardware.** It was written
in an environment with no ESP32 toolchain and no network access to pull
the ArduinoJson library or verify a build. It's written carefully
against the standard Arduino/ESP32 core and the ArduinoJson v6 API, and
the logic has been reasoned through against every scenario in
`MCU_PROTOCOL.md` — but "compiles clean and does what the spec says"
is a claim only a real build on your desktop can confirm. Treat this as
a strong first draft, not a verified deliverable.

## Known gaps to resolve before real deployment

1. **`findActuatorSlotById()` is a placeholder.** It currently assumes
   the Pi's `actuator_id` maps directly to this firmware's array index
   (0-3), which only works if that convention is enforced on the Pi
   side too — it currently isn't. Real fix: either have the
   `pair_confirm` message include explicit `actuator_id: pin_slot`
   pairs, or establish and document a fixed convention both sides agree
   on. This is the single most important thing to fix before trusting
   this firmware with real dosing commands.
2. **`executePulse()` uses `delay()`,** which blocks the whole loop for
   the pulse duration (up to 3 seconds per the current dosing limits).
   That's a real problem if this MCU is also supposed to be responsive
   to a physical emergency-stop input during that window — worth
   moving to non-blocking timing (`millis()`-based state machine)
   before deployment, especially once more actuator types get added.
3. **`readBatteryMillivolts()` is a stub** returning -1. Wire to a real
   ADC pin if this specific board runs on battery power; if it's
   Pi-powered via the same rail, this can likely be removed entirely.
4. **No checksum/CRC on messages** — flagged as an open item in
   `MCU_PROTOCOL.md` itself; add once you've characterized real serial
   noise on your actual cable run.
5. **No physical override switch wired in.** `MCU_PROTOCOL.md`
   specifies a hardware kill switch on the dosing pump power line,
   independent of any code on either the Pi or this MCU — that's a
   wiring decision, not something firmware can provide on its own.
6. **Dosing limits are hard-coded, not synced from the Pi at pairing.**
   `MCU_PROTOCOL.md`'s `pair_confirm` message doesn't currently carry
   limit values. Keep the `dosingLimits[]` array manually in sync with
   the Pi's `dosing_limits` table for now, or extend the protocol if
   you want live sync — don't assume this happens automatically.

## Building and flashing

1. Install [Arduino IDE](https://www.arduino.cc/en/software) or
   [PlatformIO](https://platformio.org/).
2. Install the ESP32 board package (Arduino IDE: Boards Manager →
   search "esp32" → install the Espressif package).
3. Install the **ArduinoJson** library (v6.x — Library Manager → search
   "ArduinoJson" by Benoit Blanchon).
4. Edit the configuration block at the top of `safety_mcu.ino`:
   - `REQUESTED_ROLE` — set to match a role id from
     `config/devices/roles/*.yaml` if this board is being pre-flashed
     for a specific job, or leave blank for a generic board a human
     assigns later.
   - `actuators[]` pin assignments — match your actual wiring.
   - `dosingLimits[]` — these should match (or be more conservative
     than) the `dosing_limits` table on the Pi side.
5. Select your board (Tools → Board → your ESP32 variant) and port,
   then Upload.
6. Open the Serial Monitor at 115200 baud — you should see `announce`
   messages every 3 seconds until it's paired from the Pi side.

## Testing without real sensors/pumps attached

Wire an LED + resistor to each actuator pin instead of a real relay —
you can verify the full announce → pair → command → pulse → fallback
cycle visually before anything is connected to real dosing hardware.
This is the hardware equivalent of the software simulation-first
approach in `docs/SIMULATION_STRATEGY.md` — prove the logic cheaply
before it's anywhere near a real chemical.
