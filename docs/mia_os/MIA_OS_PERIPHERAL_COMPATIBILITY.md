# MIA OS: peripherals (Prompt 06 §10)

*Claude (Opus), 2026-11-17. Planning only. The rule from Prompt 05: Linux drives devices through its standard stacks;
MIA uses them only through capabilities (REQ-HW-006).*

| Kind | On the PC now (verified where marked) | Linux stack | MIA's use | Support |
|---|---|---|---|---|
| Monitors | ASUS XG27UCDMG 4K 240 Hz on the 7900 XTX; Samsung 1080p on the iGPU (verified) | DRM/KMS, KWin | the session on the main one; MIA OS must handle two GPUs driving two screens | full; test in PoC 3 |
| Audio | Windows devices (not enumerated) | PipeWire | voice in and out | full |
| Webcam | none found | V4L2, PipeWire camera portal | Look on the PC (later) | full |
| Keyboard, mouse | USB | libinput | everything | full |
| Game controllers | none | evdev | none | — |
| Printers | none | CUPS, IPP Everywhere | printing a list or a plan | full when present |
| Scanners | none | SANE, eSCL | the inbox | full when present |
| Storage (USB) | — | udisks | backups, imports | full |
| Serial and USB devices | — | tty, libusb | ESP32 flashing (PlatformIO), radios | full; needs a udev rule per device |
| Bluetooth | on (verified) | BlueZ | sensors, phones | full |
| Wi-Fi | Wi-Fi 6E, off (verified) | NetworkManager | fallback network | full |
| Meshtastic radio | planned | serial | off-grid messages | full |

**Standard over special:** prefer USB-class audio and video, IPP printers, BLE sensors with published profiles. A
device needing a Windows-only driver or vendor cloud is listed as unsupported, not worked around.

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-HW-019 | When a peripheral appears or disappears, MIA's capability record shall update within seconds and features that need it shall say it's missing rather than fail. | Should | R1 | PC | New | T: a udev event in a VM | DEC-0203 → 06 |
| REQ-HW-020 | The session shall work with two monitors on two different GPUs (the 7900 XTX and the processor's graphics). | Must | MVP | PC | New | M: PoC 3 | DEC-0191 → 06 |
