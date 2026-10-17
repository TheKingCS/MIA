# Project ALICE: what fits MIA

*Claude, 2026-10-17, for Zac ("look over this site, research it a little,
and see what features would fit the assistant"). Nothing here is
approved: the picks are in `docs/QUESTIONS.md` (Q-0017) for Zac.*

## What ALICE is

ALICE ("Shared Life with AI", project-alice.us) is an AI companion with
**one personality and one memory** that goes with you from your desk
out into the street through AR glasses. As of its September 2026 site:

- **Desktop** (macOS, Windows) is in alpha. You talk to her aloud and
  can **check what she recalled before she answers**.
- **AR** is a prototype, shown on the Ray-Ban Meta Display (the site
  also says Android XR).
- **Memory** keeps context across sessions, and she **brings things up
  herself** when they matter.
- **Voice and vision**: hands-free through the glasses, and she can
  see a **shared screen or what the glasses see**.
- **Bring your own model**: her memory works with any model, local ones
  included; conversations stay with your own installation.
- Early access is by waitlist.

(The site itself blocks this cloud container, so this comes from its
indexed text. Two other "Project Alice" projects exist and aren't this
one: the open-source offline voice assistant at projectalice.io, and an
agent framework.)

## How it compares

ALICE and MIA aim at the same picture: one assistant, private, across
the computer, the phone and the glasses. They come from opposite ends:

| | ALICE | MIA |
|---|---|---|
| Center | the companion: personality, memory, conversation | the life engine: stores, actions, missions, the game layer |
| Memory | the main feature, shown to you | a list of memories, put into every turn (up to a limit), not shown |
| Glasses | voice and camera, a prototype | readable panels and actions on the Meta Display (built) |
| Models | any model, local or not | small local model; facts assembled in code |
| Privacy | your installation | offline first, each person's data their own |

MIA already has what ALICE is still building (real data, actions you
approve, the glasses' screens). What ALICE does better is make **the
assistant herself** feel like one continuous someone who remembers you.
That's the part worth taking.

## Recommendations, best fit first

1. **Show what MIA remembered ("What I Used").** Under each answer, a
   small line: the memories and facts MIA used, each one tappable to
   fix or forget. Today `core/assistant_chat.py` puts the first memories
   into every turn whether they matter or not and the person never sees
   which. Two parts: pick memories by relevance to what was asked
   (words in common, the people and things it names, recency), and
   return them with the reply. Fits DEC-0014's honesty and the existing
   "why this?" work (`core/why_graph.py`). *Effort: 1 session.*
2. **One MIA everywhere: pick up where you left off.** One running
   conversation per person across desktop, phone and glasses, so
   "what were we talking about?" works anywhere and the glasses' Talk
   continues the phone's thread. The engine is already one; this is the
   conversation store and the glasses' Talk. *1 session.*
3. **Remembering on her own, at the right moment.** ALICE brings things
   up when they matter. MIA's version, through the communication gate
   (never more than the daily limit): "Jordan's birthday is in 9 days;
   you noted she wanted a chalk bag." "Last time you serviced the mower
   you said the blade was dull." Built from People, notes and memories,
   tied to what's due. *1 session.*
4. **Use the computer's bigger model from the phone.** ALICE's "bring
   your own model": when the phone is on the home network, MIA can send
   a turn to the model on the new computer (bigger, smarter) and fall
   back to the phone's own model away from home. Data stays in the
   house. **Already approved and next in the queue** as "supercharged
   online" (DEC-0022, `docs/NEXT_SESSION.md`): ALICE confirms the
   direction. *1–2 sessions.*
5. **"What am I looking at?" (vision).** Glasses or phone camera →
   MIA: read a label or receipt (OCR exists: `core/ocr.py`), match a
   machine to its asset page, see a part's number. Later: the Meta
   Display's camera access for apps is limited today, so start with
   the phone camera. *Later.*
6. **Hands-free voice on the glasses.** Talk to MIA through the
   glasses without the phone in hand. Depends on what Meta's glasses
   let an app do; the phone's voice (`docs/PHONE_VOICE_SETUP.md`) is
   the first step. *Later.*
7. **A consistent personality.** One short description of who MIA is
   (warm, plain-spoken, encouraging, never guilt), used by every
   surface that writes words: replies, notes through the gate, the
   Chronicle. Mostly a writing guide with Muse; small code change.
   *Half a session.*

Not recommended: a cloud MIA or sending conversations to an outside
model by default (against offline-first and DEC-0002), and a
"companion" that chats for its own sake (MIA's notes stay rate-limited
and useful).

**Claude's suggested order:** 4 is already next (DEC-0022); then
1 → 3 → 2, with 7 alongside; 5 and 6 when the glasses allow it.
