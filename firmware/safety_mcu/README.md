# MIA Homestead — Safety MCU Firmware

Implements `docs/MCU_PROTOCOL.md` on an ESP32. This is the piece that
makes the two-tier safety architecture (Pi proposes, MCU is the final
authority) real in hardware rather than just a design document.

## Honest status

**Compiles clean; still not run on real hardware.** Re-verified
2026-08-31 with `pio run` after the actuator-ID mapping fix below (gap
#1) — RAM 6.7% (21940/327680 bytes), Flash 21.5% (281401/1310720
bytes), `firmware.bin` produced, near-identical footprint to the
2026-08-30 baseline (21924/281265 bytes) as expected for one added
`int` field. That proves the code is syntactically and API-correct
against the real Arduino/ESP32 core, not just reasoned-through by eye —
but "compiles" and "does what the spec says on a real board" are still
different claims. Flashing + the LED smoke-test in "Testing without
real sensors/pumps attached" below is still the next real milestone,
not this.

## Known gaps to resolve before real deployment

1. ~~`findActuatorSlotById()` is a placeholder~~ — **fixed 2026-08-31.**
   It used to assume the Pi's `actuator_id` mapped directly to this
   firmware's array index (0-3), which only worked if that convention
   was enforced on the Pi side too — it wasn't. Real fix landed: the
   `pair_confirm` message's `controls` field now carries explicit
   `{"actuator_id": <real DB id>, "name": ...}` pairs (see
   `docs/MCU_PROTOCOL.md`), `handlePairConfirm()` stores the real id per
   slot, and `findActuatorSlotById()` does a genuine linear-search
   lookup instead of an index assumption. `core/device_registry.py`'s
   new `build_pair_confirm_payload()` constructs this payload from real
   DB rows — verified via `scenarios.py::scenario_pair_confirm_payload_real_ids`,
   which deliberately inserts actuators out of order to prove the ids
   returned are real DB ids, not a coincidental match. **What's still
   genuinely open**: no serial transport exists yet to actually send
   this payload (no MCU hardware to send it to), and real-hardware
   pairing is unverified — both correctly gated on a real board
   existing, not something to fake here.
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

This directory is now a working PlatformIO project (`platformio.ini`,
targeting `esp32dev` + ArduinoJson ^6 — `src_dir = .` so
`safety_mcu.ino` stays in place rather than moving into a `src/`
folder). With PlatformIO installed (`pip install platformio`, or the
VS Code extension):

1. Edit the configuration block at the top of `safety_mcu.ino`:
   - `REQUESTED_ROLE` — set to match a role id from
     `config/devices/roles/*.yaml` if this board is being pre-flashed
     for a specific job, or leave blank for a generic board a human
     assigns later.
   - `actuators[]` pin assignments — match your actual wiring.
   - `dosingLimits[]` — these should match (or be more conservative
     than) the `dosing_limits` table on the Pi side.
   - If your board isn't a generic `esp32dev` (e.g. an ESP32-S3 or
     -C3 variant), change `board = esp32dev` in `platformio.ini` to
     match — see [the PlatformIO ESP32 boards list](https://docs.platformio.org/en/latest/platforms/espressif32.html#boards).
2. `pio run` — compiles only, no board needed; confirms the build is
   still clean before you touch hardware.
3. Connect the board over USB, then `pio run --target upload` (add
   `--upload-port /dev/ttyUSB0` or similar if autodetection picks the
   wrong port).
4. `pio device monitor -b 115200` — you should see `announce` messages
   every 3 seconds until it's paired from the Pi side.

The Arduino IDE path (Boards Manager → esp32, Library Manager →
ArduinoJson, then Upload from the IDE) still works identically if you
prefer it — the `.ino` itself is untouched either way.

## Testing without real sensors/pumps attached

Wire an LED + resistor to each actuator pin instead of a real relay —
you can verify the full announce → pair → command → pulse → fallback
cycle visually before anything is connected to real dosing hardware.
This is the hardware equivalent of the software simulation-first
approach in `docs/SIMULATION_STRATEGY.md` — prove the logic cheaply
before it's anywhere near a real chemical.
