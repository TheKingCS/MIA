# H-0076: Step 3 is mine with Zac — information architecture and design standards

- From: muse
- To: claude (cc chat, zac)
- Date: 2026-10-27
- In reply to: H-0075 (The Body and the Relationship: audit and plan)

## What I'm accepting

Step 3 of the plan (`docs/BODY_AND_RELATIONSHIP_PLAN.md` section 3):
the information architecture and the written design standards, built on
`web/tokens.css`, done with Zac. Two dependencies I am stating plainly
so nobody builds ahead of them:

1. Step 3 starts after step 2 lands (`docs/UI_AUDIT.md` plus Chat's
   ten-question scorecard per page). I can't write an architecture
   over 51 pages I haven't inventoried, and the scorecard is Chat's
   input, not mine to invent.
2. Every IA call is Zac's (DEC-0048, DEC-0045). What follows is my
   working position and my evaluation criteria — proposals, not
   decisions. Nothing here changes an approved decision, and no page
   moves until Zac approves the architecture.

## Guardrail (DEC-0008)

The design system already exists (`web/tokens.css`, `web/shell.js`,
line icons, DEC-0023) — step 3 extends it into written standards, it
doesn't start over and doesn't duplicate it. This is UI only: no new
Life State fields, no new life events, no new links, nothing new for
`/api/state` to expose. The About Me page (step 1) reads existing
stores; the IA itself is PLANNED until step 2 and Zac's approval.

## Design standards: what "written" means

`tokens.css` today is values without prose. The standards doc will pin,
for each pattern, the rule plus the exception that proves it:

- Type scale, spacing, density; cards, tabs, strips, dialogs.
- Status colors (including the H-0074 precedent: a boss + hard run
  shows both the amber edge and the accent glow — both signals, not
  one replacing the other).
- Motion (celebration may be loud per DEC-0014; everything else
  quiet), AR/glasses rules (answer-first, one idea per card), contrast.
- The rule from every look pass so far: a new page follows the
  existing pattern unless it has a stated reason not to — the
  variation we already have (tab counts, strip cells, section
  patterns differing page to page) is exactly what step 2 must measure
  before step 3 writes the rule.

## Information architecture: how I'll evaluate the candidates

The plan's candidates (Missions + Skills + Character + Reward Shop +
Chronicle as one "You" area; Money + Freedom + the Dungeon +
Compliance + Insurance as one money area; Garage + Workshop +
projects; Kitchen + Workout + My plan) are evaluations, not decisions.
My criteria, in order:

1. **Shared state.** Grouping earns its keep when the grouped apps
   read the same state (progression, pay, a plan). Grouping apps that
   merely rhyme hides distinct jobs.
2. **One job per area.** A grouped area must still answer "what do I
   do here?" in one sentence. If it takes two, it's two areas.
3. **Reach, not removal.** Per DEC-0045 the apps stay the layout —
   the sidebar and the phone's Home and Apps bar stay, and every app
   stays reachable. Consolidating is grouping inside that layout;
   nothing disappears into a sub-page you can only reach from inside
   another page (we already have 17 of those — the audit counts them
   as a problem, not a pattern).
4. **Fix-It Log evidence.** Where the log shows people stumbling on a
   page, that page's grouping gets questioned first (phase 4).

My early lean, for Zac to test against the inventory: the "You" and
money groupings look strongest on criterion 1 (one progression state;
one pay state — and the duplicate-pay fix in the plan, Freedom reading
pay from the Dungeon, is a precondition for the money grouping making
sense at all). Kitchen + Workout + My plan is the weakest candidate on
criterion 2 until My plan's job is stated separately from each app's.

## About Me (step 1): design input

One page, grouped by area, each fact carrying where it came from and
Fix / Forget — the user model's face before its store. Two rules:

- A value another store owns is shown as a pointer, never copied
  (the same rule the user model itself follows). About Me must never
  become a third source of truth.
- Read-only first, with Fix / Forget on every row: it answers Chat's
  "inspect, correct, delete" on day one and shows the audit exactly
  what's scattered.

## User Sync screens (step 5 dependency)

Agreed: Sync's screens are designed inside the IA, not after it. The
chapter shape (optional, resumable, confirm at the end of each
chapter) already matches propose → approve → execute → record → undo,
so the screen work is layout and wording, not a new contract. Voice,
typing, or both, and one sitting vs chapters, are section 9 questions
for Zac — see below, not decisions here.

## Section 9 questions: my input, Zac's call

These are Zac's questions and I am not answering them for him. What I
can offer, as the experience side:

- **Q1 (routing change):** supported from the experience side. The
  "never 'I don't know what to do'" rule — one short clarifying
  question, or the two closest things she can do — is the right shape,
  and facts about the person's own data still come only from their
  data, never invented. Verified on the PC's model before it ships, as
  the plan says.
- **Q3 (User Sync):** lean both voice and typing, chapters over a
  few days, and yes, run it for the existing user too — the gaps it
  fills are exactly what About Me will surface. Defaults in the plan
  are sound; Zac confirms.
- **Q4 (quiet hours):** lean a Loop-derived default over a fixed
  clock default — the Loop already learns the person's real rhythm,
  including night shifts, so a fixed window would be wrong for the
  very person it serves. Off until set is the safe fallback if the
  Loop has nothing learned yet.
- **Q2 (EULA):** not mine. Needs Zac's facts and, as the plan says, a
  lawyer before anyone outside the household relies on it.

## Noted, no contradiction

- DEC-0047 (missions/Loop/Sunday check-in), DEC-0048 (User Sync +
  design audit), DEC-0049 (Fix-It Log) are approved and stand. The
  Fix-It Log's evidence feeds phase 4 scorecards; the Loop's
  learned/yours rule is the pattern the user model extends.
- H-0074's tweaks are applied per CURRENT_STATE; the Dungeon keeps
  its accepted look. Nothing in step 3 reopens it.

## Next from me

When step 2 lands (inventory + scorecard), I'll file the IA proposal
as PROPOSED in DECISIONS format for Zac's approval, with the
standards draft alongside it. Until then, no page moves and no
redesign builds from this handoff.
