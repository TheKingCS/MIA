# MIA Homestead — Current Hardware Pricing (checked Aug 26, 2026)

These are the two components that gate almost everything else — the
pH and EC probes are what the aquaponics control loop actually needs
to run against real data, and the Safety MCU is what the whole safety
architecture in `docs/MCU_PROTOCOL.md` depends on. Pricing below is
from a live search; verify at checkout since these move.

## pH sensing

| Option | Price | What you get |
|---|---|---|
| EZO-pH circuit alone | ~$46–51 | Just the circuit — only makes sense if you already own a compatible pH probe |
| KIT-101P (full starter kit) | ~$175 | Circuit + probe + everything to get a first reading |
| Lab-grade probe alone (ENV-40-PH) | ~$85 | Better accuracy/longevity than the economy probe, if buying separately |

**Recommendation for a first purchase:** the full kit (~$175) — buying
circuit and probe separately only saves money if you're confident in
probe compatibility, and getting a mismatched probe is a real failure
mode for a first build.

Source: atlas-scientific.com, digikey.com (both live-checked)

## EC sensing

| Option | Price | What you get |
|---|---|---|
| EZO-EC circuit alone | ~$68–86 | Circuit only |
| EC-KIT-1.0 (full starter kit) | ~$230 | Circuit + K1.0 probe + everything needed |

Same recommendation — the kit, for the same reason.

Source: atlas-scientific.com, digikey.com

## Safety MCU (ESP32)

Adafruit's ESP32 development boards (HUZZAH32 or the plain ESP32
Development Board) run **approximately $20**, though I wasn't able to
pull an exact current listed price in this pass — confirm at
adafruit.com before ordering. Any ESP32-family board with I2C/UART and
enough GPIO for the relay outputs works; Adafruit's isn't the cheapest
option (AliExpress generic boards run $2–5) but has better documentation
and support, which matters more for the safety-critical firmware this
board runs than saving $15.

## Updated running estimate

Real pH+EC kit pricing (~$405 combined) is meaningfully higher than the
earlier rough estimate (~$180) — the code's hardware requirement
declarations have been updated to reflect kit pricing rather than
circuit-only pricing, since that's what you'd actually buy first. Run
`python3 core/hardware_bom.py --db mia_homestead.db` after re-registering
to see the corrected running total.

## Dosing pumps

Basic 12V DC DIY peristaltic pumps (INTLLAB, Kamoer NKP, and similar —
the same class of pump hobbyist aquarium/hydroponics builders use) run
**~$10–15 each**. This is meaningfully cheaper than the earlier $25
placeholder — updated in code below.

Source: Amazon, INTLLAB store (live-checked)

## PIR motion sensor

HC-SR501 modules — the standard hobbyist PIR sensor — run **~$4–5
each**, confirming the earlier estimate was already accurate. No
update needed.

Source: multiple hobbyist electronics retailers (live-checked)

## Solar charge controller (Modbus/RS485)

A 10A MPPT controller with RS485/Modbus support runs **~$100–130**; a
40A version (more realistic for a greenhouse-scale array) runs
**~$149**. The RS485/Modbus requirement — needed so `power_monitor.py`
can actually poll telemetry — rules out the cheapest PWM controllers,
which typically don't expose any digital interface at all.

Source: Linovision, Amazon (live-checked)

## Battery bank

Left unpriced this round — capacity needs to be sized against actual
greenhouse load first (aeration, circulation, dosing pumps, the Pi
itself), which isn't finalized yet. Pricing a battery before sizing it
would just produce a number that has to be redone anyway.

## Not yet priced this round

Alert beacon (light/speaker) and the battery bank still carry earlier
rough estimates or are unpriced — flag before actually ordering.
