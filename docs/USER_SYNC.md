# User Sync: MIA getting to know a person

*Zac, 2026-10-27. Recorded by Claude; approved to plan (DEC-0048), not
built yet. Zac's words: "This would be a cool feeling way to present MIA
as if she is connecting with your consciousness and gathering info about
you to become your system."*

## What it is

A deep first conversation that turns into a working MIA for that person.
"Hey MIA, I'm about to pass you to Faith. Change the active user to
Faith and start User Sync." MIA waits until Faith says she's ready, then
talks with her (not a form) about:

- her **routine**: work days and hours, breaks, chores and how often,
  sleep;
- **hobbies and interests**, and how often she wants to do each
  (building projects, reading as a habit...);
- **goals**, and why;
- **meals and workouts**: what she eats, cooks, trains, how often;
- **assets**: vehicles, tools, equipment, the house;
- anything else each part of MIA needs to work for her.

What she says becomes real records: her **loop** (rhythms with days and
times), her **first missions** and quests, her **garage** (assets), her
**kitchen** and **workout** info, her goals and reasons. Every record is
shown to her to confirm before it's kept (Propose → Approve, as always).

## Then MIA keeps growing with them

- **Curious, now and then**: short conversations to update what's
  changed and learn more ("You've been building a lot lately: want
  woodworking as a weekly rhythm?"). Through the communication gate.
- **A survey of what's working**: what they like, what they'd change,
  and switching features or missions on and off for them, so the system
  adapts itself to the person.

## Rules it has to keep

- **Each person's data is their own** (core/personal_data.py). Passing
  MIA to someone by voice never opens another person's account: Faith
  confirms she's ready **by signing in** (her own password or PIN), or
  User Sync creates her account on a device that allows account creation
  (never through the network-reachable server).
- A **child** account gets the child-safe version (no money questions,
  no weigh-ins; core/child_accounts.py).
- Nothing personal in the repo; nothing hardcoded about anyone.
- The model only phrases questions and reads answers into proposed
  records; the records go through the action contract, undoable.

## Open questions for Zac

1. Voice first, typed, or both? (Both is the default plan.)
2. How long should the first sync be: one sitting, or a few short
   sessions MIA picks back up?
3. Should an existing user (Zac) be able to run User Sync too, to fill
   in what MIA doesn't know yet?
