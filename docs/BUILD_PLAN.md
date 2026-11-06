# MIA Build Plan

*Claude, 2026-11-06, for Zac: "Lets create a detailed implementation checklist for all the improvements and
functions we have covered this session and then start from step 1." Built from H-0083 (the master overview, the
Interconnection Architecture, Good News Radio, Zac's notes) and everything decided since 2026-11-03 (DEC-0068 to
DEC-0099). The checklist is the order of work; `work/tasks/` holds each step as tasks as it starts.*

Legend: ✅ done · 🔨 in progress · ⬜ to do · 🧑 needs Zac (the PC, the glasses, a choice)

---

## Part 1: What her intelligence layer and modules are missing

Measured against the master overview and the Interconnection Architecture, these are the gaps, most important
first. Each is a step below.

1. **Nothing closes the loop.** MIA measures herself in a dozen places (the Fix-It Log, traces, ratings, the
   benchmark, the corpus, the ledger) but nothing watches the numbers over time, notices a slide, and turns it into
   work. Without that, she doesn't get better by herself. *(Steps 1 to 6.)*
2. **No module contract.** Each module integrates its own way. The Interconnection Architecture asks for typed
   events, first-class links and live capability awareness; there's no written contract a module is checked
   against, and no catalogue of the events modules emit and consume. *(Step 7.)*
3. **Cross-domain reasoning is shallow.** Question plans answer known questions well; a new cross-domain question
   ("can I afford the coop and still hit my freedom date?") falls to the model. She needs scenario tests across
   domains and a planner that composes plans. *(Step 8.)*
4. **She doesn't know how Zac actually lives versus how he means to.** Goals and routines are scattered; nothing
   compares intent with behaviour. *(Step 11: the Operating Journal.)*
