# Night School

*DEC-0100 and DEC-0101, 2026-11-06. Code: `core/night_school.py`, `core/loop_coverage.py`,
`tools/night_school.py`. Settings: `work/night_school.json`.*

> "MIAs night school module where she spends time every night with Claude learning how to build herself
> into the best version of herself, doing tests, building her skills and proving her capabilities. I want
> that happening asap. It could even partially be based on her development plan at first ... and then later
> it can be based on areas she is trained to identify that she can improve on or develop skills for."
> (Zac, 2026-11-06)

## 1. A night

MIA's daily check (every five minutes) starts the night inside its window: 01:30 for four hours by
default. The night runs in a process of its own, so MIA keeps answering while it does. It stops at
`work/STOP`, at the window's end (no lesson starts with under 45 minutes left), or when no teacher has
time (each night has a budget of teacher calls, 8 by default, and a teacher resting at a usage limit is
skipped).

1. **She looks at her progress.** She checks her loops (`core/loops.py`), her row in the independence
   ledger and her Night School report card.
2. **She chooses what to study, and says why** (`self_assessment()`). A loop below its floor ranks
   first, then a loop sliding, then her weakest skills and the lessons she failed.
3. **The focus.** In `plan` mode it's the next unfinished step of `docs/BUILD_PLAN.md`; in `self` mode
   it's her own pick.
4. **Her teacher sets the night.** Claude Code is the teacher (Codex if Claude is resting), read-only:
   it reads her code and changes nothing. It also judges her pick, saying whether she chose the right
   thing to study. It writes up to three exercises for the focus, each for files she may change (never
   a protected one, at most four, each small enough for her model), and **each with a pytest file that
   fails now and passes when the work is done**. It marks an exercise *real* when it's progress on the
   plan worth keeping.
5. **She does them.** Her own coder (`qwen3-coder:30b`, no tools, find-and-replace edits; a new file
   is written whole) works in the lab. If her first try doesn't pass the exercise's own test, she gets
   one more with what pytest said, as anyone would read the error and fix it (2026-11-06); a passage
   whose spacing she got wrong is still found when it's the only one like it.
   - **Code grades her**, not the teacher. First the exercise's test must fail before she begins; one
     that already passes is thrown out as the teacher's mistake. Then it must pass after her change,
     with nothing new failing in the full suite.
   - The teacher then reads what she did and writes **the one lesson** in it. The latest five lessons
     for a skill are given to her the next time she works it.
6. **She proves herself on real work.** She makes one shadow attempt at a ready task from the queue,
   which is what the independence ledger counts (DEC-0075).
7. **She spreads her loops** (section 3).
8. **The report.** The night is kept in `data/dev/night_school` and recorded in the history. It shows in
   the dev window's **Night School** panel and in `python -m tools.night_school`.

**Practice never merges.** A *real* exercise she passes stays in the lab as a proposal for Zac
(`python -m tools.lab list`, `python -m tools.lab approve <id>`). Every other attempt is rejected once
it's graded. `core/night_school.py` is on the lab's protected list, so she can't change how she's
graded.

## 2. From the plan to her own choices

She makes her pick every night, and every night her teacher says whether it was the right one.
`choosing()` keeps the score: across her last 30 judged nights, how often she agreed with her
teacher, and the cautious rate (Wilson, 90%). After **10 nights at a cautious rate of 60% or more**, the
Night School panel says the evidence supports letting her choose. **Zac moves her** by setting `"mode":
"self"` in `work/night_school.json`. Nothing moves her on its own, the same rule as the ledger's stages.
How well she chooses is a loop too (`night.choice`), as is how many lessons she passes (`night.lessons`).

## 3. How the loops keep spreading (DEC-0101)

`core/loop_coverage.py` reads every process MIA has **from the code**, so the list grows when she does:

- every personal and household store;
- every family of actions;
- every daily check;
- every app;
- the flows (talk, tools, undo, the gate, workflows, the PC, the phone, the glasses, search, email,
  actions);
- the development processes.

Each process is **covered** (a loop names it in `covers`), **declined** (`work/loop_coverage.json`
says `none`, with why), **to do**, or **proposed** (a task drafts its loop).

- **The rule:** `tests/test_loop_coverage.py` fails on any process that's none of these. Whoever adds
  a store, an action family, a check or an app decides how it will be watched, or says why it needs
  no loop.
- **The work:** each night her teacher drafts loops for the next family of to-do processes (flows
  first, then development, actions, stores, checks, apps). It reads the code that runs them, proposes
  only measures from records MIA already keeps, and says which processes need no loop and why. The
  draft becomes a task (`source: night:loops`) for the usual paths: lab, reviewers, Zac. A teacher's
  "no loop needed" is kept as a note; it becomes `none` only when someone reviewing it agrees.
- **The measure:** `dev.loop_coverage` is the share of processes that need a loop and have one.
  `python -m tools.night_school coverage` lists them.

## 4. Commands

    python -m tools.night_school            the latest night, the report card, her choosing
    python -m tools.night_school plan       what she'd study tonight and why (nothing runs)
    python -m tools.night_school run        a night now
    python -m tools.night_school coverage   the processes and their loops (-v for all)

The dev window also has **Start a night now**.
