# The Specialist Forge, online and offline knowledge, and agents working in parallel

*Claude (Opus), 2026-11-17, for Zac's request of the same day (`docs/mia_os/prompts/26_SPECIALIST_FORGE_AND_PARALLEL_AGENTS.md`,
kept verbatim). A design with decisions for Zac (section 6). Nothing here is built yet. It extends
`MIA_OS_LOCAL_SPECIALISTS_PLAN.md` (DEC-0197) and `MIA_OS_SPECIALIZED_AGENT_TEAMS.md` (DEC-0198); it doesn't replace
them.*

## 1. What he asked for, in three parts

1. **MIA adds, refines and specializes her own specialists**, for whatever kind of expert a project turns out to
   need, instead of waiting for a Claude session to write each one.
2. **Specialists use resources online and keep working offline.**
3. **Several agents working at once, visibly**: like the video, many cursors moving over one area, each an agent
   doing its part.

## 2. Where things stand

| Part | Exists | Missing |
|---|---|---|
| A specialist | 19 in `core/specialists.py`: charter, limits, caveat, words, starter questions, role (DEC-0198); workbooks of notes (derived until Zac confirms); Night School studies one a night | Every one is written by hand in code, by a Claude session |
| Doing the engineering | The worksheet (`core/specialist_work.py`): the model picks calculators, code computes and traces every number; calculators in `core/eng_calcs.py`; the bench (`core/eng_bench.py`) measures each model per discipline; `core/specialist_models.py` picks each one's model; a second model reviews (`core/specialist_review.py`) | A new discipline has no calculators or bench tasks until someone writes them |
| "Counts as added" | The plan's bar (section 7): charter and limits, caveat, starter questions, first calculators, its own bench tasks | Nothing checks the bar in code; there is no roster page |
| Knowing a need exists | `core/capability_gaps.py` (requests she couldn't do), the workspace's open questions, `who_knows()` | Nothing turns "no specialist covers this" into a proposal |
| Building code safely | The lab (`core/dev_lab.py`): a worktree, a coding model, the full suite, Zac's approval to merge; Forge's scaffold (`core/app_scaffold.py`) | The lab can't yet be pointed at "build this specialist" |
| Online | His own search engine (`core/online_lookup.py`, SearXNG, scrubbed words), her browser behind its safety gate (DEC-0117/0196), the UAL's Research and Verify, World Intelligence | What a specialist learns online isn't kept for offline use |
| Offline | The reference library (`core/reference_library_manager.py`, Kiwix ZIM packs), which Night School already cites | No way to make a pack from what was read online |
| Parallel agents | Her browser runs one tab of her own; the run record holds many runs; the stop halts all | One task at a time; nothing shows agents working |

## 3. Part 1: the Specialist Forge

A specialist goes through one pipeline whether Zac asks for it, a project needs it, or MIA notices a gap:

```
need ──▶ draft ──▶ research ──▶ calculators ──▶ bench ──▶ measure ──▶ Zac approves ──▶ on the roster
 (gap,     (charter,   (sources       (lab: code +     (tasks whose   (each local     (merge, like
  project,  limits,     online, kept   tests against    answers come   model, the      any lab
  his ask)  caveat)     as a pack)     published        from the       usual table)    change)
                                       worked examples) calculators)
                    ◀───────────── refine: evidence from use ─────────────────────────────┘
```

**Need.** Three ways in: he asks ("I need an acoustics specialist"); a project's workspace has questions no
specialist's words match (`who_knows()` finds none); a capability gap repeats. MIA *proposes* a specialist; she never
starts building one on her own (the same rule as teams, Q-54).

**Draft.** A local model writes the charter, limits, caveat, the words that route questions to it, and starter
questions, in the exact shape `Specialist` and its role need. Code checks the draft: every field present, the
department real, a caveat wherever the department is safety-critical, no tool that changes anything.

**Research (online, kept offline).** Section 4. The specialist's sources are found, read and kept as a pack, so the
calculators and the bench have something real to cite.

**Calculators.** Written in the lab by its coding model, one discipline's first few, each **tested against a worked
example taken from a cited source**, never against numbers the same model made up. A calculator whose example can't
be found isn't written: the specialist ships without it and says so.

**Bench.** Tasks whose correct answers come from the calculators (and so from the cited examples), including one with
a missing input (the right answer is a question). The bench is what makes "added" mean something.

**Measure.** The new tasks run on each local model (`tools.eng_bench`); `core/specialist_models.py` picks the model
or marks the discipline not passing.

**Approve.** The whole specialist arrives as one lab proposal: the diff, the sources, the bench table. Zac's
approval merges it; nothing reaches the running MIA before that. The registry stays code, so tests still check every
name it refers to, and nothing MIA reads can edit a charter, a limit or a tool list (DEC-0156: nothing she reads can
grant her anything).

**Refine.** Evidence from use, all of it already recorded somewhere:
- a worksheet answer he corrected, or one whose numbers didn't trace;
- the second model's doubts (`specialist_review.py`);
- bench tasks that fail; questions it couldn't route;
- his confirmed and withdrawn notes.

Refinements split by what they touch:
- **Without asking:** notes (still *derived* until he confirms), study priority, a re-run of the bench, the model
  choice.
- **Through the lab and his approval:** a new calculator, a new bench task, a change to the charter, limits, caveat
  or tools.

**Specializing.** A specialist that keeps getting one narrow kind of question can be split. Construction already
became carpentry, plumbing and electrical by hand. The Forge proposes a split the same way it proposes a new one, with
the questions that show the need.

**The roster page.** Built, in progress and planned specialists, each with its bench result and what's missing from
the "counts as added" bar. The bar becomes a check in code, so a specialist can't be called added with a calculator
or its bench missing.

## 4. Part 2: online and offline

The rule: **learn online, keep it offline, work offline.**

- **Online** uses only what exists and is already safe: his own search engine with scrubbed words, and her browser
  with its gate (outside text is information, never instructions; secret fields never typed; commits only by him).
  A specialist's research never carries his records out: only the discipline's own questions.
- **Kept**: each source read becomes a pack entry: the text, its address, the date read, the edition for a standard
  or code, and a content hash. The packs live in the reference library's folder beside the Kiwix packs and are
  searched the same way, so Night School and the worksheet cite them without knowing where they came from.
- **Offline**: a specialist answers from its calculators, its confirmed notes and its packs. When the network is
  back, MIA can re-check a pack's sources for new editions and say what changed. Nothing is fetched mid-answer
  without the network being there and allowed (the existing switch, `ual.online`).
- **Honest about age**: an answer that rests on a pack says when it was read. A code or standard says its edition,
  because a 2018 wiring table isn't the 2023 one.

## 5. Part 3: agents working in parallel, visibly

**What the video shows, honestly.** A computer has one real mouse. Videos with ten cursors are either several
browser sessions, each drawing its own cursor on its own page, or several virtual machines tiled on one screen. So:

**What MIA can do now (the Workroom).** Several of her browser agents at once, each in its own isolated browser
context (its own tab, cookies and run record), with a **drawn cursor** of its own colour on its page and a label
saying which specialist it is and what it's doing. A Workroom page shows them tiled, live (the browser's own
screencast, frames a second), with each one's current step underneath. One agent might read a datasheet, another
compare three suppliers' prices, a third check a standard, all for the same project.