5. **"I can't do that" is a dead end.** A request no tool matched is logged and dropped; the overview's
   self-enablement (what's missing, can she enable it, a proposal) isn't built. *(Step 9.)*
6. **No sight.** The glasses have a camera and MIA has no local vision model wired in. *(Step 15.)*
7. **Calibration.** Answers don't carry how sure she is in a way that's checked later. *(Step 8.)*
8. **Long-term memory is lists, not understanding.** Memories and history aren't summarized into what changed
   over a season or a year. *(Step 10.)*

## Part 2: The checklist

### Phase 0: Done this session (for the record)

- ✅ The development platform: tasks, history, agents, loop, lab, two reviewers, objections, lessons (DEC-0068 to 0071)
- ✅ The dev window, the council chat, the floor's budgets, voices, missions and the runner (DEC-0076 to 0082)
- ✅ Knowledge vault, MIA's own coder, shadow attempts, the independence ledger, her architecture map (DEC-0073 to 0078)
- ✅ The Chronicles archive and the Story Bible (DEC-0084, 0085, 0087)
- ✅ ACAF: screens, history sources, workflows, CSV import, usage observed (DEC-0088 to 0093)
- ✅ Council Mode, engine side (T-0035, part); the local image model runs on the card (T-0036, part)
- 🧑 Approve T-0019; `codex login`, `gh auth login`, Copilot `/login`; pick voices; try Make Something

### Phase A: Close the loops (DEC-0094; `docs/IMPROVEMENT_LOOPS.md`)

1. ✅ **The loop registry and runner** (`core/loops.py`): loops declared with their signal, floor, cadence and
   scope; measured into a history (the PC's in `data/dev/`, a person's in their folder); judged against the floor
   and their own trend; a loop below its floor opens one task (`source: loop:<id>`, numbers only); the dev window's
   **Her loops** panel; `tools.work loops` to run them now; the app's daily check runs them.
1a. ✅ **Night School and loop coverage** (DEC-0100, DEC-0101; `docs/NIGHT_SCHOOL.md`): every night she
   studies the next step of this plan with her teacher (exercises with a test that fails first, graded by code),
   makes one attempt at real work, and drafts loops for processes nobody watches yet; every process in MIA is
   covered, declined with a reason, or on the to-do list, and a test holds new ones to it.
2. ⬜ **The development loops that need running**: the weekly full suite against the known failures, reverts per
   merge, the dependency audit.
3. ⬜ **The remaining usage loops**: numbers she didn't look up, memory quality, the gate's unwelcome kinds and
   saturation, maker failures, held creations, data recovery, vault coverage, glasses voice, phone link.
4. ⬜ **Corrections in every area**: an action MIA proposed that the person undid or re-edited within 3 days,
   counted by area; Plaid re-categorizations learned as rules; OCR field corrections; the Loop's predictions
   against what happened.
5. ⬜ **The weekly benchmarks on a schedule**: the 112-question benchmark, the corpus, the routing audit, the
   phone model check, a shadow attempt, run by the runner when the PC is idle; each question that falls is a task.
6. ⬜ **Loops feed missions**: a standing "Keep MIA healthy" mission whose tasks are the loops' tasks; MIA's
   weekly self-report through the gate ("what got better, what I'm working on").

### Phase B: The fabric (the Interconnection Architecture, DEC-0095)

7. ⬜ **The module contract** (`docs/MODULE_CONTRACT.md`, a contract test): each module declares the events it
   emits and consumes, the life-event types it records, its links, its read sources for ACAF, its tools and its
   child rules; the event catalogue generated from code; a test fails a module that breaks it. The one layering
   break the map found (T-0042) goes first. 🧑 *The rest of the Interconnection Architecture (it was cut off at
   section 3) comes before this is final.*
8. ⬜ **Cross-domain reasoning**: scenario tests across domains ("can I afford X and still hit my freedom date",
   "what slipped this week and why"); a planner that composes question plans; answers that say how sure they are,
   checked later by the `answers.calibration` loop.

### Phase C: The gaps in her intelligence

9. ⬜ **Self-enablement**: a request no tool matched becomes a capability gap with what it would need (data, a tool,
   a device, a permission); repeated gaps become a proposal (an ACAF creation when it's a screen or workflow, a lab
   task when it's code).
10. ⬜ **Seasons of memory**: what changed this month and this year, summarized from history in code, phrased by
    the model; the Chronicle's yearly edition grows from it.
11. ⬜ **The Operating Journal** (DEC-0097): a template, filled by talking to MIA or on a screen, for how Zac means
    to operate (values, priorities, the ideal day and week, rules he keeps) and a regular entry for how he did;
    MIA compares intent with what the records show (the Loop, missions, money, workouts), and the gap becomes a
    loop he sees, never a judgment. 🧑 *Zac writes the first one with MIA.*
12. ⬜ **Recreation in the health cluster** (DEC-0098): sports and play logged as activities (what, with whom,
    how long, how hard), counting toward training load, skills and the Chronicle; voice-loggable ("played
    pickleball for an hour").

### Phase D: New capabilities

13. ⬜ **Good News Radio** (DEC-0096): sources (an allowlist of credible outlets and science, health, energy and
    civic feeds, fetched only when switched on, DEC-0053); stories chosen by code and the local model, each claim
    checked against a second source and linked; nothing hidden that matters; a daily episode written in the voice
    of a chosen personality (an energetic morning host, a late-night talk show, calm, curious) and spoken with
    Kokoro voices; played on the PC, the phone and the glasses; the personality follows the mood asked for. Its
    loop: stories later found misleading, skips, ratings by personality.
14. ⬜ **Maps and comms, inspired by defense systems** (DEC-0099): research first (Part 3), then an offline map of
    the property and trails with MGRS grid references, waypoints and tracks; a shared picture of places, people (by
    consent) and sensors, Lattice-style; and later mesh messaging that works without cell service (Meshtastic
    LoRa radios), speaking open civilian standards (Cursor on Target, ATAK-CIV) so a TAK app can see MIA's
    picture.
15. ⬜ **Sight**: a local vision model through the glasses' camera and the phone (what is this, read this label,
    inspect this part), within inspection's permission levels.
16. ⬜ **The council from the phone**: an owner-only Council screen in MIA's web and phone app; the glasses' speaker
    card and each member's voice on the phone (T-0035). 🧑 *Testing on the real glasses.*
17. ⬜ **The Chronicles' weekly issue**: scripts from approved events, continuity checks in code, panels from the
    local image model with a bigger model and consistent characters (T-0036). 🧑 *Zac approves each issue.*

### Phase E: The rest already queued

18. ⬜ T-0042 (the Skills module reaching into Missions), T-0040 (JSON imports, diagnostics), T-0041 (blueprint
    proposals once there's use), T-0008 (GitHub Issues mirror, after `gh auth login`), the self-knowledge map
    (T-0007), the glasses' rating (T-0010), User Sync by voice (T-0014).

## Part 3: Research to do

| Topic | Questions | For step |
|---|---|---|
| Defense-derived mapping and comms | How Anduril's Lattice fuses sensors into one picture; ATAK-CIV and the Cursor on Target format; MGRS; offline vector tiles (OpenStreetMap, protomaps); Meshtastic and LoRa mesh range and licensing; what's open and civilian | 14 |
| Local vision models | Which run on the 7900 XTX (DirectML or Ollama: Qwen2.5-VL, LLaVA), speed and accuracy on labels, parts, plants | 15 |
| Credible good-news sources | Outlets and feeds with good track records (science, medicine, energy, environment, civic); how to check a claim against a second source cheaply | 13 |
| Evaluation of small models | How to measure tool choice, faithfulness and calibration on 14B models; what fine-tuning on Zac's ratings would need | 5, 8 |
| Self-improving agent practice | What's known to work for agents learning from feedback without drifting (eval-gated changes, held-out tests) | 1 to 6 |
| Character consistency in local image models | Reference conditioning (IP-Adapter) on DirectML; style training | 17 |

## Part 4: Testing that keeps her honest

| When | What |
|---|---|
| Every change | the full suite in the lab; two reviews; Zac's approval (exists) |
| Every day | every free loop; the glasses' and phone's health; the gate's log |
| Every week | the benchmark, the corpus, the routing audit, the phone model check, a shadow attempt, the dependency audit |
| Every month | Zac reviews the loops' floors, the ledger's stages, the Chronicles waiting, what to retire |
| Every new feature | its loop is part of its definition of done (DEC-0094) |
