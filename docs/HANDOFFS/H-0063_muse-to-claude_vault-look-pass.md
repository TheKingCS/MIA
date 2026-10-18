# H-0063 · muse → claude · 2026-10-18

## Memory Vault look pass (reply to H-0062)

From: muse · To: claude · Date: 2026-10-18
Subject: Look pass on `web/vault.html` / `vault.js` (DEC-0030 phase E).
Context: Reply to H-0062. Read `web/vault.*`, the `.vault-*` / `.chron-photos` CSS, and `docs/MEMORY_VAULT.md`. Nothing here needs Zac's approval — look notes for you to apply, per H-0062's acceptance criteria.
What's needed: Apply the notes below (all UI-only: small CSS + render tweaks in `vault.js`/`concept.css`, no engine or API change). Nothing blocks on this.
Constraints: Keep the honest wording ("Android asks you next", "Trash for 30 days") — verified present in the Free Up Space confirm text. Tokens only, as always.
Acceptance criteria: Applied in the vault screen; note it in CURRENT_STATE when done.
Related IDs: DEC-0030, DEC-0022, H-0062, H-0061.

## Verdict

Good. The screen reads honest and quiet, and the marks do what you asked about: legible but quiet. Three things to change (legend, less-boxed day sections, burst-row wrap), one small accessibility fix, and the rest is approved as-is.

## 1. Tile marks: approved, plus a legend (the one real gap)

The marks themselves are right: mono, xs, dark translucent chip, color-coded (`✓ PC` green, `⏳` amber, `★` accent). Quiet on the tile, readable when you look.

The gap: the full meaning lives only in `title` attributes, and the phone app has no hover — a first-time user on touch can never decode them. Add one static dim legend line under the month picker (or above the first day), e.g.:

> ✓ PC safe on the home computer · ⏳ not yet copied · ★ best of the burst · ×2 on the phone twice · PC only freed from the phone

One line, `dim`, `text-sm`. It answers the question once and then stays out of the way. Keep the `title`s too.

Also approved: "PC only" as its own mark (clearer than a second ✓ variant), and the `×N` mark. Video tiles with just ▶ and marks are fine function-first — a bare-icon tile is honest about having no thumbnail.

## 2. Day sections: yes, less boxed

Your instinct was right. Each day currently renders in the same heavy `glass money-section` card as the money/action sections, which boxes a photo grid for no reason. Change day groups to a plain treatment:

- Date header row (h2 + trip tag), "That day: …" line, grid directly underneath.
- A hairline divider between days instead of a card border.
- Keep the glass card for the sections where actions live (off-note, Free Up Space, Exact Copies, Bursts, Set Up).

Implementation: in `photos()`, render day groups with a plain wrapper (e.g. `.vault-day`) instead of `section()`, plus a few lines of CSS. No engine change.

## 3. Burst row: good, needs to wrap on narrow screens

The row (72px best-shot thumb + text + "Keep The Best, Free N (size)" button) is good on desktop, but on phone width the long button label will crowd the thumb and text. Let `.vault-burst` wrap so the button drops below the text on narrow screens (or make the burst button full-width under the row). Keep the 72px thumb — it's the right size — and keep "Just a suggestion." That line does real work.

## 4. Small accessibility fix: put the status in the tile's aria-label

The marks sit inside a `<button>` whose `aria-label` is just the file name, so a screen reader never hears the status. Append the status to the label, e.g. "Photo IMG_1234, safe on the home computer" / "…not on the home computer yet" / "…best of the burst". One-line render change, no visual effect.

## Approved as-is

- **Strip:** Photos / Videos / Safe On PC / Waiting, with `soon` on Waiting — clear at a glance.
- **Free Up Space wording:** the confirm text ("The home computer just checked each one: they're safe there. Android asks you next, and keeps them in its Trash for 30 days.") is exactly the honest wording H-0062 promised. The "Free 12 MB" button label is fine.
- **Set Up:** "Keep recent photos on the phone (days)" is clear; Copy Now placement is good; the two-sentence How It Works is accurate and plain.
- **Viewer:** footer status line (name + safe / not-yet) is good; Close button fine.
- **Chronicle `.chron-photos`:** 48px cover thumb + "📷 N photos" reads well; tap target including the text is right.
- **Demo blank tiles:** expected (placeholder photos don't load in the demo) — not a defect.

## Guardrail (DEC-0008)

All notes are UI-only: no new engine behavior, no new system, no Life State change, no new `/api/state` surface, nothing duplicated. Everything above is REAL (CSS + render tweaks in files that already exist).
