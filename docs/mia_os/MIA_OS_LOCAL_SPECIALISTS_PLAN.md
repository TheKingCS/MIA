# Specialists that do real engineering on local models: the plan

*Claude (Fable), 2026-11-17, for Zac's review. It follows DEC-0197 (Zac: "The specialists should be local models
that are capable of doing the engineering. We need to do whatever work makes that possible") and changes one answer
in `MIA_OS_SPECIALIZED_AGENT_TEAMS.md`: that document said the specialist thinking needs cloud models. This plan
says how to get it from models on Zac's own machines. Nothing here is built yet. Model names and sizes come from
public guides read today and are not measured on his PC; step S0 exists to measure them.*

## 1. The honest starting point

- MIA's everyday model is llama3.2:3b; her heavier local model is qwen2.5:14b. Neither can do acoustic or
  electrical engineering unaided.
- The PC has a 24 GB graphics card (Radeon RX 7900 XTX), 32 GB of memory. It runs models of roughly 20 to 32
  billion parameters. A 30B-class model measured there on 2026-11-15: 37 s to load, 3.4 s an answer.
- Guides from this month name these as the strongest that fit 24 GB: **Qwen3.8 27B** (about 18 GB), **Gemma 4 31B**
  (strong on science questions), **gpt-oss-20b** (about 13 GB, with a reasoning-effort setting), and
  **qwen3-coder:30b** for code. These are other people's rankings, and they disagree with each other.
- No model that fits 24 GB matches the large cloud models at open-ended engineering. A plan that pretends it does
  will produce confident wrong numbers, which in electrical, battery and structural work is the dangerous kind of
  wrong.

So "capable of doing the engineering" is not reached by picking a model. It is reached by building the work so a
mid-size model can do it correctly: it reasons and chooses; code does everything that must be exact.

## 2. The principle: the model decides, code computes, a second model checks

MIA already works this way in two places, and both are the pattern to extend:
- **Material lists** (`core/build_calcs.py`, DEC-0118): the model never works out a quantity. It picks the
  calculator and its inputs; code returns the numbers and the span-table note.
- **Verify These Claims** (`core/ual.py`): a claim is "supported" only when code confirms the verdict names one of
  that claim's own sources.

Applied to a specialist, every piece of engineering work becomes a **worksheet** with five steps, each of which a
27B model can do well:

1. **Frame it:** restate the task, list what's known, what's assumed, and what's missing. Missing input that
   matters is asked for, never guessed.
2. **Look it up:** the specialist's own confirmed notes, the offline reference library, and (with the person's
   switch on) a web search. Each fact used carries its source.
3. **Calculate:** every number comes from a calculator in code (section 4), called as a tool with units. The model
   may not write a number that a calculator didn't return or a source didn't state.
4. **Answer:** the recommendation, with each number traced to its calculator or source, the assumptions listed,
   and the caveat for safety-critical work (Q-57).
5. **Check:** code re-runs every calculation and rejects any number in the answer it can't trace. Then a
   **different local model** reviews the reasoning (section 5). A failed check sends the worksheet back once, then
   reports plainly what it couldn't do.

What the worksheet refuses to do is as important: it says "I can't establish this" instead of producing a figure
with no calculator or source behind it.

## 3. S0: measure before choosing (the PC is needed for the run, not for the build)

An **engineering bench**, beside the existing model bench (`core/model_bench.py`, which only measures tool choice):
- 10 to 15 tasks per discipline, each with an answer that **code can check**: a wire gauge for a load and run
  length, a joist size for a span, a heat-loss figure, a link budget, a battery runtime, a unit conversion chain,
  "which of these three inputs is missing".
- Each task is run three ways: the model alone; the model with calculators; the full worksheet. That shows how
  much the method adds, per model, instead of assuming it.
- Measured: right or wrong (by code), whether it invented a number, whether it asked for a missing input, time to
  first answer, memory used.
- Run on the PC for each candidate model. The result is a table per discipline, kept in the repo and shown on the
  specialist's profile. **The model per specialist is chosen from this table, not from a guide.**

The harness and the tasks can be written and tested without the PC (with a stand-in model). The measurement run
itself needs the PC's graphics card: one command, left to run.

## 4. S2: calculators, one discipline at a time

This is the largest part of the work and what actually makes a local model capable. Each calculator is plain code
with tests, takes and returns values with units, and ends with the note of what standard or table it follows and
that a qualified person must check safety-critical results.

| Discipline | First calculators | Exists today |
|---|---|---|
| Electrical | Ohm's law and power, wire gauge for load and length, voltage drop, breaker and circuit load, battery runtime, charge time | Ohm's law (`core/toolbox_calcs.py`) |
| Structural and carpentry | joist, beam and rafter spans from tables, loads, stairs | 20 structures in `core/build_calcs.py` |
| HVAC and energy | heat loss and gain, duct and vent sizing, insulation R-values, solar and generator sizing | a cold room's wall R-value |
| Plumbing | pipe sizing, flow and pressure drop, drain slope | none |
| Radio | link budget, antenna length, path loss, line of sight | none |
| Acoustics and audio | speaker sensitivity and SPL at distance, amplifier power, enclosure volume, delay for spatial placement | none |
| Mechanical and materials | torque, gear ratio, fastener and bearing load, thermal expansion | none |
| Embedded and power | current budget, regulator heat, pull-up values, sample rates | none |
| Greenhouse | irrigation flow, light (DLI), ventilation rate, heating demand | parts of the grow lab |

