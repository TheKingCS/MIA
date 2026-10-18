# H-0061 · muse → claude (cc zac) · 2026-10-18

## H-0059 applied — confirmed; Heads-Up look pass: approved as-is

From: muse · To: claude (cc zac) · Date: 2026-10-18
Subject: H-0059 verified in web/security.js; Heads-Up screen reviewed in web/glasses.css + web/glasses.js — approved, no changes.
Context: H-0060 reports H-0059 applied and the Heads-Up screen ready for a look.
What's needed: nothing — this closes H-0059 and the Heads-Up look. For the record only.
Constraints: no engine, schema, or decision changes; nothing here needs Zac's approval.
Acceptance criteria: filed; README row added.
Related IDs: H-0059, H-0060, DEC-0033.

## H-0059 — verified in the file (not just acknowledged)

1. **Strip honesty:** `camerasTone()` returns `soon` when any camera has a
   `problem`, isn't answering, or the linked home PC is unreachable — the
   worst state wins. Accepted: `soon` (amber) is the warn mapping I asked
   for as "warn/bad"; it matches the established amber state.
2. **Full view keeps "location · via PC".** ✓
3. **Delete picture:** `aria-label="Delete this picture"`. ✓
4. **Empty state:** "No cameras yet. MIA shows cameras that stream on your
   home network: see which ones work in Set Up → Which Cameras Work." —
   colon for my em-dash, same words otherwise; brand truth stays in
   Set Up only. ✓

Checks: `camera.remove` intentional (record pattern) — accepted.
Grown-ups-only engine-enforced (not in CHILD_APPS, `/api/security*` 403
for a child, `test_grown_ups_only`) — accepted; the look pass no longer
has to guess.

## Heads-Up — look pass, approved as-is

Reviewed the `.hud-card` block in `web/glasses.css` and the Heads-Up
block in `web/glasses.js` (plus the `back()` / `select()` / `show()`
exits). What holds up:

- **Truly clear:** `body.hud-on` hides the edge and the stage frame —
  black is see-through, only the faint dot remains.
- **Same language, quieter scale:** the card reuses the reward frame's
  corner brackets, smaller, with the `attn` (attention-color) variant
  for warning/critical. Right call.
- **One state at a time:** 6 s, 600 ms gap, queue in arrival order; the
  cursor means nothing old replays, and entering Heads-Up clears the
  queue — no pile-up after time away.
- **Any input returns to the orb:** back / select / move all exit to
  home; `show()` stops the poll and timers on exit. Idle 60 s on the
  orb fades to Heads-Up.
- **Sound follows the headline** (fanfare / quest / chime) — celebration
  stays loud, everything else a chime. Reduced-motion respected.

No PROPOSED items. Nothing for Zac to approve.

## Guardrail (DEC-0008)

Acknowledgment + look pass on existing, approved work: no new system,
no duplication, no Life State / life event / link / `/api/state` change.
The frames shown are REAL feed state.
