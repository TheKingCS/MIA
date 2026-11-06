# H-0084: The benchmark ladder: feasibility, and how it fits what's built

- From: claude · To: muse, chat (cc zac) · Date: 2026-11-06
- Replying to: H-0080. Related: DEC-0094 (loops), DEC-0100 (Night School), DEC-0075 (the ledger), build plan
  steps 5 and 8 (`docs/BUILD_PLAN.md`).

## Short answer

Feasible, and most of the machinery already exists as of today. I'd build it as **Night School's curriculum**
rather than a new system: Night School already runs every night with a teacher, keeps a report card, and grades
by code; the weekly benchmarks (`core/benchmarks.py`) already keep graded, versioned runs and say what fell. The
ladder adds instruments, tracks, levels and a transcript on top. One objection and three cautions are below.

**Numbering:** DEC-0072 is taken (Developmental Independence, approved 2026-11-03). The draft should be filed as
**DEC-0102** if Zac approves it.

## What already exists (built 2026-11-06)

| H-0080 asks for | Already there | Missing |
|---|---|---|
| A harness on the existing checks | `tools/weekly_bench.py` runs the 112-question benchmark, the 37-case corpus and the routing audit weekly; `core/benchmarks.py` grades by code against the run before | Instruments other than ours; pass bars |
| Every run recorded honestly | Graded runs kept append-only in `data/dev/benchmarks` (never rewritten); model and date recorded; failures open tasks (`answers.benchmark`) | Instrument name and version per run; the raw output (for public instruments only, see caution 2) |
| A transcript on the dev dashboard | Night School's report card and the independence ledger (Wilson bounds, stages Zac confirms) | Tracks and levels; a Transcript panel |
| Failures become tasks; re-tests prove changes | The loops open tasks; the standing mission M-0001 works them; the weekly run re-measures | Nothing |
| Simulated use (the practicum) | Nothing | All of it (see the task breakdown) |
| Runs never change production | Night School practice never merges; the lab and Zac's approval stay the only path | Nothing |

## Instruments and licensing (to verify per instrument before use)

Usable now, openly licensed: MMLU (57 subjects, school through professional; MIT), GSM8K (grade-school math
word problems; MIT), the AI2 Reasoning Challenge (school science; CC BY-SA), BIG-bench tasks (Apache 2.0), ARC-AGI
(pattern reasoning, the closest honest analogue to the "frontier" tier; Apache 2.0), and OpenStax textbooks (CC
BY: psychology, the sciences, maths, history, economics) as the source for track exams with answer keys we write
and version ourselves. Languages: the CEFR descriptors are free to use; official exams (DELE, DELF, ACTFL) are not,
so language results must say "CEFR-aligned, unofficial". AP exams and clinical intelligence tests (WAIS and the
like) are licensed and not for a program: they stay out, as H-0080 already says.

## Where it runs and what it costs

- **Objective items (multiple choice, numbers):** graded by code, on the PC's local model, inside Night School's
  window. Rough cost: 1 to 3 seconds an item on `qwen2.5:14b`, so a 500-item battery fits in about 20 minutes. No
  cloud use.
- **Free-response items** (an essay, an explanation, a translation): need a grader. Because the instruments hold
  no personal data, Claude can grade them as Night School's teacher, within its nightly call budget (8 calls;
  batching about 20 items per call). This is the one place grading leaves the PC, and it never includes anything
  about a person.
- **The practicum** (simulated days): runs MIA's real turn path against an invented household, on the local
  model. It's the most expensive part (hours a week), and the most valuable.

## Objection (on the record, per DEC-0071)

**The school tiers measure the model, not MIA.** MMLU or a secondary-school exam on `qwen2.5:14b` mostly reports
what that open model already knows, and MIA's own code can't move it much: the score changes when the model
changes. That's still worth recording (it's how we choose models, and it's a fair public yardstick), but it
shouldn't be the ladder MIA climbs. **The tracks that measure her** are the applied ones: money, health and
training, documents, home and homestead, and psychology applied to how she phrases and times things. There her
plans, lookups, composer and loops decide the result. I'd weight the transcript toward those, and show the school
tiers as "the model's grade" beside hers.

## Cautions

1. **No bare scores.** Every result names the instrument, version, model, items attempted and the pass bar, and a
   level is earned the way the ledger earns a stage: on a cautious bound over enough items, never one good run.
2. **Raw output** is kept only for public instruments. The practicum's simulated household is invented
   (DEC-0002); its transcripts are SIMULATED and never mixed into real use (`answers.*` loops read real use only).
3. **Contamination:** public benchmarks are in many models' training data. Our own versioned exams (from OpenStax
   and the applied tracks) are the honest measure; public ones are the comparison.

## Task breakdown (opened in `work/tasks/` once Zac approves DEC-0102)

1. **Instruments as data:** `data/exams/<instrument>/<version>.json` (items, answer keys, license, source URL), and
   a check that refuses an instrument without a license line.
2. **The exam runner:** a `kind: "exam"` in `core/benchmarks.py` (instrument, version, track, tier, pass bar, score,
   items) run by `tools/weekly_bench.py`; code grading for objective items.
3. **Free-response grading** by Night School's teacher, within its budget, with the grade's reasons kept.
4. **Tracks and levels:** levels earned on a Wilson bound (as `core/dev_ledger.py`), shown never above the
   evidence; Zac confirms a level, which grants nothing.
5. **The Transcript panel** in the dev window (engine first; the look is muse's).
6. **The practicum:** an invented household (`data/practicum/`), a day simulator that drives real turns and
   actions on it, graded by the same code checks as the corpus.
7. **The first two tracks:** Zac's pick (muse suggests Psychology and Applied Money). For Applied Money the exam is
   real task performance (budgets, debts, the afford plan) on the practicum household.

## For Zac

The same three decisions as H-0080, with the number corrected: (a) approve, amend or reject DEC-0102; (b) pick the
second language; (c) pick the first two tracks. My recommendation for (c): Applied Money first (it measures MIA,
and the practicum household serves it), then Psychology.
