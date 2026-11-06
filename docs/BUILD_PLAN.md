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
2. ✅ **The development loops that need running** (`core/dev_checks.py`): the weekly full suite on the committed
   code against `work/known_failures.json` (`dev.suite`, `dev.suite_time`), reverts per merge (`dev.reverts`), the
   dependency audit (`dev.vulnerable` against osv.dev, `dev.outdated` against PyPI). Heavy loops run from Night
   School and `tools.work loops --run`, never in the app's check. First run: `cryptography` 47 had three HIGH
   advisories, raised to 50.0.2 (T-0048).
3. ✅ **The remaining usage loops**: built 2026-11-06: `answers.numbers` (a number she hadn't looked up, so the
   plain facts were shown), `memory.quality` (memories edited or deleted within 14 days), `gate.saturation`,
   `gate.unwelcome`, `creations.held`, `data.recovered`, and T-0047's six (`actions.*`, `email.*`, `gate.dismissed`,
   `gate.expired`), and (2026-11-07) `glasses.voice` (turns now traced by device) and `phone.link` (when a linked
   phone last reached the PC, kept by `core/phone_link.py`) and `creations.maker` (designs that missed their checks
   the first time), and (2026-11-06, later) `vault.coverage` (photos over a week old still only on the phone, from
   the vault's own list), `checks.dismissed`, `missions.recurring`, `screens.broken`, `dev.lab` and `notes.offers`:
   every process now has a loop or a reason (228 of 257 covered, 23 declined, 6 to do with their why).
4. 🔨 **Corrections in every area** (`core/corrections.py`, built 2026-11-06): MIA's changes (actions she proposed
   that were approved, her Assistant tools' changes) are watched for 3 days; the person undoing one, or editing or
   deleting something of the same kind (the same record when both name its id), corrects her once;
   `corrections.all` and one loop per area (money, kitchen, workouts, missions, calendar, maintenance, inbox,
   memories, creations, home, tasks, and since 2026-11-06 people, music, files). Built 2026-11-06: edits on the
   desktop's Qt screens (recipes, meals, upkeep tasks, people: `corrections.screen_edit`) and her tools matched by
   what they change. Not yet: Plaid re-categorizations learned as rules (waits on Zac's Plaid work). Built:
   `loop.prediction` (the Loop's planned work days against the days worked) and `inbox.reading` (fields of a read
   document the person corrected when filing it).
5. ✅ **The weekly benchmarks on a schedule** (`core/benchmarks.py`, `tools/weekly_bench.py`, 2026-11-06): Night
   School runs the 112-question benchmark, the conversation corpus (glasses and phone) and the routing audit once a
   week on this PC; code grades each against the week before (route worse, newly flagged, newly slow) and keeps
   grades only, never an answer. Loops: `answers.benchmark` (questions that fell: a task naming them),
   `answers.benchmark_clean`, `answers.corpus`, `answers.routing`. The shadow attempt is Night School's own. The
   phone's model check stays in CI's Model check workflow.
6. ✅ **Loops feed missions** (2026-11-06): the standing mission M-0001, "Keep MIA healthy", works every task the
   loops open (`source: loop:`) and Night School drafts (`source: night:`) through the usual runner, lab and
   reviewers, a week's budget at a time (`takes` in `core/work_runner.py`; Zac starts it: `python -m tools.work
   mission start M-0001`). MIA's weekly self-report (`core/self_report.py`): Sundays, to the PC's owner, through
   the gate: loops that got better or slipped, what she fixed, what she's working on, Night School's week.

### Phase B: The fabric (the Interconnection Architecture, DEC-0095)

7. 🔨 **The module contract** (first piece, 2026-11-07: the event catalogue, `docs/EVENTS.md` from
   `core/event_catalog.py`, kept current by a test, with no listener waiting on an event nothing sends; the rest
   waits on Zac's full Interconnection doc) (`docs/MODULE_CONTRACT.md`, a contract test): each module declares the events it
   emits and consumes, the life-event types it records, its links, its read sources for ACAF, its tools and its
   child rules; the event catalogue generated from code; a test fails a module that breaks it. The one layering
   break the map found (T-0042) goes first. 🧑 *The rest of the Interconnection Architecture (it was cut off at
   section 3) comes before this is final.*
8. 🔨 **Cross-domain reasoning** (2026-11-06): a question that joins domains gathers the other plans it names onto one
   sheet (`composed_with()` in `core/question_plans.py`); two cross-domain plans, `afford` (the freedom plan worked
   out twice, with and without the purchase, once or monthly) and `slipped` (history, deadlines, open loops, what
   she noticed); every plan answer is marked sure, likely or unsure from its sheet, told to the model, and noted
   (`core/calibration.py`) so `answers.calibration` checks sure answers are rated up more than the rest. Next in
   it, built 2026-11-07: four more cross-domain plans (projects, habits, priorities, resources: 11 benchmark
   questions moved from the model alone to a plan) and calibration against outcomes (projected debt-free and
   freedom dates kept and checked a month after they come, `answers.projections`). Built 2026-11-06: DEC-0054's
   notes (`core/life_notes.py`: promises, decisions, ideas and goals set aside, kept on a yes) and seven plans
   over them and the records (recall, person, patterns, discussed, returns, time, held back): the routing audit
   answers 84 of 112 benchmark questions by a plan; the 16 left to the model are research, how-to and coaching.

### Phase C: The gaps in her intelligence

9. ✅ **Self-enablement** (`core/capability_gaps.py`, 2026-11-06): requests no tool matched are grouped into gaps, each
   with what it would take, worked out in code (a tucked-away app, a screen or workflow she can make, a sense or
   device she lacks, or new code); a gap asked twice is offered through the gate (once a fortnight). "Bring it
   back" shows the app; "build it" opens a task (`source: gap:<id>`) that names the gap, never the person's
   words, which stay in their folder (`python -m tools.gaps show <id>` on this PC). Screens and workflows point
   to Make Something. Loop: `gaps.repeated`.
10. ✅ **Seasons of memory** (`core/seasons.py`, 2026-11-06): a month or a year against the one before, in code from
    the history and memories (what grew, what's new, what stopped, the numbers, money, what she came to know, the
    biggest moments); the `seasons` question plan puts it on a sheet for the model to phrase ("what changed this
    month?", "how was my year?", "how did October go?"); each closed month and year is kept once in the person's
    folder for the Chronicle's yearly edition (which isn't built yet: step 17). No money for a child.
11. ✅ **The Operating Journal** (DEC-0097; `core/operating_journal.py`, 2026-11-06): the person's lines (values,
    priorities, the ideal day and week, rules), each read by code for what the records can check (workouts, meals,
    people, tasks, missions, upkeep a week; spending in a category a month) or else self-rated 1 to 5 each week;
    how they did as plain numbers by week, never a judgment (the `operating` plan: "am I living how I said I want
    to?"); talked to with "add to my operating journal: ..." and "rate early mornings 4"; on Sundays one question
    for the lines only they can rate; `journal.pace` is theirs to see, never a task. Not yet: a screen for it
    (muse's look). 🧑 *Zac writes the first one with MIA.*
12. ✅ **Recreation in the health cluster** (DEC-0098; `core/recreation.py`, 2026-11-06): games and sports logged by
    voice ("played pickleball for an hour with Sam, it was hard") or the `play.log` action: what, with whom, how
    long, how hard (1 to 10 or words); training load by session-RPE (minutes × effort) beside workouts' minutes,
    in the week review; skill XP by the sport; a `played` life event for the history, the seasons, the Operating
    Journal ("play pickleball twice a week") and the Chronicle's "Week Of Play"; `recreation.load` watches the
    week against the four before (past 1.5: easing off helps), theirs to see. Not yet: a screen (muse's look).

### Phase D: New capabilities

13. ✅ **Good News Radio** (DEC-0096; `core/good_news.py`, `tools/good_news.py`, 2026-11-06): once a day, when a
    person switched it on (Zac has: "turn on good news radio"), the PC reads 16 public feeds Zac approved: primary
    sources (NASA, NIH, WHO, Nature, MIT News, Our World in Data), science journalism (BBC, NPR, The Conversation,
    ScienceDaily press releases, labelled) and solutions journalism (Positive News, Reasons to be Cheerful,
    Anthropocene, Canary Media); nothing about anyone is sent. Good news is judged in code (a topic, the progress in
    the headline, no harm words; picture-of-the-day posts and roundups skipped); each story says how it's known
    (confirmed by two outlets, from the source itself, or one outlet), keeps its caveats (animals or the lab, an
    early result, could not does, a press release) and its links; two a topic and two an outlet. Four
    personalities by the hour or asked for (Sunny, Spark, Still, Night Owl), each a Kokoro voice, each episode a
    track in the music library (the last week kept). "What's the good news?", "good news, the calm one", "that
    story was misleading" (`news.misleading`; a source called misleading twice is dropped). Not yet: the model
    phrasing the script (it's made in code), a screen.
14. 🔨 **Maps and comms, inspired by defense systems** (DEC-0099; `docs/MAPS_AND_COMMS.md`): built 2026-11-06: MGRS
    grid references in code (`core/geo_grid.py`, checked against pyproj and the mgrs package), waypoints by grid by
    voice, and MIA's places as a TAK data package of Cursor on Target events and KML (`core/tak.py`,
    `python -m tools.tak_export`) for ATAK-CIV; tracks from GPX (`core/gps_tracks.py`, `python -m tools.tracks add`;
    distance, climb, moving time, grids; lines in the TAK package; "how far was my last hike?"). Next: CoT on the
    local network by approval (built 2026-11-07: `map.tak_share`, one hop, never a child's), vector
    offline maps (PMTiles), Meshtastic mesh radios (needs hardware), the shared picture of people by consent and
    sensors.
15. 🔨 **Sight** (`core/sight.py`, 2026-11-06): a photo and a question, answered on this PC by a local vision model
    (Qwen2.5-VL 7B in Ollama, `sight.model`): what is this, read this label (Tesseract first, its words exact),
    inspect this part (condition, wear, what to check by hand); `POST /api/sight` for the glasses, the phone and
    the PC; authorized one photo at a time, never a running camera; never identifies a person (refused in code);
    the photo isn't kept, only each look's kind and timing (`sight.failed`). Tried for real: a photo described,
    a label read exactly (1.4 s warm, about 28 s for the model's first load). Not yet: the glasses' and the
    phone's Look button (Kotlin).
16. 🔨 **The council from the phone** (2026-11-06): `web/council.html`, the same chat as the dev window, for the PC's
    owner only (`GET`/`POST /api/council`, 403 for anyone else; the sidebar shows it to the owner alone): the
    latest messages, who's ready, Reply, @name to ask one member; a message starts the council's turn in the
    background, within its budget. Not yet: the glasses' speaker card and each member's voice on the phone
    (T-0035). 🧑 *Testing on the real glasses.*
17. 🔨 **The Chronicles' weekly issue** (`core/chronicle_issue.py`, `tools/chronicle_issue.py`, 2026-11-06): on Sundays,
    from approved series events no issue has told (oldest first), a script made in code (each panel's caption
    names its event; real names become the series' own), lines from the local model in each character's voice,
    the Story Bible's five rules checked in code (an issue with a problem stays a draft and says why), panels by
    the local image model in its own environment (`data/chronicles/`, off the repo); Zac approves each issue,
    which marks its events as told and lists it in `docs/chronicles/issues.md`. Tried end to end on sample
    events: checked, in character, panels drawn (storyboard quality). Not yet: consistent characters and a
    bigger image model (T-0036). 🧑 *Zac approves each issue.*

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
