# MIA OS: Zeta Astralis (Prompt 11 §16)

*Claude (Opus), 2026-11-17. A future concept, not a product: a forearm-worn display with a compact MIA, the phone as
its computer. `MIA_OS_FUTURE_CAPABILITIES.md` lists it as research.*

## 1. Interface

| Part | Design |
|---|---|
| Layout | a wide, short screen (about 4:1): the orb at the left, one card at a time to its right |
| Moves | swipe between cards; tap to open; long-press to talk |
| Cards | what's due, a quick note, a timer, the greenhouse, a message, music |
| Quick actions | the card's suggested action (the one change path) |
| Voice and audio | the phone's microphone and an earbud |
| Notifications | one line, a short vibration |
| Look | the reduced token set (as the glasses), solid surfaces |

## 2. What can be prototyped now

| Step | Hardware |
|---|---|
| The compact layout as a web page at its aspect ratio | any screen (a browser window) |
| On the wrist | **Zac's choice (Q-86): an old Android phone, or the Raspberry Pi 5 with a small screen**, in a forearm mount. The phone runs MIA's phone app in the compact layout; the Pi runs the same web screens full screen (cage, as the Pi's kiosk, DEC-0191), reaching the PC's engine over the home network |
| Custom display | a flexible display with a microcontroller: custom hardware, later |

**Power:** the display shows nothing while not looked at; the phone does the work.

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-VIS-022 | A compact layout at about 4:1 shall show the orb and one card at a time, using the same screens and change path. | Could | Later | Wearable | New | D: a prototype | DEC-0239 → 11, 12 |
