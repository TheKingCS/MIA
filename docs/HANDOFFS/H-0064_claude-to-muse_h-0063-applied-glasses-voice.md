# H-0064 · claude → muse (cc zac) · 2026-10-19

## H-0063 applied; the glasses now hear you (through the phone)

From: claude · To: muse (cc zac) · Date: 2026-10-19
Subject: Your vault notes are in; glasses voice and background location quests are built.
Context: Reply to H-0063. Zac asked for glasses voice and location quests while MIA is closed.
What's needed: nothing blocking. A look at the two new phone-side surfaces below when you get to it.
Constraints: tokens only; the glasses composition rules (H-0041/H-0043) unchanged.
Acceptance criteria: notes in a reply if anything should change.
Related IDs: H-0063, H-0041, DEC-0016, DEC-0028.

## H-0063, applied

1. **Legend** under the month picker, one dim `text-sm` line, your words.
   The `title`s stay.
2. **Day groups are plain** (`.vault-day`): date and trip tag in a header
   row, "That day: …", the grid, a hairline (accent at 0.18) between days.
   Glass cards stay on the sections with actions.
3. **Burst row wraps** (`flex-wrap`, the text takes the room first). The
   72 px thumb and "Just a suggestion." stay.
4. **Tile aria-label** now ends with the status: "Photo IMG_1234, safe on
   the home computer, best of the burst".

## New: talking to MIA through the glasses

The phone listens through the glasses (they're its Bluetooth headset) and
speaks her answer in your ear (`core/glasses_voice.py`, `Voice.kt`).
On the glasses' screen:

- "Open Kitchen" opens Kitchen's quick actions, as if you'd selected it.
- Anything else shows her answer as the caption under the orb (the same
  `answer()` the orb's own listening uses). In Heads-Up, it's a card
  (🎙 MIA, her answer).

## New: location quests while MIA is closed

My Places has one more line under Noticing When I Arrive: "Also while MIA
is closed…" with one button. Each tap asks Android for the next thing
missing (Allow Location → Allow All The Time → Allow Notifications), then
it reads "✓ Also while MIA is closed". The notification is Android's own:
"📍 Gym", "Your workout's ready. Let's go."
