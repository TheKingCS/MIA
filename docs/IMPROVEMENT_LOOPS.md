# MIA's Improvement Loops

*Claude, 2026-11-06, for Zac's requirement (DEC-0094): "We need to identify every situation and interaction and
operation that should have monitoring and trigger improvements and development to better her functioning so those
loops will always be in place to make her better ... almost every process has the potential for some kind of self
assessment and improvement loop and we should identify those and build it." The registry in code is
`core/loops.py`; this document is its map. If the two disagree, fix one in the same change.*

## 1. One shape for every loop

```
MEASURE ──▶ COMPARE ──▶ FINDING ──▶ WORK ──▶ FIX ──▶ (MEASURE again: did it work?)
```

- **Measure**: a number from something MIA already records (a failure, a trace, a rating, a test, an undo, a review,
  a run). Code computes it, never a model. Each measurement is kept, so there's a trend, not a snapshot.
- **Compare**: against a **floor** (the level it must not fall below) and against **itself** (a drop from its own
  recent median is a regression even above the floor). Too few data points means "not enough yet", never a guess.
- **Finding**: what's wrong, in numbers, with where the numbers came from.
- **Work**: a task in `work/tasks/` (source `loop:<id>`, one open task per loop at a time), which the council,
  a mission or MIA's own coder can take; or a lesson, or a finding for the person through the communication gate,
  depending on the loop.
- **Fix**: through the existing paths only: the lab, two reviewers, Zac's approval for code (DEC-0058, DEC-0069);
  approval for anything that changes the person's data.
- **Verify**: the next measurement says whether the fix worked. A task closed while its loop stays below its floor
  is reopened by the loop.

**Rules** (DEC-0094):
1. Loops measure; they never change MIA by themselves. Every fix goes through the paths above.
2. A loop over a person's use keeps its history in **their** folder (DEC-0001). What reaches a task in the repo is
   numbers and kinds ("12 rephrases in 7 days, 4 about Kitchen"), never what the person said.
