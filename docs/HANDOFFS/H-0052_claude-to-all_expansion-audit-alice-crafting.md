# H-0052: Expansion audit done; ALICE picks and crafting built
- From: Claude · To: ChatGPT, Muse (cc Zac) · Date: 2026-10-17
- Related: DEC-0028, DEC-0029 (approved), DEC-0030 (proposed), `docs/EXPANSION_AUDIT.md`,
  `docs/future/PROJECT_ALICE_REVIEW.md`, `docs/design/MIA_VOICE.md`, H-0051

## Context

ChatGPT's "MIA Expansion Audit" (real-life RPG, homestead businesses,
memory vault, contextual AI) came through Zac. Claude checked it
against the code before building: `docs/EXPANSION_AUDIT.md` lists every
capability as Built / Partial / Designed / Missing / Blocked, maps it to
the code, and proposes phases A–F (DEC-0030, waiting for Zac). Zac
approved Claude's Project ALICE picks (DEC-0029).

**Glasses finding (for everyone's plans):** the Meta Ray-Ban Display's
web apps (how MIA's glasses view runs) have **no camera and no
microphone**. The camera (photo capture) comes only through Meta's
Device Access Toolkit in a phone app, still a developer preview with
public publishing closed. So "what am I looking at" is an explicit
capture, never a continuous camera.

## Built today (all on existing stores, every change an undoable action)

1. **What I Used** (ALICE 1): memories picked by relevance and listed
   under each Talk answer, with Fix and Forget.
2. **Crafting recipes, end to end** (phase B, the handoff's suggested
   first demo): Workshop → Recipes (materials one per line, cut list,
   tools, steps, price; what's short; the shopping list; Bought It
   receives purchases into Materials) and Builds (steps, before /
   progress / after photos, Finish, Sold It, Add Cost, the build's real
   profit and per hour).
3. **MIA Remembers** (ALICE 3): birthdays, tomorrow's plans and due
   upkeep bring back what you told MIA. Home card plus desktop gate notes.
4. **One conversation everywhere** (ALICE 2): the phone, the web and the
   glasses continue the desktop's conversation. Talk opens on the thread
   and has New Chat.
5. **MIA's voice guide** (ALICE 7): `docs/design/MIA_VOICE.md` plus a
   never-guilt check in code (`core/personality.py`).

## What's needed

- **Muse:** a look pass on the new pieces: Workshop Recipes / Builds
  cards (`.craft-*` in `web/concept.css`), the MIA Remembers card on
  Home (`.home-remember`), the What I Used list under Talk replies
  (`.talk-used`), and the buff chips. Please also read the voice guide
  and change it where you disagree.
- **ChatGPT:** a vision check of DEC-0030's phase order (business loop
  next, or the grow lab, or the memory vault once the phone↔PC link
  exists).

## Constraints

DEC-0014 (never punishing), DEC-0002 (no real personal data in the
repo), offline first, and every change proposed and approved.

## Acceptance criteria

Muse's notes or changes on the four pieces; ChatGPT's view on the phase
order. Zac decides DEC-0030.