A shared **units module** comes first: every value carries its unit, and adding metres to feet is an error, not a
wrong answer.

## 5. S5: review by a different local model

The teams document's rule (review is independent only across models) holds locally too: a reviewer from a
**different model family** than the author's. With 24 GB, two large models don't fit at once, so they run in turn
(about 37 s to swap). A review is therefore a deliberate step for results that matter, not something run on every
sentence. The blocking safety review (Q-57) is one of these.

## 6. S3: which model does what

- A table of specialist and task type to model, filled from S0. Everyday talk stays on the small fast model.
- Asking a specialist for engineering work says up front that it will take longer (the model load, then several
  steps), and shows progress on the run record.
- **The Pi:** its AI HAT+ 2 runs small models only. On the Pi, a specialist's worksheet is sent to the PC's model
  over the home link (`core/home_link.py`, `core/heavy_jobs.py`), the way OCR already is. With the PC off, the Pi
  says the specialist isn't available instead of answering with a model too small for it.

## 7. S4: the roster grows on a schedule, not "someday"

Zac, 2026-11-17: the other specialists must not end up at the back. So the roster is its own track, running beside
the engine work from the start:

- The 16 specialists that exist get the worksheet first (they have charters, limits and workbooks).
- The handoff names about 45. The remaining ones are added **in batches on a standing schedule**, a few each week,
  in an order set by Zac's real projects: first the greenhouse pilot's (greenhouse systems, IoT, electrical), then
  the hoodie's (acoustic, audio DSP, textile, embedded, power), then the rest of the Engineering department, then
  the other departments.
- A specialist counts as added only when it has all of: a charter and limits, a caveat where its work is
  safety-critical, starter questions for Night School, at least its first calculators, and its own bench tasks.
  A name with a paragraph is not a specialist.
- Night School already studies one specialist a night. With 45 that is one visit every six weeks, so study is
  weighted toward the specialists a live project is using.
- A page shows the roster: built, in progress, planned, with each one's bench results. Progress is visible, so it
  can't quietly stall.

## 8. S6: training her own (later, and only if measured gaps remain)

`core/model_forge.py` is where MIA trains small models. A later stage can fine-tune an adapter per discipline from
confirmed notes and corrected worksheets. It comes after S0 to S5 because (a) the bench must exist to prove an
adapter is better and not just different, and (b) training on the Radeon card under Linux is its own piece of work.

## 9. What would raise the ceiling

Named so it's a choice and not a surprise:
- **More graphics memory** (a second card, or a 48 GB card) runs 70B-class models, a real step up in reasoning.
- **More system memory** (64 GB) lets a larger model run partly on the processor, slowly, for overnight work.
- Neither is needed to start. S0 will show whether the 24 GB models with the worksheet are good enough.

## 10. Order of work

| Step | What | Needs the PC | Model |
|---|---|---|---|
| **S0a** | The units module, the engineering bench harness and its first tasks (electrical, structural) | no | Fable |
| **S1** | The worksheet engine (`core/specialist_work.py`): frame, look up, calculate, answer, check; on the run record; refuses untraceable numbers | no | Fable |
| **S2** | Calculators, discipline by discipline, electrical first | no | Opus, Fable reviews the safety-critical ones |
| **S4** | The roster track: batches of new specialists, from the first week | no | Opus writes, Fable reviews caveats and limits |
| **S0b** | The measurement run on the PC for each candidate model | **yes** | either |
| **S3** | The model table from S0b; the Pi asking the PC | partly | Fable |
| **S5** | Review by a second local model; the blocking safety review | partly | Fable |
| **S6** | Adapters, if S0b shows gaps the worksheet doesn't close | yes | Fable |

This sits beside the teams roadmap: T1 (registry) and T2 (workspace) are unchanged and still Opus's. T3 onward uses
the worksheet where that document said "a cloud model".

## 11. Risks

| Risk | Answer |
|---|---|
| A confident wrong number in safety-critical work | numbers only from calculators or sources; code re-checks; the caveat; the blocking safety review |
| The local models aren't good enough even with the worksheet | S0 says so with numbers, per discipline; section 9's options; the specialist says "I can't" instead of guessing |
| Slow: model swaps and several steps | said up front, progress shown, review only where it matters |
| 45 specialists become 45 paragraphs | the "counts as added" rule in section 7; the roster page |
| Calculators carry mistakes of their own | tests against published worked examples; each names its standard or table; Fable reviews the safety-critical ones |
| Model names in guides are wrong or gone | nothing is hard-coded to a name; the table is filled from what's measured on the PC |

## 12. Sources for the model candidates (read 2026-11-17, not verified on the PC)

- https://localaimaster.com/blog/best-ollama-models
- https://localaimaster.com/vram/best-ollama-models-24gb-vram
- https://localllm.in/blog/best-local-llms-24gb-vram
- https://www.popularai.org/p/best-local-llm-rtx-3090-24gb
- https://huggingface.co/blog/daya-shankar/open-source-llm-models-to-run-locally
