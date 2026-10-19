# H-0065 · claude → muse (cc zac) · 2026-10-19

## The Insurance app: ready for a look

From: claude · To: muse (cc zac) · Date: 2026-10-19
Subject: A new screen, `web/insurance.html` / `insurance.js` (DEC-0034), built on the frame, function first.
Context: Zac picked the insurance check-up from the ideas list.
What's needed: a look pass when you get to it. Nothing blocks on it.
Constraints: keep the honest wording: "⚠ Covers less" is never hidden or softened, MIA "never shops for you", isn't a licensed agent, and only drafts (you press Send). Tokens only.
Acceptance criteria: your notes in a reply handoff; I apply them.
Related IDs: DEC-0034.

## What's on the screen

- **Strip:** Policies, A Year, Renewing Soon (`soon` when any renew within 60 days), Could Save (each policy's best same-coverage saving, added up).
- **My Policies:** one card per policy: icon and name, insurer and what it covers, the cost a year (mono, accent), the terms line, coverage chips (`.ins-tag`; one they don't have is struck through), the checks (amber for time or price, plain for questions), and "Switching to X · I Switched" while a switch is under way.
- **Shop It:** per policy: Draft A Quote Request / Add A Quote, the checks, then one card per quote (`.ins-quote`): cost a year, what it saves or costs more, "✓ Same coverage as now" or "⚠ Covers less: …", then each line that differs ("Bodily injury: 50,000/100,000 (you have 100,000/300,000)"). The ★ and green border mark the cheapest same-coverage quote. "What an agent will ask for" folds open.
- **Add:** Read A Policy (a PDF or photo fills the form), Type One In.

Things I'd like your eye on: the quote cards (does "Covers less" read loud enough without alarm?), the coverage chips, and the strip's money cells.

Demo data: `docs/schema/insurance.example.json` (placeholder insurers).
