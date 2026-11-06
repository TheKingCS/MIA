# MIA's loops, as built

*Generated from `core/loops.py` by `python -m core.loop_catalog`; never edit by hand (a test keeps it current). The design and the reasons: `docs/IMPROVEMENT_LOOPS.md`; what each process is watched by: `python -m tools.night_school coverage`.*

80 loops in 7 areas.

## Answers

| Loop | Watches | Scope | Floor | When it slips | Covers |
|---|---|---|---|---|---|
| `answers.benchmark` | benchmark questions that fell since last week | device | ≤ 0 | opens a task, weekly | `flow:talk` |
| `answers.benchmark_clean` | benchmark questions answered by a plan or code, unflagged | device | trend | shown, never acted on, weekly | `flow:talk` |
| `answers.calibration` | how much better her sure answers land than the rest (👍 share) | person | ≥ 0 (from 5) | opens a task | `store:ratings` |
| `answers.corpus` | conversation answers code flagged (filler, closing offers, lists...) | device | trend | opens a task, weekly | `flow:talk`, `flow:glasses` |
| `answers.failures` | turns that went wrong, per 100 | person | trend (from 20) | opens a task | `flow:talk`, `module:assistant`, `action:failures`, `store:conversations` |
| `answers.model_down` | the model not answering, or garbled | person | ≤ 0 | opens a task | `flow:talk`, `flow:pc` |
| `answers.no_tool` | asked for something she has no tool for | person | trend | shown, never acted on | `flow:tools`, `store:failures` |
| `answers.numbers` | answers with a number she hadn't looked up, per 100 turns | person | ≤ 2 (from 20) | opens a task | `flow:talk` |
| `answers.projections` | projected dates (debt-free, freedom) that came true when they came | person | ≥ 0.5 (from 3) | opens a task | `store:budget` |
| `answers.rephrased` | asked again in other words, per 100 turns | person | trend (from 20) | opens a task | `flow:talk` |
| `answers.routing` | benchmark questions that reach no plan, lookup or tool | device | trend | opens a task, weekly | `flow:tools` |
| `answers.slow` | share of answers over 25 seconds | person | ≤ 0.1 (from 20) | opens a task | `flow:talk`, `store:traces` |
| `answers.talked_instead` | had the tool but only talked, per 100 turns | person | ≤ 2 (from 20) | opens a task | `flow:tools` |
| `answers.thumbs` | answers rated 👍 | person | ≥ 0.7 (from 5) | opens a task | `flow:talk`, `store:ratings`, `action:answer` |
| `answers.undo_soon` | what she did, undone right away, per 100 turns | person | trend (from 20) | opens a task | `flow:undo` |
| `gaps.repeated` | things she can't do yet, asked more than once (self-enablement) | person | trend | shown, never acted on | `flow:tools`, `check:capability_gaps`, `action:gap` |
| `memory.quality` | memories corrected within 14 days of being kept | person | ≤ 0.15 (from 5) | opens a task | `store:user_memories`, `module:memories` |
| `sight.failed` | photos she couldn't answer about, in 30 days | person | ≤ 0.1 (from 5) | opens a task | `flow:sight` |

## Corrections

