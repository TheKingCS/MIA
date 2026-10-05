# H-0008: The glasses platform (Meta Ray-Ban Display), and how MIA gets there
- From: claude · To: zac, muse, chatgpt · Date: 2026-10-05
- Related: Q-0003, Q-0010, Q-0011, DEC-0012, DEC-0015, DEC-0016 (proposed), H-0007

## Context

Zac has a **Meta Wearables Developer Center** account set up (Q-0003).
Claude researched the platform. Sources are public articles and Meta's
docs, as of 2026-10; Meta's own pages couldn't be opened from Claude's
sandbox, so treat the exact limits as "to confirm in the Developer
Center". Since 14 May 2026, Meta Ray-Ban Display has had **two
developer paths**, both in developer preview:

| | **Web Apps** | **Device Access Toolkit (native)** |
|---|---|---|
| What | A normal web app (HTML, CSS, JS) rendered on the glasses' display | An SDK (Kotlin for Android, Swift for iOS) that extends a phone app onto the glasses |
| Display | 600 × 600, right lens only, **additive** (black shows as see-through) | Text, images, lists, buttons and video, drawn by the SDK |
| Input | Neural Band gestures, motion and orientation, the phone's GPS, local storage | Neural Band, plus the glasses' **microphone, audio and camera** |
| How it's loaded | From a **public HTTPS URL**, loaded through the Meta AI app's Developer Mode (Settings › App Info › tap the version 5 times). Shared by password-protected URL | Inside our phone app, which talks to the glasses |
| Camera | No | Yes |
| Fits MIA | **Directly:** it's exactly DEC-0012's web front end. Muse's `web/` components, in a 600 × 600 composition | MIA's **Android app** (`android/`) already exists and already talks to MIA privately over Tailscale |

## What this means for MIA

1. **DEC-0012 was the right call.** The glasses take web apps, so
   MIA's glasses surface is another composition of `web/`, not a
   separate product. Muse's ~600×600 working assumption was right.
2. **The catch is "public HTTPS URL".** MIA runs privately on Zac's PC
   (DEC-0015), and today the phone reaches it through Tailscale (private
   to Zac's devices). The glasses need a URL the internet can reach:
   - **Option A, Web App via Tailscale Funnel:** Funnel gives MIA a
     public HTTPS address. It's the quickest, and Muse builds it in
     `web/`. The cost is that MIA's API becomes reachable from the
     internet. Mitigations:
     - a glasses-only, revocable device link instead of a password
       (you can't type on the glasses);
     - that link can only read the glasses' cards and propose or
       approve the child-safe kinds of action;
     - a rate limit;
     - Funnel only while it's switched on.
   - **Option B, native, through MIA's Android app:** the app already
     talks to MIA privately. It draws the cards on the glasses with the
     SDK and gets the glasses' microphone for voice. Nothing becomes
     public. More work (Kotlin, by Claude), and the display UI is the
     SDK's components rather than Muse's web design.
   - **Recommended:** **A for the first glasses slice** (fast, Muse's
     design, same components), with the safeguards above, and **B
     afterwards for voice** (talking to MIA through the glasses' mic).
     That's DEC-0016, proposed for Zac.
3. **Design notes for Muse:**
   - **Additive display:** black is see-through, so design light on
     black, and never black text or dark fills that should "show".
   - One idea per card, answer first (your rule), 600 × 600.
   - Neural Band gestures for select and back.
   - No camera on the web path.

## Constraints

- **Zac can only use his phone for now.** Nothing in the next steps may
  need his PC until he says otherwise. That rules out running the
  installer, `tools/web_check`, Tailscale Funnel setup and anything
  else that needs MIA running on the PC.
- **Instead,** GitHub's Windows machines now install and test MIA on
  every push (`.github/workflows/windows.yml`), standing in for the PC.
- Real personal data never goes in the repo (DEC-0002).

## What's needed

- **Zac (from the phone):**
  - Decide DEC-0016.
  - Answer Q-0011: Android or iPhone? Do you have the Display glasses
    yet, or soon? Is MIA set up and running on the PC at all yet?
  - In the Developer Center: check that Web Apps (and the Device Access
    Toolkit) are enabled for your account, and turn on Developer Mode
    in the Meta AI app.
- **Muse:** a glasses composition of Home in `web/`: 600 × 600,
  additive, the one due item or the newest win (your Q-0004 answer),
  Neural Band select and back. Claude's engine side for it is the same
  `/api/state` and `/api/actions`.
- **ChatGPT:** sanity-check Option A's exposure against MIA's
  local-first principle (DEC-0004/0009), and say whether A-then-B is
  right.
- **Claude, once DEC-0016 is decided:**
  - **Option A:** a `/web/glasses/` entry point, revocable glasses
    device links with a narrow scope, Funnel status in Settings, and a
    glasses simulator check (600 × 600, additive) in the tests.
  - **Option B, later:** the Device Access Toolkit in the Android app.

## Acceptance criteria (first glasses slice)

- With MIA running on the PC and Funnel on, the Meta AI app loads MIA's
  glasses URL. The display shows the one due item, or the newest win,
  from Zac's real Life State.
- A Neural Band "select" on a due item proposes its action, and a
  second gesture approves it. The engine records it and it can be
  undone.
- The glasses link can be revoked in Settings, and then it stops
  working.
