# The "MIA on a phone" test (DEC-0019, Phase 1)

*Claude, 2026-10-07. The plan: `docs/PHONE_FIRST_PLAN.md`. This is what
the test found.*

## The question

Can MIA's own engine (`core/`, Python) and her screens (`web/`) run inside an Android app, with no computer? What does it cost in size, start time and memory, and what doesn't come along?

## Step 1: does the engine need anything a phone can't have? (done, in this repo)

On a phone-like Python 3.13 (no Qt, no desktop voice, no Plaid, no psutil, no offline library, no Web Push sender), MIA's engine and server failed on six imports at first. Every one was an optional feature. Each now loads only if its package is there, and says plainly when it isn't available on this device:

| Feature | Package(s) | On the phone, for now |
|---|---|---|
| Offline reference library (Kiwix) | libzim | "isn't available on this device" |
| Desktop voice and its effect | numpy, sounddevice | the phone will use Android's own speech (Phase 2) |
| Bank sync | plaid-python | "isn't available on this device yet" |
| Battery, system health | psutil | Android reports these (Phase 2) |
| Sending Web Push | pywebpush, py_vapid, requests | not needed: MIA *is* on the phone |

After that, on the phone-like Python:
- the engine built in **0.3–0.8 s**;
- the server started in **0.5–1.0 s**;
- all 12 screens' data loaded;
- an action ran and was undone.

**The phone needs five packages:** FastAPI, uvicorn, cryptography, astral and mutagen. Only two contain compiled code needing Android builds: **cryptography** and **pydantic-core** (inside FastAPI).

`tests/test_phone_ready.py` keeps it that way. It builds the engine and server with every desktop-only package blocked, so a new hard import fails a test instead of someone's phone.

## Step 2: the app (`android-phone/`, a separate test app)

- **Chaquopy** runs Python 3.13 inside the app. That's the version CPython officially supports on both Android and iOS, which matters because Zac moves to an iPhone later.
- The repo's `core/`, `server/` and `web/` go in unchanged as `mia.zip`. On first start, the app unpacks them into its private storage, where MIA's `data/` folder sits beside them as on a computer. An update replaces only code; the person's data stays.
- `mia_phone.py` builds the engine and serves it on 127.0.0.1, the phone talking to itself and reachable from nowhere else. The screen is `web/` in a WebView.
- **Install:** it installs *beside* the companion app (`com.mia.phone`), from the **phone-spike** release on GitHub.
- **CI** (`.github/workflows/android-phone.yml`) builds the APK, starts it on an Android emulator (`ci_smoke.sh`), checks MIA comes up and answers, runs an action, takes a screenshot, and notes memory and APK size.

## Results on Android

*(filled in from the CI run below)*

## What this test does not cover yet (Phase 2)

- **Onboarding.** The test app makes a person called "You".
- **Talk.** There's no model on the phone yet; Talk will say it can't reach a model.
- **Phone-native features:** notifications, Android speech, battery.
- **Background work.** Android stops idle apps; MIA's daily checks move to Android's scheduler.
- **Battery over a day.** That needs Zac's real phone, not an emulator.
- **iPhone.** Same plan with BeeWare's iOS packaging (Phase 5).
- **The data folder.** It lives beside the code because 70 engine files compute it that way. A single "where MIA keeps her data" setting would be cleaner, and is worth doing before sync.