3. Each loop says its cadence (every day, every week) and its cost (free and local, or a model's time); the expensive
   ones run when the PC is idle, within the usage rules (DEC-0079).
4. The loops' own code is on the lab's protected list: MIA can't loosen how she's judged.

## 2. The catalog

Status: **built** (measured now), **step N** (in `docs/BUILD_PLAN.md`), **later** (needs something not built).
Scope: **device** (the PC and the development platform) or **person** (one person's use).

### A. Conversation and intelligence (how well she answers)

| Loop | Watches | Signal (source) | Floor / trend | Triggers | Status |
|---|---|---|---|---|---|
| `answers.failures` | Turns that went wrong | Fix-It Log events per 100 traced turns (`core/failure_log.py`, `core/turn_trace.py`) | trend | task, by top kind | built |
| `answers.thumbs` | Whether answers land | 👍 share of rated answers (`core/answer_ratings.py`) | ≥ 70% | task | built |
| `answers.rephrased` | Not understood the first time | `rephrased` events per 100 turns | trend | task | built |
| `answers.talked_instead` | Had the tool, only talked | `talked_instead` per 100 turns | ≤ 2 | task (tool routing) | built |
| `answers.no_tool` | Asked for something she can't do | `no_tool` events | trend | **capability gap → proposal** (self-enablement) | built (count); step 9 (proposals) |
| `answers.slow` | Too slow | share of turns over 25 s | ≤ 10% | task | built |
| `answers.model_down` | The model not answering | `model_down` + `garbled` | 0 a week | task | built |
| `answers.undo_soon` | Did the wrong thing | `undo_soon` per action | trend | task, by action kind | built |
| `answers.benchmark` | Zac's 112-question benchmark | score (`tools/intelligence_check.py`) | no drop | task per question that fell | built |
| `answers.corpus` | Personality and tone | golden conversations (`tools/conversation_check.py`) | no drop | task | built |
| `answers.routing` | Questions reaching the right plan | `tools/bench_audit.py` coverage | no drop | task | built |
| `answers.numbers` | A number she didn't look up | answers replaced by the fact sheet (`core/question_plans.answer`) | 0 | task | built |
| `memory.quality` | Memories she keeps | memories edited or deleted within 14 days of being kept | ≤ 15% | lesson for the extractor | built |
| `phone.model` | The phone's model | golden set (`tools/model_check.py`) | no drop | task | step 5 |

### B. Proactivity (what she says unasked)

| Loop | Watches | Signal | Floor / trend | Triggers | Status |
|---|---|---|---|---|---|
| `gate.unwelcome` | Messages people stop | "pause this kind" (`communication.resume` history) and dismissals | trend | lower that kind's priority (a proposal) | built |
| `gate.saturation` | Too many offers | days the daily limit was hit | ≤ 2 a week | task: merge or drop a kind | built |
| `findings.acted` | Whether her findings matter | findings followed by the suggested action within 7 days | trend | retire or improve a finding kind | later (step 9) |

### C. Corrections in every area (the universal "she got it wrong")

Whenever the person edits or undoes something MIA did or suggested, that's a judgment of her work. One loop per
area, the same code:

| Loop | Watches | Signal | Status |
|---|---|---|---|
| `corrections.<area>` (money, kitchen, workout, missions, calendar, maintenance, inbox, memories, creations...) | MIA's changes later corrected | an action proposed by MIA undone, or the same record edited by the person within 3 days | built (`core/corrections.py`) |
| `money.categories` | Plaid categories | transactions re-categorized by the person (and the rule that would have got it right) | step 4 |
| `inbox.reading` | OCR and document reading | fields corrected after a read | step 4 |
| `loop.prediction` | The Loop's predicted week | predicted shifts and routines against what was logged | step 4 |
| `pantry.prediction` | Pantry levels | predicted against counted | later |

### D. Her creations (ACAF)

| Loop | Watches | Signal | Status |
|---|---|---|---|
| `creations.unused` | Screens nobody opens | published, not opened in 30 days (`core/creations.py`) | built |
| `creations.maker` | Designs that fail their checks | maker retries and failures | step 3 |
| `workflows.failing` | Workflows that stop | runs ending "stopped" | built |
| `creations.held` | Screens broken by a change | creations that no longer pass their checks | built |

### E. Devices and data

| Loop | Watches | Signal | Status |
|---|---|---|---|
| `pc.disk` | Room to work | free disk on the PC (`core/system_health.py`) | built |
| `data.recovered` | Corrupt files | data-recovery events (`core/data_recovery.py`) | built |
| `vault.coverage` | Photos kept safe | phone media not yet on the PC, and transfer failures | step 3 |
| `glasses.voice` | Speech through the glasses | glasses turns rephrased or failed | step 3 |
| `relay.health` | The sealed relay | failed or slow relay calls | later |
| `phone.link` | Phone to PC | home-link failures and fallbacks | step 3 |

### F. Her development (the platform)

| Loop | Watches | Signal | Floor / trend | Status |
|---|---|---|---|---|
| `dev.tests` | The suite | failures beyond the known ones (weekly full run) | 0 new | built (`dev.suite`) |
| `dev.layering` | The layering rule | breaks (`core/dev_map.py`) | 0 | built |
| `dev.doc_drift` | Docs against code | files the current-truth docs name that don't exist | 0 | built |
| `dev.stuck` | Work going nowhere | tasks in review or claimed for 7+ days | 0 | built |
| `dev.reviewers` | Review accuracy | each provider's reviewing rate (`core/dev_ledger.py`) | bound ≥ 50% | built |
| `dev.knowledge` | MIA's write-ups | withdrawn share of her derived entries | ≤ 30% | built |
| `dev.coder` | MIA's own coder | shadow pass rate (the ledger) | trend | built |
| `dev.limits` | Usage limits | limit hits per provider per week (`core/dev_usage.py`) | trend | built |
| `dev.council_cost` | Council chatter | calls per council turn | trend | built |
| `dev.reverts` | Merges undone | reverts per merge | 0 | built |
| `dev.dependencies` | Outdated or vulnerable packages | `pip list --outdated` and advisories | 0 critical | built (`dev.vulnerable`, `dev.outdated`) |
| `dev.chronicles` | Story material waiting | candidates waiting | trend | built |

### G. Planned features (each built with its loop)

| Feature | Its loop |
|---|---|
| Good News Radio | stories later found misleading; skipped episodes; ratings by personality |
| Operating Journal | the gap between how Zac means to operate and how he does, by area, as a trend he sees |
| Recreation log | planned against played; connection to training load |
| Maps and comms | position fix quality, offline tile coverage, message delivery on the mesh |
| Council on the glasses | turns that failed or were cut off; speaker misheard |

## 2a. How the loops keep spreading (DEC-0101)

This catalog was written by hand once; from now on the code keeps it honest. `core/loop_coverage.py` lists
every process MIA has from the code itself, and each is covered by a loop (`covers` in `core/loops.py`),
declined with a reason, or on the to-do list in `work/loop_coverage.json`. A test fails on a new process
that's none of these. Night School's teacher drafts loops for the next family of to-do processes every
night (`docs/NIGHT_SCHOOL.md`). `python -m tools.night_school coverage` shows where each stands.

## 3. Cadence

| When | What runs |
|---|---|
| Every change | the test suite, in the lab (exists) |
| Every day (the app's daily check, and the dev window) | every free loop (A, B, C, D, E, most of F) |
| Every week, when the PC is idle | the full suite, the benchmark, the corpus, the routing audit, the phone model check, a shadow attempt, the dependency audit |
| Every month (Zac, in the dev window) | the loops' floors, the ledger's stages, which loops still earn their place |

## 4. Where it shows

The dev window's **Her loops** panel: every loop, its latest number, its trend, its floor, and the task it opened.
For a person's own loops, MIA's weekly self-report (through the communication gate) says what got better and
what she's working on.