| Loop | Watches | Scope | Floor | When it slips | Covers |
|---|---|---|---|---|---|
| `actions.declined` | suggestions she made that were turned down, per 100 turns | person | trend (from 20) | opens a task | `flow:actions` |
| `actions.failed` | things approved that broke when they ran, in 7 days | person | ≤ 0 | opens a task | `flow:actions` |
| `corrections.all` | her changes corrected within 3 days, every area | person | ≤ 0.2 (from 10) | opens a task | `flow:actions`, `flow:undo` |
| `corrections.calendar` | her changes in calendar corrected within 3 days | person | ≤ 0.25 (from 5) | opens a task |  |
| `corrections.creations` | her changes in creations corrected within 3 days | person | ≤ 0.25 (from 5) | opens a task |  |
| `corrections.files` | her changes in files corrected within 3 days | person | ≤ 0.25 (from 5) | opens a task |  |
| `corrections.home` | her changes in home corrected within 3 days | person | ≤ 0.25 (from 5) | opens a task |  |
| `corrections.inbox` | her changes in inbox corrected within 3 days | person | ≤ 0.25 (from 5) | opens a task |  |
| `corrections.kitchen` | her changes in kitchen corrected within 3 days | person | ≤ 0.25 (from 5) | opens a task |  |
| `corrections.maintenance` | her changes in maintenance corrected within 3 days | person | ≤ 0.25 (from 5) | opens a task |  |
| `corrections.memories` | her changes in memories corrected within 3 days | person | ≤ 0.25 (from 5) | opens a task |  |
| `corrections.missions` | her changes in missions corrected within 3 days | person | ≤ 0.25 (from 5) | opens a task |  |
| `corrections.money` | her changes in money corrected within 3 days | person | ≤ 0.25 (from 5) | opens a task |  |
| `corrections.music` | her changes in music corrected within 3 days | person | ≤ 0.25 (from 5) | opens a task |  |
| `corrections.people` | her changes in people corrected within 3 days | person | ≤ 0.25 (from 5) | opens a task |  |
| `corrections.tasks` | her changes in tasks corrected within 3 days | person | ≤ 0.25 (from 5) | opens a task |  |
| `corrections.workouts` | her changes in workouts corrected within 3 days | person | ≤ 0.25 (from 5) | opens a task |  |
| `email.discarded` | drafts thrown away instead of sent, in 30 days | person | ≤ 0.4 (from 5) | opens a task | `flow:email`, `store:email_drafts` |
| `email.left_open` | drafts left open over a week | person | trend | shown, never acted on | `flow:email` |
| `inbox.reading` | documents whose read fields were corrected when filed, in 60 days | person | ≤ 0.25 (from 5) | opens a task | `store:inbox`, `action:inbox` |
| `loop.prediction` | the Loop's planned work days that didn't match what happened, 4 weeks | person | ≤ 0.3 (from 8) | opens a task | `store:loop`, `check:loop` |

## Creations

| Loop | Watches | Scope | Floor | When it slips | Covers |
|---|---|---|---|---|---|
| `creations.held` | published screens that no longer pass their checks | person | ≤ 0 | opens a task | `store:creations` |
| `creations.maker` | designs that missed their checks the first time (Make Something) | person | ≤ 0.5 (from 5) | opens a task | `module:web_home` |
| `creations.unused` | published screens nobody opens | person | ≤ 0 | offers it to them | `store:creations`, `action:creation` |
| `workflows.failing` | workflow runs that stopped | person | ≤ 0 | opens a task | `flow:workflows`, `check:workflows` |

## Development

| Loop | Watches | Scope | Floor | When it slips | Covers |
|---|---|---|---|---|---|
| `dev.chronicles` | Chronicles candidates waiting | device | trend | shown, never acted on | `dev:chronicles`, `check:chronicle`, `store:saga_moments` |
| `dev.coder` | MIA's coder: shadow attempts passed | device | trend | shown, never acted on | `dev:shadow` |
| `dev.council_cost` | calls per council turn | device | trend | shown, never acted on | `dev:council` |
| `dev.doc_drift` | files the docs name that don't exist | device | ≤ 0 | opens a task | `dev:code` |
| `dev.knowledge` | MIA's write-ups withdrawn | device | ≤ 0.3 (from 5) | opens a task | `dev:knowledge` |
| `dev.lab` | her lab proposals that went in, of those settled in 60 days | device | ≥ 0.5 (from 5) | opens a task | `action:lab` |
| `dev.layering` | breaks of the layering rule | device | ≤ 0 | opens a task | `dev:code` |
| `dev.limits` | usage limits hit in a week | device | trend | shown, never acted on | `dev:usage` |
| `dev.loop_coverage` | processes with a loop, of those that need one | device | trend | shown, never acted on | `dev:loops`, `check:loops` |
| `dev.outdated` | required packages behind their latest release | device | trend | shown, never acted on, weekly, heavy | `dev:dependencies` |
| `dev.reverts` | merges the lab reverted, of those approved in 30 days | device | ≤ 0.2 (from 3) | opens a task | `dev:merge` |
| `dev.reviewers` | the weakest reviewer's cautious rate | device | ≥ 0.5 | opens a task | `dev:review` |
| `dev.stuck` | tasks claimed for a week or more | device | ≤ 0 | opens a task | `dev:tasks`, `dev:missions` |
| `dev.suite` | tests failing on the committed code that aren't known failures | device | ≤ 0 | opens a task, weekly, heavy | `dev:suite` |
| `dev.suite_time` | seconds the full suite takes | device | trend | shown, never acted on, weekly, heavy | `dev:suite` |
| `dev.vulnerable` | installed packages with a known vulnerability | device | ≤ 0 | opens a task, weekly, heavy | `dev:dependencies` |
| `night.choice` | nights her own pick of what to study matched her teacher's | device | trend (from 5) | shown, never acted on | `dev:night_school` |
| `night.lessons` | Night School lessons passed this week | device | trend (from 3) | shown, never acted on | `dev:night_school`, `check:night_school` |
| `phone.vulnerable` | packages the phone app bundles with a known vulnerability | device | ≤ 0 | opens a task, weekly, heavy | `dev:dependencies`, `flow:phone` |

