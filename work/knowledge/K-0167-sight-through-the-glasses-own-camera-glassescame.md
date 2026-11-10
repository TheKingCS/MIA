---
id: K-0167
kind: implementation
title: Sight through the glasses' own camera (GlassesCamera.kt)
status: confirmed
by: claude
created: 2026-11-09T09:43:52+00:00
concerns: android-phone/app/src/main/java/com/mia/phone/GlassesCamera.kt, android-phone/app/src/main/java/com/mia/phone/Voice.kt, core/glasses_voice.py, core/parity.py
from: dec:DEC-0062, dec:DEC-0125
---
The last parity todo, sight:glasses. Said through the glasses, 'what am I looking at?' (core/sight.wants_look) now answers from core/glasses_voice.handle with {say: 'Let me look.', look: question} instead of a Talk turn. Voice.kt sees `look`, GlassesCamera.photo opens a camera-only toolkit session (AutoDeviceSelector), waits for STARTED, adds a camera (StreamConfiguration LOW, 7 fps, compressed, as Meta's 1.0.1 samples do), waits for STREAMING, takes one capturePhoto (PhotoData Bitmap or HEIC to JPEG), closes the camera and stops the session, then posts the JPEG to /api/sight with x-question and says Sight's `said`. The toolkit camera permission is Meta AI's (Settings → Glasses → Let MIA Use the Glasses' Camera, RequestPermissionContract().createIntent from a plain Activity). mwdat-camera brings Android's CAMERA permission, so Look's phone camera now asks for it before opening the camera app (MainActivity pendingCapture/pendingPick). API taken from facebook/meta-wearables-dat-android samples (BirdSpotter, CameraAccess) at the same 1.0.1. Compiled in CI; untried on real glasses: the display web app (DEC-0062) and a toolkit session may have to take turns.
