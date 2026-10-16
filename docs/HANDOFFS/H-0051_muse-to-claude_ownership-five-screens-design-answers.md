# H-0051: Design answers: ownership apps polish (H-0049) + five new screens, Inbox, Home (H-0050)
- From: muse · To: claude (cc zac) · Date: 2026-10-16
- Related: DEC-0025, DEC-0026, DEC-0027, H-0049 (claude → muse), H-0050, H-0036

## Context
Two handoffs arrived the same day, both "look is yours to polish". This
answers both. Nothing here needs Zac's approval: it polishes already-built,
already-approved screens (DEC-0025/0026/0027) within the settled Stark /
technical-plate language (H-0036). No engine changes, no new fields, no
new endpoints.

Guardrail (DEC-0008): everything below is already supported and built —
this is UI-only polish. Nothing duplicates a system, nothing enters Life
State, no life events, no links, no `/api/state` change. REAL.

## H-0049: Home & Appliances cards, bucket-tab counts, chat bar

- **Home & Appliances cards:** one technical-plate card per appliance,
  same plate treatment, spacing and Title Case as the Garage asset cards
  so the three ownership apps read as one family. Card lines: name
  (Title Case), type tag (e.g. Furnace), location (e.g. Kitchen), next
  upkeep due line. Status dot only: past due red, due today amber, due
  soon neutral, otherwise muted. No photo yet: plain module-color
  placeholder per the DEC-0018 item 5 pattern until Zac uploads one.
  Add Appliance is an outlined plate button, same as Add on the other
  ownership screens.
- **Bucket-tab counts:** keep counts on Past Due / Due Today / Due Soon
  tabs only — "Past Due (3)", count in parentheses, muted except Past
  Due with items, which reads red. No counts on the inventory tabs
  (Assets, Properties, Home & Appliances) — those are inventories, not
  buckets of due work. This does not contradict DEC-0026: its no-counts
  rule was for the Missions tabs specifically.
- **Chat bar fix:** accepted — text box shrinks (min-width: 0), buttons
  keep their size, 44 px tall on phones, chips on one swipeable line.
  Two additions: keep the Send label visible (not icon-only) so it stays
  discoverable, and give the chip row a fade at the right edge so the
  swipeability is visible. Same for Home's talk bar.

## H-0050: five new screens, Inbox, Home

- **Journal:** entries as full-width stacked cards, newest first, in the
  "more like At A Glance" stacked-row language Zac asked for on Skills.
  Tag chips filter; Write Entry is the primary gold-outline button;
  Talk It Out is secondary. Private/encrypted entries stay a count-only
  row, never content — as built.
- **Workshop:** tabs Jobs / Materials / Products / Parts / Money keep the
  standard app tab row. Stock + / − are 44 px touch targets. Sell is
  gold. Money tab: three stat plates — sales, costs, profit — same
  treatment as the Money app's stat plates.
- **Expeditions:** Happening Now / Coming Up / Past as section headers,
  not tabs — trip counts are small and sections scan faster. Packing-list
  checkboxes use the shared `.tick-row` pattern from the Inbox File It
  dialog, so a checked box looks the same everywhere.
- **Music:** song rows with a play affordance, Playlists as plates,
  Artists as a simple list. Playback controls live on the Music page
  itself, not a global bar — Home stays quiet (Witness Principle).
- **Files:** breadcrumb for the folder path, rows with icon + name +
  size, Upload / New Folder as outlined buttons, Open shows pictures,
  PDFs, songs and text in place — as built.
- **Inbox:** accepted as built — Waiting cards with MIA's reading line,
  File It dialog with `.tick-row` checkboxes, Dismiss secondary,
  Filed And Dismissed as a muted card with a Filed tag. One note: the
  File It dialog keeps the total / category / maintenance-step
  checkboxes in the same order every time, so filing becomes muscle
  memory.
- **Home replaces the Dashboard (DEC-0027):** accepted — greeting,
  Today's Focus, Upcoming, level card; no quick buttons, no date; MIA's
  badge opens the chat; bottom bar Home and Apps. The retired Dashboard
  redirects to Home.
- **Hero art:** the shared hero stands. If per-app imagery goes on the
  `mod-*` body classes, keep it technical-plate style (H-0036), not
  photos — photos belong to Zac's own uploads (recipes, assets), not to
  app headers.
- **412 px, no sideways scroll:** accepted as the standing constraint
  for every screen above.

## Acceptance criteria
- Ownership apps read as one family: same plates, same tab-count rules,
  same Add-button treatment.
- No screen scrolls sideways at 412 px; all touch targets 44 px.
- No engine, schema or endpoint changes in this handoff.
