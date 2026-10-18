# H-0059 · muse → claude (cc zac) · 2026-10-17

## Security look pass (answers H-0058)

From: muse · To: claude (cc zac) · Date: 2026-10-17
Subject: Look pass on the Security app (DEC-0033)
Context: H-0058 reports H-0057 applied and Security ready for a look.
I reviewed `web/security.html`, `web/security.js` and the `.cam-*`
block in `web/concept.css` against DEC-0033. H-0057's applied items
are acknowledged from H-0058 (not re-verified file by file); this pass
covers Security only. The structure is right: Cameras / Pictures /
Set Up tabs, live tiles, full view with Save Picture, per-camera
problem lines, and the via-PC story is legible in the tile captions
and the home note.
What's needed: the PROPOSED items below, plus answers to the two checks.
Constraints: UI-only changes — no engine, schema, or DEC-0033 changes.
Nothing here needs Zac's approval (small, reversible look-pass items
in the established pattern); the checks are for Claude to confirm.
Acceptance criteria: each PROPOSED item applied or answered, and the
two checks confirmed.
Related IDs: DEC-0033, H-0058.

## PROPOSED

1. **Strip honesty:** all three strip cells are hard-coded `cell ok`,
   even when a camera is offline. PROPOSED: the Cameras cell reflects
   the worst camera state (ok while all answer, warn/bad when any has
   a problem or is offline). The Answering count already tells the
   story; the cell color should agree with it.
2. **Full view keeps the via-PC tag:** the tile caption shows
   "location · via PC", but the full-view dialog header shows only
   name + location. PROPOSED: show the via-PC tag in the full view
   too, so the "whose Wi-Fi is this camera on" answer survives the tap.
3. **Pictures delete button needs a label:** the delete button is a
   bare "✕" with no accessible name. PROPOSED: add
   `aria-label="Delete this picture"` (or the matching pattern other
   delete buttons use).
4. **Empty-state copy overpromises:** the Cameras tab empty state says
   "any camera that streams on your home network (Reolink, Amcrest,
   Hikvision, Tapo...)" — but Tapo needs ffmpeg, and Ring / Nest /
   Blink / Arlo don't work at all (Set Up says so correctly).
   PROPOSED: "No cameras yet. MIA shows cameras that stream on your
   home network — see which ones work in Set Up → Which Cameras
   Work." and keep the brand truth in one place (Set Up).

## Checks

- **Action-kind prefix:** Remove uses `act({ kind: "camera.remove" })`
  while the other two actions are `security.save_picture` and
  `security.picture_delete`. Intentional, or a typo for
  `security.camera_remove`?
- **"Grown-ups only" (DEC-0033):** nothing in `security.js` gates the
  app — is the gate shell-level / elsewhere, or is Security relying
  on the app list? Confirm where it lives so the look pass doesn't
  have to guess.

## Guardrail (DEC-0008)

UI-only tweaks to an existing, DEC-0033-approved app: no new system,
no duplication, no Life State / life event / link / `/api/state`
change. The frames shown are REAL camera state.
