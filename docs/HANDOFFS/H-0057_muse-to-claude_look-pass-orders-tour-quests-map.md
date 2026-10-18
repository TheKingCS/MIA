# H-0057: Look pass — Orders & Quotes, Greenhouse Water, Show Off tour, Quests / Party / World Map / Places / Sound
- From: Muse · To: Claude (cc Zac) · Date: 2026-10-17
- Related: H-0054, H-0055, H-0056, DEC-0030, DEC-0031, DEC-0032

Guardrail: everything below is UI-only on engine features that already
exist. No new systems, no Life State changes, no duplication. The
arrival-prompt card formats an existing proposal; the sound check is a
button on the Settings page.

## H-0054 checks — answered

- **MIA Remembers: keep the heading** (same style as Today's Focus and
  Upcoming). Heading hierarchy wins over a mono eyebrow here.
- Reward Shop **Claimed** text: good.
- What I Used Fix / Forget Title Case + focus ring: good.
- DEC-0031 scrub note: noted, built in per H-0055.

## H-0055: Orders & Quotes, Greenhouse Water, Show Off

- **Orders & Quotes: approved as built.** Craft-card reuse is right;
  Email Quote as the amber primary on a quote is right.
- PROPOSED: hide **Delivered** until an order's status is Ready.
  Delivered takes the build out of stock once, and two terminal buttons
  (Delivered, Cancel Order) sitting side by side on every open order
  invites a mis-tap. Keep Cancel Order as-is (the gate confirms it).
- Check: the hero icons are still emoji (🧾 on Orders & Quotes) while
  H-0055 says line icons exist (`business`, `grow_lab`). Wire the
  hero-icon to the line icon, or leave the emoji — your call, just say
  which one is the pattern.
- **Greenhouse Water** (grow.html now redirects to the Greenhouse, so
  this pass applies to its Water tab): the readings row
  (`1fr 70px auto`) reads well at phone width, and the "Outside Your
  Range" list plus "MIA only flags readings" line is exactly the right
  tone. Keep both.
- PROPOSED: when a reading has no trend, `spark()` returns null and the
  middle column collapses, so that row's range button shifts left of
  the others. Keep a fixed 70px slot (an empty span) so the rows line
  up.
- **Show Off tour: approved as built.** One card at a time, the
  Back / Voice / Next grid, the always-reachable Stop link, the Voice
  toggle with `aria-pressed`, reduced-motion respected.
- PROPOSED: on the tour list only, widen the bar column from
  `minmax(60px, 1fr)` to `minmax(80px, 1fr)` — at narrow phone width
  the 60px floor squeezes the stat bars.

## H-0056: Quests, Party, World Map, My Places, Sound

- **Quests: approved as built.** The vertical path with its connector,
  done green / current gold glow / locked dimmed, the season banner,
  the dashed offer cards — all read clean.
- Check: a locked step says "Unlocks after chapter N". Confirm N is
  the 1-based chapter number, so chapter 2 says "Unlocks after
  chapter 1".
- **Party: approved as built.** Raid cards reusing the quest card,
  crew chips with done/total, the opt-in leaderboard copy ("counts
  wins, never money, never what wasn't done"). Pick-crew ticking
  everyone by default is the right default — keep it.
- **World Map: approved with one PROPOSED change.** The fog, the
  glowing cleared tiles, the edge-only outline, the legend, the
  `role="img"` label — all good. The pins are the weak part, as you
  said: emoji drawn straight onto the tiles wash out on the glowing
  accent tiles. PROPOSED: draw a dark disc (panel fill at 0.85) with a
  thin light ring behind each emoji pin, then the glyph — the same
  pattern as the gold "?" ring. Keeps the emoji, makes them readable
  on fog and on cleared ground.
- **My Places: approved, with one PROPOSED change.** The rows
  (place, on-arrive, radius, note, arrivals) and the Noticing copy
  ("asks before doing anything", "never leaves it") are right.
  PROPOSED: the arrival prompt should be a real MIA dialog card —
  place name, what arriving does, Accept / Decline — not a browser
  `confirm()`. `confirm()` blocks, can't be styled, and doesn't look
  like MIA. Note: `.place-arrival` has no CSS yet, so the card and
  its style land together.
- **Sound: approved as built.** The four tunes sit in C major /
  consonant fifths — a coherent identity. Keep them.
- PROPOSED: a Play button per tune in Settings → Sound (a sound
  check), so the tunes can be heard without earning a win first.
