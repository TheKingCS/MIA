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

## Not yet priced this round

Dosing pumps, PIR motion sensor, alert beacon, solar charge controller,
and battery bank still carry earlier rough estimates in the code — flag
these for a pricing pass before actually ordering them.
