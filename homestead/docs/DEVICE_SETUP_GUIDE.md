# MIA Homestead — Device Setup Guide

## Who this is for

Anyone. You don't need to know what an MCU is, you don't need to touch
a keyboard beyond answering a menu prompt, and you don't need to
understand anything about how the software works. If you can read a
label and plug in a connector, you can set up a new device.

## The convention

Every physical controller (an MCU) has:
- **A label** — a physical tag on the device itself saying what it's
  for ("WATERING," "FERTILIZER," "PH DOSING")
- **A color** — matching label colors on the device and its port, so
  you can match them visually without reading anything carefully
- **One port it belongs in** — ports are numbered and labeled on the
  Pi's expansion hub, matching the device's own label

You genuinely cannot plug something into the wrong port and have
anything bad happen — a mismatched device just won't pair, and the
system will tell you so.

## How to set up a new device

1. Run the setup helper:
   ```
   python3 core/device_setup_cli.py --db mia_homestead.db
   ```
2. It'll show you a numbered menu of what can be set up. Pick a number.
3. It tells you exactly what to plug in, which port, and where to mount
   it — in plain language, no jargon.
4. Plug it in, power it on. The system checks for it on its own within
   a few seconds — you don't do anything else.
5. If it doesn't show as connected after about a minute, double-check
   the connection and the CLI will let you know via the "waiting for
   you" list at the top of the menu.

## If you'd rather just ask

The assistant can do the same thing conversationally — "how do I set
up the watering controller" gets you the same instructions in chat,
and "is anything waiting to be set up" tells you if a device is plugged
in but hasn't been claimed yet.

## What happens behind the scenes (only if you're curious)

Every device role — what it's called, which port, where it mounts,
what it controls — lives in a plain text file under
`config/devices/roles/`. Adding a new kind of controller later means
adding a new file there, not touching any code. See
`core/device_registry.py` for the pairing logic and
`docs/MCU_PROTOCOL.md` for the exact handshake an MCU goes through
before the system trusts it to control anything.
