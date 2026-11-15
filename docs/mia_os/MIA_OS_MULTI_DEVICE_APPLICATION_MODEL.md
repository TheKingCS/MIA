# MIA OS: applications across devices (Prompt 03 §15, §16)

*Claude (Opus), 2026-11-15. Planning; nothing built. Part of [MIA_OS_APPLICATION_FRAMEWORK.md](MIA_OS_APPLICATION_FRAMEWORK.md).
Prompt 12 designs the distributed system itself.*

## 1. The model: one application, many surfaces (option 1)

| Option (prompt §15) | Fit for MIA |
|---|---|
| 1. One app with device-specific interfaces | **recommended**: what MIA is today (one engine, web pages, phone app, glasses cards, voice) |
| 2. Separate apps sharing services and data | only for a device with its own platform (greenhouse firmware) |
| 3. A distributed app of device endpoints | later, for the Pi and sensors (Prompt 12) |

DEC-0125 is the rule: every feature works by voice and without it, on the PC, the phone and the glasses; devices
change how it's shown, not what it can do. `core/parity.py` measures it per app and per way (voice, web, glasses);
`work/parity.json` decides each gap.

## 2. Device classes and what they get

| Device | Surface | Runs | Offline |
|---|---|---|---|
| PC (MIA OS) | the full web screens, the classic view, voice | the MIA Runtime, the model | everything local |
| Phone (Android) | the phone app (its own screens over the same API), voice | a smaller engine and a small model; syncs with the PC | its own copy; syncs when it can reach the PC |
| Glasses | cards (`core/glasses_cards.py`), voice | nothing: through the phone | while the phone is |
| Pi | the runtime as a service; maybe a small screen | the runtime; sensors | everything local |
| Truck (later) | the phone or a Pi with a screen; OBD-II data | as the phone or Pi | yes |
| Wearables, displays | cards like the glasses | through the phone | — |

## 3. Consistency

Identity: the same profile on every device (a linked device, `core/linked_devices.py`). Data: synced stores (`core/sync.py`).
Settings: person settings sync; interface preferences stay per device. Capabilities: declared per device in the
manifest; a capability a device can't run is offered on the device that can ("open it on the PC" links exist).

## 4. Interface integration (prompt §16)

| Element | Owned by |
|---|---|
| The frame: sidebar, search, Talk, the bottom bar on the phone | the OS's MIA shell (`web/shell.js`) |
| Theme | tokens (`web/tokens.css`, DEC-0023/0136): no app hard-codes a colour |
| Notifications | the gate and the shell |
| Context actions on a selection | the UAL, for every app |
| Search | the shell (Ctrl+K), over every app's records |
| Voice | the shell and Talk |
| Accessibility | the shell's defaults (text size, contrast) plus each app's markup |
| The app's own content and layout | the app |

A conventional window when opened directly, and conversational access through its capabilities, from the same code:
that's how every MIA app already works.
