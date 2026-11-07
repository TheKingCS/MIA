# Taught procedures: one way to teach MIA anything (DEC-0123, proposed)

*claude, 2026-11-07, from Zac's review: "Browser routines are now teachable,
but they're not yet the same thing as a universal skill system that can
teach MIA workflows across desktop apps, phone features, and other tools."*

**The proposal in one line:** one kind of thing, a *procedure*, that you
teach MIA once (by doing it, by telling her, or by letting her draft it),
that she practises with you watching until it's proven, and that then runs
when you ask, on a schedule, or when something happens. Its steps can be
anything she can already do (her own tools, her browser, your phone) and,
later, desktop apps. The browser routines and workflows built so far become
two kinds of step inside it, not separate systems.

## What exists today

| Engine | Taught how | Steps | Runs when | Proven how |
|---|---|---|---|---|
| Workflows (`core/workflows.py`, DEC-0092) | MIA writes a spec | read, count, when, tell, add | every day, week or month | dry run, then standing approval by kind |
| Browser routines (`core/browser_routines.py`, DEC-0117) | you do it in her browser | open, click, type, sign in | when you ask | learned after 2 clean runs |
| Learning paths (`core/paths.py`, DEC-0112) | a program, for *you* | lessons, practice | weekly homework | by evidence |

Each solves one slice. None can say "every Sunday, check the county tax
site, log the bill in Money, and remind me Monday if it's over $300."

## The model

A **procedure** has a name, a **trigger**, ordered **steps**, and a
**practice state**.

- **Trigger:** when you ask ("do the tax check"); a schedule (absorbs
  workflows' day/week/month); or an event MIA already publishes (a receipt
  filed, a place arrived at, a bill coming due: `docs/EVENTS.md`).
- **Practice state:** *practising* until its last 2 runs went cleanly with
  you watching (as browser routines do now), then *learned*. Only a learned
  procedure runs on a schedule or an event, unattended.

### Step kinds and their gates

Every step goes through a gate that already exists. Nothing new decides
what's safe.

| Step kind | What it is | Gate (already built) |
|---|---|---|
| `tool` | any of her Assistant tools (add an expense, log a reading, add groceries...) | the tool's own rules; changes undoable (`core/undo_log.py`) |
| `action` | an action kind (`bill.pay`, `inbox.file`...) | Propose → Approve, or a standing approval for that kind (as workflows have) |
| `browser` | a browser routine, or one browser step | DEC-0117 commit gate + DEC-0122 only-your-words |
| `read` / `when` / `tell` | workflows' logic: look something up, compare, tell you | the communication gate (5 a day) |
| `ask` | a question to you mid-run ("which card?") | it waits for your answer |
| `you` | something only you can do ("sign the form"), MIA waits for "done" | none needed |
| `phone` (phase 3) | a phone feature: take a photo, share a file, open an app, a notification | the Android permission, plus your OK the first time |
| `desktop` (phase 4) | a step in a desktop app on the PC, by its on-screen labels (Windows UI Automation) | per-app allow list; commit words ask, as in the browser |

### Teaching it

1. **By doing it with her** (the main way). "Watch me: paying the water
   bill." Everything you then do through MIA is recorded as steps: in chat
   (the tools she runs for you, from the turn traces she already keeps), in
   her browser (as today), on the phone (phase 3). "Done" keeps it.
2. **By telling her.** "Every Sunday, check my spending and tell me if
   eating out went over $200." She drafts the steps from her tool list and
   shows them in plain words; you say yes. That's how workflows work today.
3. **By her offering.** When she sees you do the same sequence three times
   (her capability-gap and pattern loops already notice repeats), she
   offers to learn it. Never more than the communication gate allows.

### What doesn't change

- **Approval rules.** Anything that commits outside MIA (submit, buy,
  send, pay) asks every time unless you gave that kind a standing approval,
  and never for money moves or sending.
- **Only your words go out** (DEC-0122), in every step kind.
- **Undo** is exact, per run (as receipts do, DEC-0121).
- **Every run is logged.** A run that stops says where and why. The
  "stopped runs" loop (`browser.runs` today) watches them all.

## The plan, in phases

1. **The engine and chat teaching.** `core/procedures.py`: the model, the
   runner (with `tool`, `action`, `ask`, `you`, `tell` steps), "watch me"
   in chat, the practising-then-learned states, a Procedures screen. Browser
   routines become `browser` steps (existing ones carried over).
2. **Triggers.** Schedules and events. Workflows' specs become procedures
   (existing ones carried over), so there's one list.
3. **Phone steps.** Through the Android app's bridges (camera, gallery,
   share, notifications, open an app), taught by doing them on the phone.
4. **Desktop apps.** Windows UI Automation, by labels like the browser,
   only for apps you allow, commit words always asking. The largest and
   riskiest step: it gets its own decision before it's built.
5. **Glasses.** "Start the tax check" from the glasses, steps narrated.

## Questions for Zac

- [ ] Approve the direction (one engine; browser routines and workflows
      folded into it)?
- [ ] The name: "procedures", "routines", or something else? ("Skills" is
      already your skill tree, and "Routines" is the Household app's.)
- [ ] Phase 1 first, as listed?
- [ ] Desktop apps (phase 4): which apps would you want her to learn first?
      That decides whether it's worth its risk.
