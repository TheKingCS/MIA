# MIA Homestead — Pi ↔ Safety MCU Protocol

## Purpose

Defines how the Pi (brain) and Safety MCU (spinal cord) talk. The MCU is
the final authority on actuation — this protocol is designed so the MCU
can ALWAYS fall back to safe behavior even with zero valid input from
the Pi. Physical link: UART (serial) over a wired connection between Pi
and MCU — no wireless, no dependency the MCU can lose independently of
losing the Pi itself.

## Core rule

**The MCU does not trust the Pi by default — it trusts silence.**
Every safe default is what happens when the MCU hears nothing. The
protocol's job is to describe what "hearing something" looks like, not
to define safety (that's `SAFETY_SPEC.md`) — this file is the wire format.

## Message format

Newline-delimited JSON over serial, one message per line. Kept
human-readable deliberately — you should be able to `screen` into the
serial port and read what's happening without a decoder.

### Pi → MCU: Heartbeat + Command

```json
{"type":"heartbeat","seq":10432,"ts":"2026-08-26T14:03:12Z"}
```

```json
{"type":"command","seq":10433,"actuator_id":7,"action":"pulse","duration_ms":1500,"dose_type":"ph_up"}
```

- `seq` is a monotonically increasing counter. MCU rejects any command
  with `seq` <= last accepted seq (prevents replay of stale commands
  after a Pi restart sends buffered/delayed messages).
- Every `command` message MUST have a `heartbeat` within the last
  `HEARTBEAT_TIMEOUT_MS` (see below) or the MCU discards it.

### MCU → Pi: Ack + Status

```json
{"type":"ack","seq":10433,"executed":true}
```

```json
{"type":"ack","seq":10433,"executed":false,"reason":"dosing_limit_exceeded"}
```

```json
{"type":"status","battery_mv":12420,"uptime_s":884213,"fallback_active":false}
```

MCU sends `status` on a fixed interval (default 10s) regardless of
whether the Pi is sending anything — this is how the Pi detects "MCU is
alive but not hearing me" vs "MCU is dead" vs "all healthy."

## Timeout behavior (the actual safety mechanism)

```
HEARTBEAT_TIMEOUT_MS = 60000   # 60s, tune after field testing

if (now - last_heartbeat_received) > HEARTBEAT_TIMEOUT_MS:
    MCU enters FALLBACK MODE:
        - All dosing pumps -> OFF (they're pulse-only anyway, so this
          just means "stop accepting new pulse commands")
        - Aeration -> ON (hard-wired safe default, not commanded)
        - Circulation -> ON (hard-wired safe default, not commanded)
        - Non-critical actuators (lighting, etc) -> OFF
        - MCU begins broadcasting status at 2x normal frequency so the
          Pi immediately sees fallback_active:true the moment it comes
          back and can alert accordingly
```

Exiting fallback mode requires: heartbeat resumes AND the Pi sends an
explicit `{"type":"resume_control"}` message — resuming should never be
silent/automatic, because "the Pi came back but might be malfunctioning"
is exactly the scenario this protocol needs to be paranoid about.

## Hard limits enforced IN THE MCU, not just checked by the Pi

The MCU firmware itself (not just the Pi's `_validate_command`) holds a
small local copy of dosing limits — max pulse duration per dose type,
minimum interval between pulses. This is deliberate redundancy: if the
Pi's logic has a bug and sends a runaway command, the MCU firmware is
the last line of defense, independent of Pi software correctness.

```
MCU_LOCAL_LIMITS = {
    "ph_up":   {"max_pulse_ms": 2000, "min_interval_s": 300},
    "ph_down": {"max_pulse_ms": 2000, "min_interval_s": 300},
    "nutrient_concentrate": {"max_pulse_ms": 3000, "min_interval_s": 600},
}
```
These values sync from the Pi's `dosing_limits` table on connect/reload,
but the MCU keeps the LAST KNOWN values in non-volatile memory if it
loses contact with the Pi entirely — it never reverts to "unlimited."

## Physical override

A hardware switch (not a GPIO the Pi controls) wired directly into the
MCU's power/enable line for dosing pumps. When engaged: dosing pumps are
physically unpowered regardless of any software state on either the Pi
or the MCU. This is the true last line of defense, and it's the one
Zac (or anyone at the greenhouse) can hit even if both the Pi and MCU
firmware are somehow both wrong at once.

## Device announce / pairing (plug-and-play)

Before an MCU is trusted for control commands, it goes through a
one-time announce/pairing handshake — see `core/device_registry.py`
and `docs/DEVICE_SETUP_GUIDE.md` for the human-facing side of this.

### MCU → Pi: Announce (sent once on boot, before normal heartbeat starts)

```json
{"type":"announce","hardware_id":"ESP32-A1B2C3D4E5F6","requested_role":"watering_mcu"}
```

`hardware_id` should be something permanently burned into the chip
(e.g. the ESP32's factory MAC address) — never something a human
assigns, so it can't collide or be typo'd. `requested_role` is
optional — a pre-flashed MCU (e.g. firmware built specifically for the
watering role) can declare it; a generic/blank MCU can omit it and
wait for a human to assign a role via the setup CLI or the assistant.

### Pi → MCU: Pair confirmation

```json
{"type":"pair_confirm","role":"watering_mcu","cell_id":1,"controls":["irrigation_valve"]}
```

Once paired, the MCU is now a legitimate target for `command` messages
per the normal protocol above. An MCU that hasn't been paired should
refuse to execute any `command` message it receives, even if the
message format is otherwise valid — pairing is the authorization step,
not just a labeling convenience.

### If the role is ambiguous, unknown, or already claimed

The Pi does NOT auto-pair. The device sits in a `needs_attention` state
(see `device_registrations` table) until a human resolves it — via
`core/device_setup_cli.py`, or by asking the assistant. This is
deliberate: silently guessing which role an unlabeled MCU should have
is exactly the kind of thing that goes wrong once and is hard to debug
later.


- Confirm UART baud rate / physical pinout once MCU board chosen
- Decide checksum/CRC on messages (recommend yes, once real serial
  noise on the actual cable run is characterized)
- Field-tune `HEARTBEAT_TIMEOUT_MS` — 60s is a starting guess, not
  measured against real Pi boot/reboot timing yet