## Devices

| Loop | Watches | Scope | Floor | When it slips | Covers |
|---|---|---|---|---|---|
| `data.recovered` | data files found corrupt and reset, in 7 days | device | ≤ 0 | opens a task | `flow:data` |
| `glasses.voice` | glasses turns unanswered or slow, in 7 days | person | ≤ 0.15 (from 10) | opens a task | `flow:glasses` |
| `pc.disk` | free space on the PC | device | ≥ 20 | opens a task | `flow:pc` |
| `phone.link` | hours since their phone last reached this PC | person | trend | shown, never acted on | `flow:phone` |
| `screens.broken` | desktop apps and web pages that broke, in 7 days | person | ≤ 0 | opens a task | `module:assistant`, `module:budget`, `module:character`, `module:classroom`, `module:dashboard`, `module:diagnostics` and 29 more |
| `search.empty` | Ctrl+K searches that found nothing, in 30 days | device | ≤ 0.3 (from 10) | opens a task | `flow:search` |
| `vault.coverage` | photos over a week old still only on the phone | person | ≤ 0.1 (from 20) | opens a task | `store:memory_vault` |

## Life

| Loop | Watches | Scope | Floor | When it slips | Covers |
|---|---|---|---|---|---|
| `classroom.stalled` | courses under way that no lesson moved in 30 days | person | trend | shown, never acted on | `store:classroom` |
| `journal.pace` | how often they operate the way they said they mean to | person | trend | shown, never acted on | `store:operating_journal`, `action:operating`, `check:operating_journal` |
| `missions.recurring` | daily recurring missions not done, in 30 days | person | ≤ 0.5 (from 10) | offers it to them | `check:recurring_mission` |
| `recreation.load` | this week's play load against the four weeks before (past 1.5: easing off helps) | person | ≤ 1.5 | shown, never acted on | `store:recreation`, `action:play` |

## Proactivity

| Loop | Watches | Scope | Floor | When it slips | Covers |
|---|---|---|---|---|---|
| `checks.dismissed` | the daily check whose messages are dismissed most, in 30 days | person | ≤ 0.6 (from 10) | opens a task | `check:budget_nudge`, `check:calendar_digest`, `check:checkin`, `check:chronicle`, `check:findings`, `check:grow_alert` and 16 more |
| `gate.dismissed` | unprompted messages dismissed, in 7 days | person | ≤ 0.5 (from 5) | opens a task | `flow:gate`, `store:communication`, `store:notifications` |
| `gate.expired` | messages held back that expired before they went out | person | trend (from 3) | shown, never acted on | `flow:gate` |
| `gate.saturation` | days the daily limit of unprompted messages was hit, in 7 | person | ≤ 2 | opens a task | `flow:gate` |
| `gate.unwelcome` | kinds of message on a break for being dismissed | person | trend | shown, never acted on | `flow:gate`, `action:communication` |
| `news.misleading` | Good News Radio stories they called misleading, in 30 days | person | ≤ 0.05 (from 20) | opens a task | `check:good_news` |
| `notes.offers` | offers to keep what they said they'd do, decided or set aside, turned down | person | ≤ 0.6 (from 10) | opens a task | `store:life_notes` |
