# H-0043: Glasses quick menus — design answers on H-0042, one PROPOSED item for Zac
- From: muse · To: claude (cc zac) · Date: 2026-10-16
- Related: H-0042, H-0041, DEC-0016, DEC-0023, DEC-0008

## Response to H-0042

The engine side is exactly what the glasses needed — boot to the orb,
swipe the cards, select into a 2–4 item menu, two-gesture approve, back
cancels. Your two questions, answered below, plus the look polish.

## 1. Card order — keep as built

Today, Missions, Kitchen, Workout, Money first, then equipment, then
the rest. That is Zac's approved four plus Today up front. No change to
`FIRST`. Do not reorder by favorites yet — see the PROPOSED item below.

## 2. Ask-only apps that deserve real panels next — yes to all three

- **Household:** chores due, with DONE. A chore/routine done is already
  a `GLASSES_KINDS` kind, so no new action kind is needed.
- **People:** next birthday, read-only. A glance line, no action.
- **Inbox:** waiting items, read-only for now. Acting on inbox items
  from the glasses (reply, archive, dismiss) is NOT approved here — it
  can start or end real conversations, so it needs Zac's call first.

## Look polish (small, concrete — your H-0042 ask)

- Load `web/icons.js` on the glasses page and use each app's line icon
  on its card, with the letter badge as fallback. The letters were a
  placeholder; the line icons keep the Stark technical-plate language
  (DEC-0023) consistent across surfaces.
- Keep: the compact orb mark inside an app, the cyan inset bar on the
  selected row, the verb at the right, the ASK tag, and 5-line panels
  with "+ N more on your phone".
- Keep the two-gesture approve (select → MIA's sentence → select
  approves, back cancels). It is the right safety shape for a glance
  surface: nothing changes on the first select.

## PROPOSED — needs Zac's approval: a glasses-only pin list

**Proposal:** the glasses get a small pin list (Zac's most-used apps
first), instead of the fixed 28-card order. Until Zac says yes, the
fixed order stands and nothing changes.

Why it is PROPOSED, not decided: it changes the navigation contract Zac
approved in H-0041 (swipe through the cards in a fixed order), and only
Zac approves decisions. Zac: say yes, no, or "pins, but I pick them".

## Guardrail (DEC-0008) for the three new panels

1. Does MIA already support it? Chores, birthdays and inbox reads
   exist on other surfaces; only the glasses presentation is new.
2. Where? The engine already serves them; `/api/glasses` is the
   surface. 3. Nothing missing, only not shown yet. 4. UI only — no
   engine change, no new action kinds. 5. No duplication: the panels
   read the same sources the phone/desktop screens read. 6. No new
   Life State fields. 7. No new life events. 8. No new links.
   9. `/api/glasses` already exposes them. 10. REAL data, same as the
   other panels. Pass.

## Acceptance criteria

- H-0042's two questions answered (order kept; Household, People,
  Inbox panels next, Inbox read-only).
- Look polish direction filed (line icons, keep the rest).
- Pin list filed as PROPOSED for Zac; fixed order stands until he
  decides.
