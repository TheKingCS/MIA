# H-0079: First boot on the real glasses: what Zac saw
- From: Claude (engine) · To: Claude Design · Date: 2026-11-03
- Related: DEC-0062, DEC-0063, H-0078, `docs/GLASSES_RELAY_PLAN.md`

## Context
`web/glasses.*` now runs on Zac's real glasses at
`mia-glasses.yhrhodes.workers.dev`, through the sealed relay. It's published
with `tools/publish_glasses.py`; `boot.js` in the `mia-art` repo replaces
`mia.js`. Pointer events are off there and input arrives as keys.

## What's needed
1. "A new connection is forming" sits too high on the real display.
2. She has no voice in the awakening: `MIA.speak` isn't on the relay, because
   `/api/heavy/speak` returns audio too large for it. Her voice has to come
   from the phone, through the glasses' speaker (Claude to wire).
3. User Sync has no conversation: answers come from the phone hearing the
   person, which needs starting from the glasses (Claude to wire).

## Constraints
Zac's priority is the screens he uses every day; these wait until then. Check
layout at the real 600x600 additive display, not only the browser preview.

## Acceptance criteria
The awakening reads correctly on the real glasses, spoken, and User Sync can
be answered out loud.
