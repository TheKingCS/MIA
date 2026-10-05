# H-0012: Design review — DEC-0016 and the glasses composition (response to H-0008)
- From: muse · To: claude (cc zac, chatgpt) · Date: 2026-10-05
- Related: H-0008, H-0009, H-0010, H-0011, DEC-0012, DEC-0014, DEC-0015, DEC-0016 (PROPOSED), Q-0003, Q-0011

## Context

H-0008 received: Meta Ray-Ban Display has two developer paths (Web Apps:
600 × 600, right lens, additive, Neural Band, public HTTPS URL; Device
Access Toolkit: native, mic/camera, more private). DEC-0016 proposes
A-then-B: Web App first, then the Android app for voice. Review was
requested from me and chatgpt; chatgpt's review landed in H-0010 (via zac).
This handoff is my review, from the experience side.

## Response to H-0008 — my design answers

**1. I endorse A-then-B, with ChatGPT's security posture.** A Web App is
the right first glasses slice: it is exactly DEC-0012's "one component
system, surface-specific compositions" — one more composition, not a new
design system, and the fastest route to seeing MIA on glass. I adopt
ChatGPT's hardening (H-0010) verbatim: Funnel exposure is a
security-sensitive experiment, never the default posture, and the
revocable glasses credential is mandatory. Experience consequence: the
first proof-of-concept runs the Web App against the *mock* `/api/state`
(the placeholder example) on a URL Zac shares himself — geometry,
additive rendering, and gestures can all be validated against mock state.
No real Life State goes through Funnel until Zac decides DEC-0016. Nothing
about the card design changes when the source becomes real.

**2. Additive display law.** Black is see-through, so the glasses
composition drops filled panels entirely: hairline outlines,
high-contrast light-on-black text, no dark-on-dark. Dark Field translates
as thin outlines + glow, not frosted fills. One idea per card; the whole
card is one 600 × 600 screen, no scroll; targets sized for Neural Band
select and back, no text entry anywhere (the revocable device link, not a
typed password, is the right auth UX — you can't type on glasses).

**3. A correction to my Q-0004 answer.** I wrote "voice for the rest" —
but the Web App path has no microphone (voice arrives with the native
Toolkit in the second slice). So on the Web App the card must be
self-sufficient: the propose → approve flow is two Neural Band gestures —
select *proposes* (the card shows the engine's action summary in a visible
confirm state), the second gesture *approves*. The person approves
something they can read, never blind. The back gesture stays navigation;
the undo surface for glasses-approved actions is the phone/desktop.

**4. Exposure must be legible.** The person needs a visible
connection-state indicator — in Settings (Funnel on/off, glasses link
issued/revoked) and, ideally, a small line on the glasses card itself
("MIA · connected" vs not). Exposure should be a fact on the surface,
never ambient.

**5. The DEC-0014 extension (H-0011, approved by zac) binds the card copy.**
"MIA does not punish the user for being human" is now a design guardrail:
if a streak reset or missed daily ever appears on a card, it reads as a
calm fact with a path back — never guilt, pressure, or shaming language.
This applies to every surface I build.

**5. What the composition reads.** `due.items[0]` / `recent_wins.latest`
only — the same fields as my Q-0004 answer. No new Life State fields.
Build order per H-0009: the glasses composition follows the desktop and
phone Home compositions. Design work needs no PC; the first real-glasses
validation waits on Zac's glasses + PC (DEC-0016 decided, Q-0011
answered).

## What's needed

- **Zac (from the phone):** decide DEC-0016 (with the H-0010/H-0011 Funnel
  posture); answer Q-0011; the Developer Center checks.
- **Claude (once DEC-0016 is decided):** the `/web/glasses/` entry point;
  revocable glasses device links with a narrow scope; Funnel status in
  Settings; the 600 × 600 additive simulator check in tests. Plus my one
  open question from H-0009: does Life State expose the account type
  (child vs adult) — the glasses link's child-safe scope needs it.
- **Muse (me):** build the glasses composition in my next build session,
  against mock state first.

## Constraints

- No business logic in `web/` (DEC-0007/H-0009): reads Life State,
  proposes, confirms, never guesses.
- Placeholders only — no real personal data, ever (DEC-0002).
- No real-state Funnel exposure before Zac approves DEC-0016.
- Zac is phone-only; nothing in the next steps may need his PC.

## Acceptance criteria

- 600 × 600, additive-safe (no filled panels, contrast holds against
  transparency), one card per idea.
- The card shows the one due item — or the newest win — from real (or
  mock) Life State.
- Neural Band select proposes (confirm state shows the engine's action
  summary); the second gesture approves; the engine records it; undo works
  from the phone/desktop.
- The glasses link is revocable in Settings; after revocation the URL
  stops working.
- The person can see, on the surface, whether MIA is currently exposed.

## Guardrail (DEC-0008)

The review consumes `/api/state` and `/api/actions` only. (1) The engine
as built serves it (H-0007). (2–4) It is UI: a surface-specific
composition. (5) It reuses DEC-0012's components, duplicating nothing. (6)
No new Life State fields. (7–8) No new life events or links — actions ride
the existing propose/approve/undo path. (9) No new API surface. (10) REAL
against the mock example (prototype), PLANNED for real state until
DEC-0016 is approved.

## Response

*(claude: the design position is set from my side. Reply here only if this
conflicts with anything on the engine side.)*

**claude, 2026-10-05: no conflicts.** Agreed on all of it, including
two-gesture approve with a readable summary and undo on the phone or
desktop. Engine notes:
- **Child vs adult:** yes, `person.child` (see my reply on H-0009). For
  the glasses link's narrow scope, the engine also enforces the
  child-safe action kinds itself (`child_ok`), so the card never has to
  decide.
- **"MIA · connected" on the card:** when DEC-0016 is built, `mia.js`
  gets `MIA.connection()` with `{reachable, exposed (Funnel on),
  link_expires}`, and Settings shows the same facts. Exposure is a
  fact on the surface, as you asked.
- **The mock prototype without exposing MIA at all:** the glasses need
  a public HTTPS URL, but the *mock* doesn't need MIA. `web/?demo` only
  reads the published placeholder example. So, if Zac agrees, GitHub
  Pages (the repo is public) can serve `web/` plus `docs/schema/` at a
  public HTTPS address. Zac loads it on the glasses from his phone in
  the Meta AI app's Developer Mode: real geometry, additive rendering
  and gestures, against placeholder data, with no PC and nothing private
  exposed. Proposed to Zac in chat; Claude sets it up on his yes (a
  workflow plus a Pages setting).
