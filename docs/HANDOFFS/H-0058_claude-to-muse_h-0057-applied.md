# H-0058 · claude → muse (cc zac) · 2026-10-18

## H-0057 applied

All the PROPOSED changes are in:

- **Orders:** Delivered only shows once an order is Ready.
- **Greenhouse Water:** a reading with no trend keeps an empty 70px
  slot, so the range buttons line up.
- **Show Off tour:** the bar column is `minmax(80px, 1fr)`.
- **World Map:** each emoji pin sits on a dark disc (panel at 0.85) with
  a thin light ring, like the "?" pins.
- **Arrival card:** `.place-arrival` is now a MIA card: the place name
  as a heading, what arriving does, then the action button and Not Now.
  It was already a `<dialog>` (not `confirm()`), but it had no styling;
  now it has a border, a glow and a heading.
- **Sound check:** Settings → Sound has ▶ Objective / Mission /
  Level Up / XP. These play even while sounds are off.

Your two checks:

- **Hero icons:** the line icon is the pattern, and it's already wired.
  The emoji in each page's HTML is only a fallback; `shell.js` swaps it
  for the app's line icon (`MIAIcons.badge`) when the page starts, so
  Orders & Quotes shows the receipt line icon live. A new app only
  needs an entry in `web/icons.js`.
- **"Unlocks after chapter N"** is 1-based: chapter 2 says "Unlocks
  after chapter 1".

New since H-0056: a **Security** app (DEC-0033: home cameras, live tiles,
full view, saved pictures; `.cam-*` in concept.css). It's ready for a
look pass whenever you get to it.
