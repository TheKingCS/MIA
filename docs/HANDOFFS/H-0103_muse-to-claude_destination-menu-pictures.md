# H-0103: The eight area paintings become the destinations' menu pictures

From: muse
To: claude (cc zac)
Date: 2026-11-11
Subject: The eight area paintings become the destinations' menu pictures (NAVIGATION_ARCHITECTURE.md §4.5)

## Context

DEC-0153 is built — MIA opens on the Dashboard and her sidebar is Zac's
eight destinations. The architecture (§4.5) says the area rooms stay as
the Spatial look of each destination's hub, and "Muse's eight area
paintings (`web/img/portals/`) can become the destinations' pictures in
the menu. That's for Muse to say, as a handoff." This is that handoff.

Saying yes: the menu gets a picture per destination, and the paintings I
made for the Nexus portals get a second home now that the Nexus keys its
paintings by universe (Living Worlds) and ignores the old area keys.

## What's needed

1. Each of the eight destinations gets a menu picture: Dashboard, Home,
   Garage, Finances, Health and Fitness, AI Tools, Missions, Settings.
2. Reuse where the mapping is clean: Home ← home, Garage ← garage,
   Health and Fitness ← health. The other five destinations (Dashboard,
   Finances, AI Tools, Missions, Settings) have no matching area
   painting — they need new pictures, either a small new batch of five
   from me or folded into the remaining portal batches (batches 3–4,
   eight pictures still owed under H-0096).
3. Keying question for you: the Nexus now keys paintings by universe and
   ignores old area keys. Do the menu pictures get a destination-keyed
   lookup (new keys in `portal_pictures.py`), or a destination→area map
   that reuses the existing area keys? My preference: destination-keyed,
   so a destination's picture survives the next regrouping — but that's
   your call, it's your file.
4. The glasses menu (orb / menu / Nexus) is text-first; tell me if the
   menu pictures belong there too or stay on PC/phone.

## Constraints

- DEC-0130 hues hold; nothing personal in any picture (DEC-0002);
  static files under `web/img/`, no engine change, no new Life State,
  no new `/api/state`.
- Guardrail (DEC-0008): UI-only reuse of real files that already exist;
  no new system, no duplication — the paintings already live in
  `web/img/portals/` and `portal_pictures.py` already serves them.

## Acceptance criteria

- Each of the eight destinations shows its picture in the menu on PC and
  phone.
- The five new pictures (or the batch plan for them) are agreed, and the
  keying is settled so the area paintings don't get orphaned twice.

## Follow-up, not this handoff

The architecture's §5 also leaves the world portals' art to a handoff
from me — that one comes once the menu pictures are settled, so the two
batches don't collide.

## Related IDs

DEC-0153, DEC-0130, DEC-0002, DEC-0008, H-0096, H-0097, H-0099, H-0100,
`docs/NAVIGATION_ARCHITECTURE.md` §4.5.
