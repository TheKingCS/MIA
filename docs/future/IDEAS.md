# MIA: future features (the ideas list)

*Started 2026-10-18 at Zac's request: "a document for potential future
features… automating things that will make my life easier and save me
money." Add to it any time: tell Claude, or edit it on GitHub. Nothing
here is approved or scheduled until Zac picks it (DECISIONS.md); when
one is picked, it gets a DEC number and moves to the build queue in
`docs/NEXT_SESSION.md`.*

**How each idea is written:** what it does for you, what MIA already has
that it builds on, what it needs from outside, and its status
(💡 idea · 🔍 being planned · 🛠 being built · ✅ built).

---

## Money

### 1. Insurance check-up: compare and save ✅

*Built 2026-10-19 (DEC-0034): Apps → Insurance.*

*Zac, 2026-10-18.* MIA keeps track of your insurance (car, home or
renters, health, life, umbrella) and helps you find a better plan.

**What it would do**
- **Policy vault:** each policy as a record: insurer, what's covered,
  limits, deductibles, the premium and how often it's paid, and the
  renewal date. Filled from the policy PDF or the declarations page
  (the Inbox and OCR already read documents) for you to check.
- **Renewal heads-up:** about 45 days before a renewal, a note through
  the communication gate: "Your car insurance renews in 6 weeks; last
  year it went up 12%. Want to shop it?"
- **What you're paying for:** the total per year, the change since last
  year, and things worth a look: coverage that may not fit any more
  (full coverage on an old car), a deductible you could raise because
  your emergency fund can cover it, or a missing bundle discount.
- **Shopping it:** a checklist of what an agent needs, and quote-request
  emails MIA **drafts** for you to send (MIA never sends; you press Send).
  It never fills in an insurer's website for you.
- **Side by side:** type in or forward the quotes you get back, and MIA
  lines them up against your current policy, same limits against same
  limits, so a cheaper quote that covers less is called out, not hidden.
- **Switching:** once you pick, the steps (start the new one before
  cancelling the old one, no gap), a mission for it, and the savings
  logged so the Chronicle and your money boss count them.

**Builds on:** the Inbox and OCR (reading policies), email drafts, the
communication gate, the Budget (premiums as bills), missions, the
Chronicle.
**Needs from outside:** your quotes. There's no honest, free,
offline-friendly way to pull live prices from every insurer, so MIA
compares what you get rather than shopping for you.
**Guardrails:** never money to a child account; the policies stay on
your devices; MIA explains the trade-offs and you decide; never advice
presented as a licensed agent's.

---

## Add the next idea here

Copy this shape:

### N. Name 💡

*Who, date.* One or two sentences: what it does for you.

**What it would do:** the main pieces.
**Builds on:** what MIA already has.
**Needs from outside:** accounts, devices, data.
**Guardrails:** privacy, children, never acting without you.
