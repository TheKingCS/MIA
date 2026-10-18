# H-0062 · claude → muse (cc zac) · 2026-10-18

## The Memory Vault: ready for a look

From: claude · To: muse (cc zac) · Date: 2026-10-18
Subject: A new screen, `web/vault.html` / `vault.js` (DEC-0030 phase E), built on the frame, function first.
Context: Zac asked for the memory vault and for sync to carry photos, files, conversations and the private journal. Both are built and tested with two MIAs (`docs/MEMORY_VAULT.md`).
What's needed: a look pass on the vault screen when you get to it. Nothing blocks on it.
Constraints: freeing space is only ever an offer, confirmed by the PC and then by Android's own dialog; please keep that wording honest ("Android asks you next", "Trash for 30 days"). Tokens only, as always.
Acceptance criteria: your notes in a reply handoff; I apply them.
Related IDs: DEC-0030, DEC-0022, H-0061.

## What's on the screen

- **Strip:** Photos, Videos, Safe On PC, Waiting (`soon` while any wait).
  Under it, one line of state: copying, waiting for Wi-Fi, waiting for
  the home computer, or "Everything is safe on the home computer."
- **Photos:** a month picker, then each day as a section: its date, the
  expedition it was on (tag), "That day: ..." (the history), and a
  grid of tiles. Tile marks: `✓ PC` (safe), `⏳` (not yet), `★` (best of a
  burst), `×2` (on the phone twice), `PC only` (freed from the phone).
  Tap: a viewer with the full photo or the video.
- **Free Up Space:** the offer (how many, how much, older than N days),
  Exact Copies, Bursts (the best shot's preview, "Keep The Best, Free N"),
  and what was freed lately.
- **Set Up:** on, Wi-Fi only, how many days to keep on the phone, Copy Now,
  and how it works in two sentences.
- **The Chronicle** now shows "📷 N photos" with the week's cover photo
  under each chapter (`.chron-photos`).

New CSS is at the end of `concept.css` (`.vault-*`, `.chron-photos`).
Things I'd like your eye on: the marks on the tiles (legible but
quiet?), the burst row, and whether the day sections should be less
boxed for a photo grid.

Demo data: `docs/schema/vault.example.json` (placeholder photos don't
load in the demo; the tiles show blank).
