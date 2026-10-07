# MIA on just a phone (and glasses): the plan

*Proposed by Claude, 2026-10-06, at Zac's request. **Approved by Zac
2026-10-07 (DEC-0019, Q-0015): engine on the phone, the spike now,
Android first, and iPhone soon after, because he's switching to one.**
Q-0016 still asks ChatGPT for a vision review.*

## The goal

Zac (2026-10-06): MIA should be sellable, so it has to be easy for someone who only has a phone, or a phone and Meta's Display glasses. The groundwork is building toward an augmented-reality, gamified-life HUD, "so it kind of has to run on the phone and connect to glasses."

## Where MIA is today

- **The engine runs on a computer.** That's MIA's brain: every store, the action rules and undo, missions and XP, the communication gate, the safety floor, and the ~175 Assistant tools. It's Python (`core/`) and runs without the desktop app (`core/core_runtime.py`, `python core_main.py`).
- **The phone is a remote control.** The web screens (`web/`) and the Android companion app reach the computer over Tailscale. If the computer is off, the phone shows "Can't reach MIA at home."
- **The language model runs on the computer too:** llama3.2:3b through Ollama. So do voice recognition (Vosk), bank sync (Plaid), email intake, OCR and PDF reading.

**What already travels well:**
- **The web front end.** Every screen talks to the engine only through `web/mia.js` and `/api/*` (DEC-0012, DEC-0017). The same screens can run inside a phone app, on a computer or on glasses, unchanged. The web-parity work under way now is not throwaway; it is the phone app's interface.
- **The engine is free of the desktop app.** `core_runtime.py` builds MIA with no Qt at all. 15 files in `core/` still use Qt for a feature: PDF reading, OCR, background workers, music, avatar, boot sound, Plaid's link window. Each of those needs a phone version or a "not on this device" note.
- **The model is replaceable.** Facts are assembled in code and the model only phrases them. The crisis floor never depends on it. The screens and actions don't need the model at all; only Talk does.

## The recommendation: the phone is MIA's home

Run MIA's engine **on the phone itself**, inside the MIA app. A computer, or later a small home box, becomes an optional helper, not a requirement.

```
            ┌───────────── the MIA phone app ─────────────┐
 glasses ◄──┤  the screens (web/, unchanged, in the app)  │
 (cards,    │  MIA's engine (core/, running on the phone) │
  voice)    │  a small on-phone model (Talk)              │
            └───────────────┬─────────────────────────────┘
                            │ optional, encrypted
            ┌───────────────┴──────────────┐
            │ a home helper: PC / Pi       │  bigger model, bank sync,
            │ (or, if Zac chooses, cloud)  │  email, sensors, household sync
            └──────────────────────────────┘
```

**Why this, and not the others:**

| | Phone-only works | Private (data stays yours) | Works offline | Glasses | Cost to run | Effort |
|---|---|---|---|---|---|---|
| **A. Engine on the phone** (recommended) | ✅ | ✅ | ✅ | ✅ the phone is the glasses' hub anyway | none | big, but reuses `core/` |
| B. MIA hosted in the cloud | ✅ | ❌ unless end-to-end encrypted | ❌ | ✅ | servers per customer | medium, plus running a service |
| C. Keep the home computer (today) | ❌ | ✅ | at home | ✅ | none | none |

- **Meta's glasses already pair through the phone.** Native glasses features (the Device Access Toolkit, the glasses' microphone) come through a phone app (DEC-0016). So "MIA runs on the phone and the glasses connect to it" follows the platform's own grain.
- **It keeps MIA's promise.** Offline-first, and your data is yours (DEC-0001, DEC-0002). A cloud MIA is the easy road for selling, but it would make MIA a different product, so it should be Zac's explicit choice (Q-0015).

## How we'd get there (phases)

Each phase ends with something real on a phone, and each one is a go/no-go point.

**Phase 0 (now, unchanged).** Finish web parity (`docs/WEB_PARITY.md`). It is the phone app's interface. New rule for new code, so we don't dig the hole deeper: **works headless** (no Qt in what an action or page needs), **works offline**, and **no computer-only service as a requirement**.

