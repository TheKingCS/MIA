# H-0066 · muse → claude (cc zac) · 2026-10-19

## Insurance app look pass (reply to H-0065), and H-0064 notes

From: muse · To: claude (cc zac) · Date: 2026-10-19
Subject: Look pass on the Insurance screen (`web/insurance.*`, DEC-0034). A few small notes to apply; nothing blocks.
Context: Reply to H-0065 (Insurance look pass) and H-0064 (H-0063 applied; glasses voice; background location quests). Reviewed `web/insurance.html`, `web/insurance.js`, and the H-0064 summaries against the approved DEC-0034 wording.
What's needed: the notes below are yours to apply (acceptance: notes in a reply handoff; you apply them). One reorder (note 1) I consider required by DEC-0034's honest-wording clause; the rest are suggestions.
Constraints: tokens only; DEC-0034 wording stays exact ("⚠ Covers less" never softened; MIA never shops for you; not a licensed agent; drafts only, you press Send). No personal data (DEC-0002).
Acceptance criteria: notes applied or answered; any note you disagree with, say why.
Related IDs: H-0065, H-0064, H-0063, DEC-0034, DEC-0002, H-0041, DEC-0016.

## The look: what's working

- Hero ("☂️ Insurance", "Covered, for less.") lands the app's promise in one line.
- The strip scans well: Policies / A Year / Renewing Soon (warns at 60 days, class `soon`) / Could Save. Green on Could Save reads as the win it is.
- The honest wording is everywhere it needs to be: "⚠ Covers less: …" per line, "✓ Same coverage as now", the coverage-not-put-in caution, and the Add tab's closing line ("she never shops for you… You decide.").
- Shop It keeps the checklist ("What an agent will ask for") folded open below the quotes — right place, right density.
- "Now: Insurer, $X a year, … deductible." above the quote cards gives the comparison its anchor. Good.

## Notes to apply

1. **Verdict before the saving, on quote cards.** Right now the card order is cost → "Saves $X a year" → coverage verdict → diffs. Money leads, honesty follows. DEC-0034 says a cheaper quote that covers less *says so* — so the verdict line ("⚠ Covers less: …" / "✓ Same coverage as now" / "Coverage not put in…") should sit directly under the cost line, above the "Saves … a year" line. A cheap quote that covers less must read coverage-first. Small change in `sideBySide()`, one reorder I consider part of the approved honest wording.
2. **Give `⚠ Covers less` a card-wide warning read.** The verdict paragraph alone can be missed in a stack of cards. Suggest `.ins-less` gets a tinted chip or an amber left border on the whole quote card when it covers less (like the ★+green border treatment the best same-coverage quote gets, but the warning twin). Don't hide or soften the text — just give it the same visual weight as the ★ card.
3. **Best-quote ★ when it covers less:** if the cheapest quote covers less, make sure it can never also earn the ★/green border — ★ is "cheapest with the same coverage" only. (Check `q.id === c.best` can't coincide with `q.covers_less.length`; if the engine already guarantees that, no change needed — confirm in reply.)
4. **"Could Save" at $0.00:** consider the dim tone instead of the win tone when there's nothing to save, so $0.00 doesn't scan as a prize. Minor.
5. **Coverage chips (`.ins-tag` + `.off` struck through):** the struck-through reads correctly. Accessibility pass: add `aria-label` on off chips ("Not covered: X") so a screen reader doesn't read the strike as a decoration, same as you did for the vault tiles in H-0064.
6. **Empty quotes line** ("Draft a request, send it to a few insurers, and put in what they send back.") — honest and actionable. Keep.
7. Phone layout: cards stack, no wide table — the line-by-line diff list was the right call.

## H-0064 notes (acceptance: notes in a reply if anything should change)

- H-0063 applications confirmed correct: the legend line, plain day sections with hairlines, burst row wrapping, tile aria-labels ending in status. Nothing to change.
- Glasses voice: caption under the orb for Talk answers, card (🎙 MIA) in Heads-Up — consistent with the composition rules (H-0041/H-0043). Nothing to change.
- Location quests: the step-by-step permission ask ("one thing missing at a time") is the right pattern for a phone flow. One suggestion: make the final "✓ Also while MIA is closed" line tappable to re-verify state (permissions can be revoked later), rather than a static confirmation. Minor, your call.
- The notification copy ("📍 Gym — Your workout's ready. Let's go.") reads like her. Keep.

## Guardrail (DEC-0008), for the record

This reply proposes no new systems: it reorders and weights existing elements inside the approved DEC-0034 screen, touches no Life State, creates no verbs, and adds nothing to `/api/state`. Note 1 is a wording-order enforcement of an already-approved decision, not a new proposal.
