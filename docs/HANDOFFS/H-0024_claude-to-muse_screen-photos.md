# H-0024: The rest of the screen photos
- From: claude (for zac) · To: muse (cc chatgpt) · Date: 2026-10-07
- Related: DEC-0018, `docs/design/IMAGE_REQUESTS.md`, H-0023

## Context
ChatGPT made the first two photos (`web/img/home.jpg` and `web/img/greenhouse.jpg`, now live). It's out of free image generation for today, so Zac asks if you can make the rest.

## What's needed
Every image in `docs/design/IMAGE_REQUESTS.md` that isn't marked ✅, with the descriptions given there:
- garage
- kitchen
- workout
- real-estate
- finances
- missions
- skills
- character
- property
- maintenance
- dashboard
- assistant

Match the two that landed: a golden-hour mountain-lake world, warm light, rich but not busy. The bottom third sits under text, so keep it calm.

## Constraints
- **Format:** landscape, at least 1536 × 1024, JPG (or PNG and Claude converts it), named exactly as listed.
- **Nothing personal:** no people's names, addresses, plates, faces or brands (DEC-0002).
- **Where they go:** commit them to `web/img/`. If you can only produce them in chat, give them to Zac and he'll pass them on.

## Acceptance criteria
- Each screen's hero shows its photo on the phone and the desktop.
- The title and tagline stay readable over it (the hero darkens the bottom; check yours does too).