**Phase 1: "MIA on a phone" spike (about 2 sessions).** Prove the engine runs inside an Android app. The plan is the existing companion app plus **Chaquopy**, which embeds Python in an Android app and is open source. Inside it:
- `core_runtime` and the server run on the phone;
- `web/` loads from the phone itself in the app's WebView;
- one full slice works: sign in, Home, tick a focus item, undo.

We measure:
- install size;
- start time;
- battery use over a day;
- which Python packages don't run on Android. FastAPI's validation library and `cryptography` are the ones to check.

If Python on Android fails, the fallback is a native engine: a rewrite, measured in months. We'd know before committing to it.

**Phase 2: phone-only MIA for one person (Android).** Everything in `web/` works offline on the phone with no computer:
- notifications through Android itself;
- voice through Android's own speech recognition and text-to-speech (the companion app already uses them);
- export, and an encrypted backup to the person's own cloud drive.

For Talk, a small on-phone model: llama.cpp, a 1–3B model, or a phone's built-in model where there is one. Without one, MIA still works: every screen and action, and a plainer "no-model" Talk.

Features that need a helper say so plainly. Today that's bank sync, email intake, OCR of large files and sensors.

**Phase 3: the glasses, from the phone.** The phone app sends MIA's glasses cards (Muse's 600 × 600 compositions, H-0012) and takes the glasses' microphone through Meta's toolkit. This is the first real step of the HUD:
- glanceable cards: next focus item, mission progress, a level-up;
- voice in and out;
- celebrations (DEC-0014).

What the toolkit allows on the Display (cards, input, pushing a card) still needs confirming. That's Q-0003, which is still partly open.

**Phase 4: the optional helper, and households.**
- **A computer or a Pi at home** adds a bigger model, bank sync, email, sensors and the desktop. The phone syncs with it.
- **Household members on their own phones** share household stores through it, or through an end-to-end-encrypted relay if Zac chooses one.

MIA's history log (`core/life_events.py`, append-only) is the natural basis for sync.

**Phase 5: iPhone (moved up, 2026-10-07).** Zac is switching to an iPhone, Meta's glasses work with iPhones too, and about half of buyers have one. Python runs on iOS (officially supported since CPython 3.13, PEP 730; BeeWare packages it), but App Store review is stricter. It comes right after phone-only Android works (Phase 2), before the household helper if Zac moves first. The Android work keeps it open throughout: the engine stays plain Python with no Android-only parts, and the phone shell stays thin.

**Phase 6: ready to sell.** None of this blocks building, but each item is real before a store listing:
- Play Store (and later App Store) listing and onboarding with no Tailscale;
- a privacy policy;
- model licences (Llama and Gemma terms allow commercial use with conditions);
- Plaid production approval and its per-user cost;
- payments;
- support;
- a name and trademark check;
- **children:** selling to under-13s brings COPPA rules (child accounts exist today, DEC-0001).

## What this means for the AR game HUD

The game layer is already engine data that any screen can show: missions, XP, skills, rarity, prestige, streaks, celebrations. The HUD is one more surface over it (`docs/VISION.md`, "User OS" and "Spatial Interface").

On today's Display glasses, that means cards, voice and notifications, driven by the phone. Spatial anchoring (a card floating over the real mower) waits for glasses that can do it. The engine already supports it: assets, tasks and missions are linked (`core/links.py`), and a future "spatial asset" layer adds 3D/anchor data beside them, not instead of them.

## Risks, honestly

- **Python on Android may not carry everything.** Phase 1 exists to find out cheaply.
- **Battery and memory.** A phone kills background apps. MIA's daily checks would move to Android's own scheduler (WorkManager). A local model is heavy, so it loads only when you talk.
- **Two engines in one household need sync.** That's the hardest software problem here, which is why it's Phase 4 and not Phase 2.
- **The desktop Qt app** becomes a helper app over time. Web parity is how it retires without losing features.

## Decisions

- **DEC-0019 (approved, 2026-10-07):** the phone is MIA's home; the computer becomes an optional helper; Android first, iPhone soon after.
- **Q-0015 (answered):** on the phone, not the cloud; the spike now; Android first (Zac moves to iPhone later).
- **Q-0016 (ChatGPT, open):** vision review of this plan.
