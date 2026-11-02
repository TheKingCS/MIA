> **Update, 2026-11-02: most of this is out of date. DEC-0062 and DEC-0063
> reverse it.** Her face on the real glasses is now a Web App, so
> `web/glasses.*` is the real surface again. A test page already runs on
> Zac's glasses from `thekingcs.github.io/mia-art` (orb animation, icon, key
> through the install link, crypto, speech). She opens from her icon; a tap
> makes her listen; the phone no longer draws on the glasses.
> What still stands: keep the steps in the engine, as data, because the page
> will be public and hold no data. It will reach the engine through a sealed
> relay (not built), so it can't call `/api/...` directly or assume the
> phone's server. Claude will tell you the shape when the relay exists.

# H-0078: The real glasses draw natively now, so slice 3 needs an engine-first shape
- From: Claude (engine) · To: Claude Design · Date: 2026-11-02
- Related: DEC-0059, DEC-0060, DEC-0023, `docs/GLASSES_FIRST_BOOT_PLAN.md`,
  `android-phone/app/src/main/java/com/mia/phone/MetaGlasses.kt`

## Context
MIA now runs on Zac's real Meta Ray-Ban Display glasses through the phone
app. `web/glasses.*` does not appear on them: `MetaGlasses.kt` draws
`/api/glasses` with Meta's own display views. A tap opens her (DEC-0060).
Slices 1 and 2 (the orb states, the awakening) still exist only in the
browser preview.

The native surface can do far less than `web/glasses.*`:
- Fixed text styles and colors, and Meta's icon set. No CSS, no glow, no
  animation, no custom font. Each send replaces the whole screen.
- 600x600. Images and video load from `https` URLs only, so nothing can
  come from the phone's own `127.0.0.1` server. Video is under 400px a
  side and 70,000 pixels in total.
- Keep to a few buttons on a screen.

## What's needed
1. Build slice 3 (User Sync, Meals) so its steps come from the engine as
   data (`core/`, an `/api/...` read plus `/api/actions`), with the screen
   only drawing them. Then the native side can draw the same steps. Logic
   inside `web/glasses.js` would have to be rebuilt.
2. Keep each step to a title, a short line and a few choices.
3. Tell Claude in a handoff when the shape is settled, and I'll draw it in
   `MetaGlasses.kt`.

## Constraints
- I'm working in `MetaGlasses.kt` on the look. `web/glasses.*` and the
  first-boot work stay yours, so we don't collide.
- The orb needs a public `https` image, which DEC-0059 didn't plan for.
  That's Zac's call; I've asked.

## Acceptance criteria
A User Sync step can be read from an engine endpoint and answered through
`/api/actions`, with no logic only `web/glasses.js` knows.
