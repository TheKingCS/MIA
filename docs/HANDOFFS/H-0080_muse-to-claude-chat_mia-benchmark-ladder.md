# H-0080: MIA's education — a benchmark ladder for her intelligence
- From: muse · To: claude, chat (cc zac) · Date: 2026-11-06
- Related: DEC-0039, DEC-0050, DEC-0052, DEC-0058, DEC-0067, DEC-0068, DEC-0069, DEC-0070, DEC-0071, T-0007, T-0010, T-0011, T-0019; `tests/live_model_check.py`, `tools/conversation_check.py`. Draft decision text for DEC-0072 is in section 4 (PROPOSED — only Zac approves).

## Context

Zac's direction (2026-11-06, via muse): study how human intelligence is
measured, and build MIA to exceed those measures — pass school curriculums
and top-level intelligence tests with proven proficiency across skills, be
bilingual, be fluent in psychology, and reach "superhuman levels of
understanding" in service of assisting the user. He also wants hours of
simulated use to test and grow her once she is built out.

Today her quality is checked by point tests (the 213-question tool check,
the conversation corpus, `tests/live_model_check.py` PERSON_CASES), but
there is no curriculum, no proficiency ladder, and no durable record of
what she is provably good at. This proposal adds exactly that: an
education system for MIA, run like her own gamified progression —
subject tracks, levels, exams — with every result recorded honestly.

Muse's framing, for the record: tests are the floor, not the ceiling.
Passing is table stakes; the differentiators are reliability (right
every time, not on a good day), breadth under one roof, and applying
knowledge to one specific person's life. The ladder exists to prove
capability and expose weakness, not to decorate her with scores.

## What's needed

### 1. The ladder (five tiers, in order)

1. **Foundations** — literacy, numeracy, reasoning basics.
2. **Secondary** — school curricula: algebra and geometry, the sciences,
   history and civics, language arts (exit standard: strong final-exam /
   AP-level performance where a public instrument exists).
3. **Undergraduate breadth** — survey-level proficiency across the major
   fields.
4. **Professional depth** — the tracks in section 2 taken to working
   proficiency, psychology first among equals.
5. **Frontier** — intelligence-test-style batteries (pattern reasoning,
   working memory, verbal comprehension), honestly labelled as
   adaptations: no clinical administration exists for a program, and no
   "IQ score" is ever claimed without its instrument and conditions
   attached.

### 2. Subject tracks

- **Core school tracks:** mathematics, natural sciences, language arts,
  history / civics.
- **Psychology** (Zac named this one first): perception, cognition,
  development, personality, social, abnormal — and its applied edge:
  how understanding people changes how she phrases, times and frames
  what she says (DEC-0014 always: she does not punish the user for
  being human).
- **Languages:** bilingual is the bar. The second language is Zac's
  pick (open decision, section 5); proficiency proven both directions,
  comprehension and production, spoken and written.
- **Applied MIA tracks:** the domains she actually serves — money and
  household finance, health and training literacy, practical law and
  documents literacy, home / homestead / trades knowledge. These matter
  most to the user and are tested against real task performance, not
  only written exams.

### 3. Proving and recording (extends what exists — no new system)

- The harness extends the existing check patterns
  (`tests/live_model_check.py`, `tools/conversation_check.py`) into a
  benchmark suite; instruments are public or licensed, versioned, and
  named in every result.
- Every run records: instrument + version, date, the exact model and
  where it ran (the PC's local model first; cloud models only when a
  device level allows, DEC-0022), score against a stated pass bar, and
  the raw output. Results land in the shared development history
  (DEC-0068, DEC-0071) and show on the dev dashboard (DEC-0070) as her
  **transcript**: track, level, proven when, by what instrument.
- Failures become `work/tasks/` items like any other work; a failed run
  stays in the record (DEC-0071 — disagreements and failures are
  resolved, never dropped). Re-tests after a change prove the change.
- **Practicum:** Zac's simulated-use hours are the applied complement —
  exams plus practicum, the way medicine pairs boards with rounds.
  Simulated days (bills coming due, training logged, missions offered,
  awkward questions asked) run against the same record; nothing
  simulated is ever reported as real use.
- Benchmark work runs at the Experiment permission tier (DEC-0069);
  results never change production by themselves — improvements are
  proposals to Zac (DEC-0058).

### 4. Draft decision for Zac (DEC-0072, PROPOSED)

> MIA gets an education: a five-tier benchmark ladder with subject
> tracks (psychology and a second language as first-class tracks),
> proven by named, versioned instruments and recorded on a transcript
> in her development history. Passing is the floor; reliability,
> breadth and applied judgment for the user are the standard. Honesty
> rules: adaptations are labelled, no bare IQ claims, failures stay in
> the record, and nothing simulated is reported as real.

### 5. What each of us is asked for

- **Claude:** feasibility pass — instrument sources and licensing, the
  harness design on the existing check code, where runs execute and
  what they cost, and a first task breakdown in `work/tasks/`.
  Objections go on the record, per DEC-0071.
- **Chat:** the vision check — is curriculum-as-progression still MIA?
  Which measures actually matter, and which are vanity metrics we
  should refuse?
- **Zac:** three decisions — (a) approve, amend or reject DEC-0072;
  (b) pick the second language; (c) pick the first two tracks to build
  (muse suggests Psychology + Applied Money, but that is muse's
  suggestion only).

## Constraints

- DEC-0002: no real personal data in instruments, results or examples —
  placeholders only. Simulated users are invented, never Zac-derived.
- DEC-0050 stands: personal-data facts still come only from the user's
  own data; a psychology-fluent MIA does not invent insight about a
  person.
- Honesty of measurement is the whole point: no cherry-picked runs, no
  rounded-up scores, no silent re-takes that erase a fail.
- Guardrail check (DEC-0008), briefly: she partly supports this today
  (point checks exist — Q1/Q2); the ladder, proficiency levels and
  transcript are genuinely missing, not merely unshown (Q3). Engine
  first, UI later (Q4): harness and records in the engine and `work/`;
  the transcript surface is a dev-dashboard view, and any user-facing
  Report Card look pass is muse's when it is built. No duplication
  (Q5): extends the existing checks and `work/` records. Not Life
  State (Q6) and no user life events (Q7): her education record is
  development data. No new Life State links (Q8) and no `/api/state`
  exposure (Q9) — admin dashboard only. Scores are REAL measurements
  of a named model under named conditions; any test-equivalent phrasing
  is DERIVED and labelled; simulated use is SIMULATED (Q10).

## Acceptance criteria

- Claude replies with the feasibility pass and a task breakdown, or
  objections recorded in this thread.
- Chat's vision verdict reaches the repo (via Zac).
- Zac approves, amends or rejects DEC-0072; on approval it is filed in
  `docs/DECISIONS.md` and the first two tracks become scheduled work.
