# MIA development plan (from 2026-11-07)

*Claude, at Zac's ask ("help plan further development"), from what was checked today: the parity report
(`docs/PARITY.md`, DEC-0125), Claude Design's 66 screens (`docs/design/CORE_SCREENS_REVIEW.md`), the audit of
everything built (https://claude.ai/artifact/56xyaTxEQThT1vrYh484Ay) and the open decisions. Zac decides the
order; this is Claude's recommendation. ⏸ marks a step waiting on someone.*

## The rule every step serves

Full use both ways, on every device (DEC-0125): every feature by voice and without it, on the PC, the phone and
the glasses; a device changes how it's shown, never what it can do. Today: voice 48 of 50 apps, PC 50, phone 46,
glasses 29. 27 gaps, each decided in `work/parity.json`.

## Stage 1: finish what's half there (Claude, about a session)

1. **Humor on the Settings screen** (it's voice-only now): a five-step choice, the same setting set_humor moves.
2. **Phone pages for Power, Toolbox, The Lab and Field Kit.** Claude Design already drew them; closes the four
   phone gaps. Running scripts and scans stays on the PC; the phone shows and logs.
3. **"Say: …" on every screen**: one quiet line per screen from its app's own ask, so each screen teaches its
   voice twin.
4. **Send the design review back to Claude Design**: the six screens that show what MIA can't do (Pay From
   Savings, the coop plan in Budgets, Settings' toggles, Party and the household lines, square miles on the World
   Map, Inbox without email).

## Stage 2: the glasses (Claude Design, then Claude)

5. ⏸ **Claude Design draws the glasses card and ask for each app** (19 apps have none; 600×600, black is
   see-through). Two exist (Home, Active Training).
6. **Claude builds them** into core/glasses.py PANELS and ASKS, each closing a line in work/parity.json.
   Passwords stay off the glasses (Zac, 2026-11-07).

## Stage 3: organization (waits on Zac's yes to the audit)

7. ⏸ **The seven areas in the sidebar, and Today with a Waiting For You queue** (the audit's step 1): what needs
   you from every app in one place (approvals, receipts filed, findings, a browser step waiting).
8. ⏸ **The eight merges** the audit proposes, one at a time, each keeping every capability (the parity test
   holds that).

## Stage 4: new capability, chosen by use

9. **Kitchen Cook Mode**: a recipe one step at a time, kitchen timers, "next step" and "how long on the chili?"
   by voice; big targets for messy hands. Designed; recipes need steps split from their instructions.
10. **Look by voice**: "what am I looking at" takes the photo itself (the phone's camera now, the glasses' later).
11. ⏸ **Taught procedures** (DEC-0123, proposed): one way to teach MIA any routine, browser routines folded in.
12. ⏸ **A planned purchase** ("plan the coop for the 15th, $340"), only if Zac wants it: Talk's design assumes it.

## Zac's hands-on steps (they unlock the most)

- **Link every card and bank with Plaid** (his first priority at the PC, 2026-10-21): Money, Freedom and the
  findings on Home all get better with real balances.
- **Email for receipts** (DEC-0120): the app password, then MIA files receipts on her own with an Undo.
- **Try talking to MIA on the PC** (Talk's mic, today) and say what went wrong.
- **Decide**: the audit's areas and merges, DEC-0113 (per-app colors), DEC-0123 (procedures).

## How each step is done

Every change keeps parity from going backwards (`tests/test_parity.py`), is documented as it's built
(DEC-0104/0110), is undoable when it changes something (`core/undo_log.py`), and leaves a line in
`docs/CURRENT_STATE.md` and a knowledge entry for MIA (DEC-0105).