**The real limits, measured not assumed:**
- **The graphics card is the bottleneck, not the browser.** The 24 GB card runs one 32B model at a time. Parallel
  agents share it: a small fast model (the bench shows which) drives clicks and reading; the bigger model plans and
  writes. Ollama can answer several requests at once; how many before it slows to a crawl is a measurement to make
  (W1 below).
- **Safety is per agent and stays the same:** every step through `browser_safety.classify()`; a purchase, send or
  sign-up is a proposal only he approves; "stop" stops all of them (each is a run).
- **Start read-only.** Research, reading and comparing first. Nothing in the Workroom fills a form until single-agent
  browsing has done so safely for a while.

**Later, on MIA OS:** desktop apps (CAD, a slicer, an IDE) in parallel need separate sessions, nested KWin sessions
or small virtual machines, each with its own cursor, tiled the same way. That belongs with Prompts 05 and 10, after
the session test (PoC 3).

## 6. Decisions for Zac

Each with its plain meaning and my recommendation.

| | Question | Recommended |
|---|---|---|
| **Q-59** | May MIA draft new specialists herself (from your ask, a project's need, or a gap she notices) and build each one in the lab, with every new specialist added only on your approval of the finished thing (its sources, calculators and bench results)? | Yes |
| **Q-60** | Refinements: notes, study priority, bench re-runs and model choice change without asking; new calculators, bench tasks and any change to a specialist's charter, limits, caveat or tools only on your approval. Agreed? | Yes |
| **Q-61** | May specialists research online through your own search engine and her browser, keeping what they read as offline packs (with the date and edition), never sending your records? | Yes |
| **Q-62** | Build the Workroom: up to four of her browser agents at once, read-only research to begin with, each with its own drawn cursor and label, shown live side by side? | Yes, after W1 measures how many your card can serve |

**Proposed (not approved): DEC-0199.** Specialists are added and refined through one pipeline (need, draft, research,
calculators, bench, measure, approve) that MIA can run herself in the lab. Every new specialist, calculator and
charter change reaches the running MIA only on Zac's approval. Online learning is kept as offline packs. Parallel
agents are isolated browser contexts with drawn cursors, read-only at first, each a run that "stop" stops.

## 7. Order of work

| Step | What | Needs |
|---|---|---|
| **F1** | The "counts as added" bar as a check in code, and the roster page | nothing |
| **F2** | Online to offline: a pack made from pages read (text, address, date, edition, hash), searched beside the Kiwix packs | Q-61 |
| **F3** | Drafting: a specialist's charter and the rest written by a local model, checked by code, shown to Zac | Q-59 |
| **F4** | The lab builds a specialist: calculators against cited worked examples, bench tasks, the bench run, one proposal | Q-59, F2, F3 |
| **F5** | Refinement proposals from evidence of use | Q-60 |
| **W1** | Measure: how many agents the card serves at once, with which model, at what speed | the PC |
| **W2** | The Workroom: parallel browser contexts, drawn cursors, the tiled live view, read-only | Q-62, W1 |
| **W3** | Desktop apps in parallel, on MIA OS | Prompt 10, PoC 3 |

F1 and W1 need no decision and can start now. The hoodie's specialists (acoustics, audio DSP, textiles, power) are
the natural first test of F3 and F4: build one by hand as today, then let the Forge build the next one, and compare.
