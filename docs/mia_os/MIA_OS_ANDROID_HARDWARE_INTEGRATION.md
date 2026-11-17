# MIA OS: the phone (Prompt 06 §7)

*Claude (Opus), 2026-11-17. Planning only. The multi-device architecture is Prompt 12's.*

## 1. What the phone is (verified)

A Samsung Galaxy A54 (8 GB) running Android and MIA's own app (`android-phone/`): MIA's engine inside the app
(Chaquopy), a small local model (measured: `docs/PHONE_MODEL_TEST.md`), its own copy of his records synced with the
PC, the bridge to the glasses (Meta's Wearables Device Access Toolkit), the selection card and share sheet (the UAL),
location, notifications and the lock screen.

**MIA OS doesn't replace Android.** The phone stays an Android phone with MIA's app, by DEC-0205.

## 2. Hardware it brings

| Hardware | Used for | Status |
|---|---|---|
| Microphone, speaker | voice to MIA; her voice | built |
| Camera | Look (a photo and a question), receipts to the inbox | built |
| GPS | location quests, "remind me when I get home", trips | built |
| Bluetooth | the glasses; later sensors and the truck's OBD-II reader | glasses built; others later |
| NFC | pairing a device by tapping (later) | not used |
| Biometrics | unlocking the app's vault (Android Keystore, hardware-backed) | partial |
| Battery and charging state | homeostasis eases off on low battery | built |

## 3. Limits and how MIA handles them

| Limit | Handling |
|---|---|
| Small local model | answers it can, asks the PC's model when reachable (Tailscale), says which answered |
| Android kills background work | the app uses foreground services for the glasses and for sync, and catches up on open |
| Storage | records only; large files stay on the PC and are fetched on demand |
| Battery | no long jobs on the phone; the PC does them |

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-HW-015 | The phone shall publish its capability record (model size, camera, location, battery, the glasses connected) to the PC, and the PC shall offer phone-only actions only when the phone can do them now. | Should | R1 | Ph | New | T | DEC-0203, → 12 |
