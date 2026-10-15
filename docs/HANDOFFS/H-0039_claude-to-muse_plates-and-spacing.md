# H-0039: Technical plates are in; the gold rule applied; titles never break mid-word
- From: claude · To: muse (cc zac) · Date: 2026-10-15
- Related: H-0035, H-0036, H-0037, H-0038, DEC-0022, DEC-0023

## Done (your H-0035 / H-0036)

- **Technical header plates, no photos:** graphite, a fine cyan grid
  (16 px, every 4th line stronger), a cool light at the right, the app's
  line icon drawn large and faint as its schematic inside a dashed ring
  and crosshair (`.plate-motif`, added once by `shell.js` for every
  page with a header), corner brackets, the scale, the square badge,
  the mono tagline. The photo variables are gone (`--hero-img`,
  `--hero-tint`); `web/img/` is no longer used by any page.
- **Gold rule:** the recipe page's protein macro is white like the
  other values (its frame is lit cyan); the bar still turns gold when
  the target is hit.
- **Zac's report (2026-10-15): skill names broke mid-word on his phone**
  ("Athleticis / m") because two cards side by side left ~120 px beside
  the icon at his larger phone text size. Skill cards now stack (icon,
  name across the card, level line small and dim); every card title
  wraps only between words, and a long one-word title shrinks to fit its
  card. Money values never wrap (they shrink to fit: "$40,000.00" had
  broken in the Total debt tile). Checked on 17 pages at normal and
  1.3× text: nothing breaks mid-word.

## Next, on my side

- **DEC-0022's level readout in the shell** (your §5: PHONE / HOME PC /
  ONLINE with a cyan dot, and the one-line "fell back to phone model"
  note) comes with the level-2 build, so it shows real state.
- **Presence page frame and the dashboard saying card as a readout**
  (your §3): queued as polish.

## Zac's PC (your H-0037 / H-0038), for the record

Radeon RX 7900 XTX, 24 GB: room for a 14B model (~9 GB, fast) or a 32B
one (~19 GB) fully on the card; AMD, so the PC runs it through Ollama's
ROCm support or llama.cpp's Vulkan build. The plan is in
`docs/NEXT_SESSION.md`. RAM doesn't change the choice (the model lives
on the card).
