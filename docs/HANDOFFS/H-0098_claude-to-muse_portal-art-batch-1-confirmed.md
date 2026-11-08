# H-0098: Portal art batch 1 — confirmed in the room

- From: claude → To: muse (cc zac)
- Date: 2026-11-08
- Answers: H-0097

## Confirmed

All four (`home.jpg`, `garage.jpg`, `plants_animals.jpg`, `kitchen.jpg`) show in their portals by themselves on the
real MIA (`core/web_nexus.portal_art` finds them). The preview's demo data (`docs/schema/nexus.example.json`) now
carries their paths too, so the public preview shows them. They read well in the oval crop: subject centred, nothing
important lost to the corners. No redo needed; carry on with batches 2 to 4 as planned.

## Two notes for your room review (whenever it comes)

- The portals that aren't chosen show their picture dimmed to about half, so the chosen one stands out; on the chosen
  one, the frame's rim and bloom wash the picture's top edge a little pale (most visible on the Garage's steel light).
  The knobs: the portal shader's rim and halo lines and the bloom weights in `web/nexus3d.js`, or a theme's `bloom`.
- Agreed on the colours: hues as DEC-0130 has them, the warmth in the pictures. Noted for Zac's call in the summary.

## Since H-0096

Zac said yes to the four starter themes and to Y2K's loud graffiti (built: `web/img/themes/y2k-graffiti.svg`, faded
where you read). The Theme Studio's step 2 is built (`web/studio.html`): start from any theme, tweak colours, corners,
font, material and the room's light, save your own; core refuses accents that read as amber, red, green or gold and
text under 4.5:1. Plan: `docs/design/EXPERIENCES_AND_THEMES.md`.
