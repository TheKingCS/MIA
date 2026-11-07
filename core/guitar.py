"""
core.guitar
=============

Guitar, the first program on MIA's learning paths (DEC-0111, DEC-0112; Zac, 2026-11-07: "I want to learn guitar and
would like for MIA to be able to help teach me as well as track my progress and assign missions like homework ...
being able to verify and test a user's skills just like it would do for itself").

The method (understand the desire, plan the steps, teach, log practice, homework missions, statistics, verify,
next stage) is core/paths.py's, the same for every path. This file is guitar's content and its ear:

- **The program** (`STAGES`, registered as `PROGRAM`): five stages, from holding the guitar to lead basics, each
  with lessons (steps, why, what to watch for) and skill checks. Chord shapes (`CHORDS`) are verified in a test to
  make exactly their chord's notes, and each lesson about chords is taught with its shapes (`_extra()`).
- **Its verifiers**, the checks MIA hears from a WAV recording (core/guitar_ear.py): `heard_chord` (every note of
  the chord rang, nothing stray did) and `heard_tuning` (one string at a time; passed when all six are in tune on
  the same day). The rest are counted (one-minute changes, a tempo held) or said.

Its XP goes to the Music skill.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from core.paths import Check, Lesson, Program, Stage, register

SKILL = "music"  # her skill tree's Music skill (data/skill_definitions.json)
MAX_RECORDING = 8 * 1024 * 1024  # bytes: a few seconds of WAV is plenty


# ------------------------------------------------------------------ the program

@dataclass(frozen=True)
class Chord:
    """One chord shape: its name, the fret on each string from the low E (6) to the high E (1), x for muted and 0
    for open, the finger on each (1 index to 4 little), and the notes in it."""
    name: str
    frets: str
    fingers: str
    notes: tuple[str, ...]


CHORDS: dict[str, Chord] = {c.name: c for c in (
    Chord("Em", "022000", "023000", ("E", "G", "B")),
    Chord("Am", "x02210", "x02310", ("A", "C", "E")),
    Chord("C", "x32010", "x32010", ("C", "E", "G")),
    Chord("G", "320003", "210003", ("G", "B", "D")),
    Chord("D", "xx0232", "xx0132", ("D", "F#", "A")),
    Chord("E", "022100", "023100", ("E", "G#", "B")),
    Chord("A", "x02220", "x01230", ("A", "C#", "E")),
    Chord("Dm", "xx0231", "xx0231", ("D", "F", "A")),
    Chord("F", "133211", "134211", ("F", "A", "C")),
    Chord("Bm", "x24432", "x13421", ("B", "D", "F#")),
)}


STAGES: tuple[Stage, ...] = (
    Stage(1, "First sounds", "holding the guitar, tuning it, two chords and steady strumming", (
        Lesson("hold_tune", "Holding it and tuning it", (
            "Sit with the guitar's waist on your right leg (left if you play left-handed), the neck pointing a little "
            "up, your back straight.",
            "The strings, thickest to thinnest, are E A D G B E: 6 is the low E, 1 the high E. Remember them as "
            "\"Eddie Ate Dynamite, Good Bye Eddie\".",
            "Tune every string before you play, every time: pluck it, let MIA hear it (or use any tuner), and turn "
            "its peg until it's in tune. Tune up to the note, not down to it: it holds better.",
            "Press a string just behind a fret (on the side nearer the body), with your fingertip, not the pad."),
            "Practising out of tune teaches your ear the wrong sounds; a guitar in tune makes every chord sound right "
            "the moment your fingers are right.",
            ("Pressing in the middle between frets (buzz) or on top of the fret (dead note).",
             "Squeezing with the thumb: it should rest behind the neck, relaxed.")),
        Lesson("em_am", "Your first chords: E minor and A minor", (
            "E minor: second finger on the 2nd fret of the A string (5), third finger on the 2nd fret of the D "
            "string (4); strum all six strings.",
            "A minor: the same two fingers move down one string each (2nd fret of D and G), and your first finger "
            "goes on the 1st fret of the B string (2); strum from the A string down, not the low E.",
            "Play each one string at a time, slowly: every string should ring. Fix any that doesn't before you strum.",
            "Then switch between them: look at where the fingers go next before you lift them."),
            "These two share a shape: moving between them is the first chord change, and the same move comes back "
            "in dozens of songs.",
            ("A finger leaning on the string below it and muting it: arch your fingers, tips straight down.",
             "Strumming the low E in A minor: it isn't part of the chord."), ("Em", "Am")),
        Lesson("strum_down", "Strumming down, in time", (
            "Set a metronome to 60 beats a minute (MIA can count it, or any metronome app).",
            "Strum down once on every beat: four strums, then four more, without stopping.",
            "Move from the wrist and elbow, loosely; brush the strings, don't dig in.",
            "Keep going when a chord sounds wrong: the beat matters more than the chord right now."),
            "Rhythm is what makes chords into music. A steady down strum is what every pattern later is built on.",
            ("Speeding up or stopping when a change is hard: slow the change, never the beat.",), ()),
    ), (
        Check("tuned", "Tune all six strings; let MIA hear each one", "heard_tuning"),
        Check("em_clean", "Play E minor so every note rings", "heard_chord", about="Em"),
        Check("am_clean", "Play A minor so every note rings", "heard_chord", about="Am"),
        Check("changes_em_am", "One-minute changes: E minor to A minor and back, as many as you can in a minute",
              "counted", passes_at=20, unit="changes a minute"),
        Check("strum_60", "Strum down on every beat at 60 bpm for one minute without stopping", "said"),
    )),
    Stage(2, "The open chords", "the five open chords most songs use", (
        Lesson("c_g", "C and G", (
            "C: third finger 3rd fret of the A string, second finger 2nd fret of the D string, first finger 1st fret "
            "of the B string; strum from the A string.",
            "G: second finger 3rd fret of the low E, first finger 2nd fret of the A string, third (or fourth) finger "
            "3rd fret of the high E; strum all six.",
            "Play each string by string until all ring; then one-minute changes between them."),
            "G and C are the two chords you'll play most: together with D they make thousands of songs.",
            ("In C, the first finger touching the high E and muting it.",), ("C", "G")),
        Lesson("d_e_a", "D, E and A", (
            "D: first finger 2nd fret of the G string, third finger 3rd fret of the B string, second finger 2nd fret "
            "of the high E; strum only the top four strings.",
            "E: like E minor, with your first finger added on the 1st fret of the G string.",
            "A: three fingers side by side on the 2nd fret of the D, G and B strings; strum from the A string.",
            "Practise the changes that share fingers first: E minor to E, then A to D."),
            "With these, the open chords are complete: every song in the next stage uses only them.",
            ("Strumming the low strings in D: it muddies the chord.",
             "In A, three fingers crowding one fret: angle them, or try 2-3-4 instead of 1-2-3."), ("D", "E", "A")),
        Lesson("strum_pattern", "The strumming pattern: down, down-up, up-down-up", (
            "Count eight to a bar: 1 and 2 and 3 and 4 and. Down strums land on the numbers, up strums on the ands.",
            "The pattern: down (1), down (2), up (and), up (and of 3), down (4), up (and). Miss the strum on 3 but "
            "keep your hand moving.",
            "Keep your hand moving down and up all the time, like a pendulum; strum or miss the strings, never stop.",
            "Start at 60 bpm on one chord, then two."),
            "This one pattern fits most pop and folk songs, and keeping the hand moving is what keeps time.",
            ("Stopping the hand on the missed strum: it's what throws the rhythm off.",)),
    ), (
        Check("c_clean", "Play C so every note rings", "heard_chord", about="C"),
        Check("g_clean", "Play G so every note rings", "heard_chord", about="G"),
        Check("d_clean", "Play D so every note rings", "heard_chord", about="D"),
        Check("changes_g_c", "One-minute changes: G to C and back", "counted", passes_at=30, unit="changes a minute"),
        Check("changes_d_a", "One-minute changes: D to A and back", "counted", passes_at=30, unit="changes a minute"),
        Check("pattern_70", "The strumming pattern on one chord at 70 bpm for one minute", "counted", passes_at=70,
              unit="bpm"),
    )),
    Stage(3, "Rhythm and first songs", "changing on the beat and playing songs through", (
        Lesson("progression", "G, E minor, C, D: the four-chord song", (
            "Four beats on each: G, E minor, C, D, round and round.",
            "Change on beat 1, every time: if you're late, let the last strum before the change go (strum open "
            "strings) and keep the beat.",
            "Use the pattern from stage 2 once the changes land on time with down strums."),
            "This progression is the backbone of a huge number of songs: when it flows, you can play them.",
            ("Waiting for the fingers before strumming: the beat goes on without them.",), ("G", "Em", "C", "D")),
        Lesson("song", "A whole song, start to finish", (
            "Pick a song you like that uses only open chords (search its name with \"chords\").",
            "Learn it a section at a time: verse, then chorus.",
            "Play it through at a slow tempo, without stopping, even through mistakes.",
            "Record yourself once a week: you'll hear what to fix, and how far you've come."),
            "Finishing songs is what keeps people playing; a song played through badly teaches more than a perfect "
            "verse played alone.", ()),
    ), (
        Check("changes_g_d", "One-minute changes: G to D and back", "counted", passes_at=40, unit="changes a minute"),
        Check("progression_80", "G, Em, C, D at 80 bpm for two minutes, changing on the beat", "counted", passes_at=80,
              unit="bpm"),
        Check("song_through", "Play one whole song through without stopping", "said"),
    )),
    Stage(4, "Barre chords and power chords", "chords that move up the neck", (
        Lesson("power", "Power chords", (
            "Root on the low E string with your first finger, then your third finger two frets up on the A string "
            "(and the fourth on the D string the same fret, if you like). Play only those strings.",
            "Slide the same shape anywhere: the note under your first finger names the chord (3rd fret is G5).",
            "Mute the other strings by letting your fingers touch them lightly."),
            "Power chords are rock and punk's backbone, and the first chord you can move anywhere.", ()),
        Lesson("barre_f", "The F barre chord", (
            "Lay your first finger flat across all six strings at the 1st fret, close to the fret, the bony side "
            "rolled a little toward the headstock.",
            "Make an E shape with the other three fingers in front of it (3rd fret A and D strings, 2nd fret G).",
            "Pull back with your arm rather than squeezing with the thumb; check every string one by one.",
            "It takes weeks for most people: practise it a few minutes a day, never until it hurts."),
            "Barre chords let you play any chord anywhere: one shape, every key.",
            ("Pressing with the soft middle of the first finger: the strings under its creases go dead.",), ("F",)),
    ), (
        Check("f_clean", "Play the F barre chord so every note rings", "heard_chord", about="F"),
        Check("changes_c_f", "One-minute changes: C to F and back", "counted", passes_at=20, unit="changes a minute"),
    )),
    Stage(5, "Lead basics", "the minor pentatonic scale, picking and bends", (
        Lesson("pentatonic", "The A minor pentatonic, box one", (
            "First finger at the 5th fret; on every string play the 5th fret and one more note: 8th on the two E "
            "strings and the B string, 7th on the A, D and G strings.",
            "Up and down, slowly, alternating down and up picks.",
            "Then with a metronome: two notes a beat (eighth notes), starting at 60 bpm."),
            "This one shape is where most rock and blues solos live.",
            ("Lifting fingers far off the strings: keep them close, ready.",)),
        Lesson("bends", "Bending a string", (
            "Third finger at the 7th fret of the G string, with the first and second fingers behind it on the same "
            "string to help.",
            "Push the string up toward the ceiling until it sounds like the 9th fret (a whole step): play the 9th fret "
            "first to hear the target.",
            "Turn the wrist, like turning a door knob; don't push with the finger alone."),
            "A bend in tune is what makes a solo sing; out of tune is the most common thing that makes it sour.", ()),
    ), (
        Check("pentatonic_80", "A minor pentatonic up and down in eighth notes at 80 bpm, clean", "counted",
              passes_at=80, unit="bpm"),
        Check("bend_in_tune", "Bend the G string at the 7th fret up to the note of the 9th fret, in tune", "said"),
    )),
)

CHECKS: dict[str, tuple[Stage, Check]] = {c.id: (s, c) for s in STAGES for c in s.checks}
LESSONS: dict[str, tuple[Stage, Lesson]] = {l.id: (s, l) for s in STAGES for l in s.lessons}


def shape_text(chord: Chord) -> str:
    """Pure logic. A chord shape said plainly, string by string from the low E: \"E minor: low E open, A 2nd fret
    (finger 2), ...\"."""
    strings = ("low E", "A", "D", "G", "B", "high E")
    parts = []
    for name, fret, finger in zip(strings, chord.frets, chord.fingers):
        if fret == "x":
            parts.append(f"{name} not played")
        elif fret == "0":
            parts.append(f"{name} open")
        else:
            parts.append(f"{name} fret {fret} (finger {finger})")
    return f"{chord.name} ({', '.join(chord.notes)}): " + ", ".join(parts)


def _extra(lesson: Lesson) -> str:
    """The chord shapes a lesson teaches, said string by string."""
    shapes = [shape_text(CHORDS[c]) for c in lesson.about if c in CHORDS]
    return ("Shapes: " + "; ".join(shapes) + ".") if shapes else ""


def _wav(payload) -> tuple[list, int]:
    """The recording a verifier was sent (WAV bytes) as samples and a rate; ValueError when it's missing, too big
    or can't be read."""
    import io

    from core import guitar_ear as ear

    if not payload or len(payload) > MAX_RECORDING:
        raise ValueError("Send a short WAV recording (a few seconds).")
    try:
        return ear.read_wav(io.BytesIO(payload))
    except ear.EarError as problem:
        raise ValueError(str(problem)) from None


def _heard_chord(context, program: Program, check: Check, payload) -> dict:
    """Verifier heard_chord: the recording's notes against the chord's; passed when every chord tone rang and
    nothing stray did. The attempt is kept either way."""
    from core import guitar_ear as ear

    samples, rate = _wav(payload.get("wav") if isinstance(payload, dict) else payload)
    chord = CHORDS[check.about]
    try:
        heard = ear.hear_chord(ear.chroma(samples, rate), chord.notes)
    except ear.EarError as problem:
        raise ValueError(str(problem)) from None
    done = context.paths.attempt(program, check.id, heard["passed"], how="heard",
                                 detail=f"rang {heard['rang']}, missing {heard['missing']}, stray {heard['stray']}")
    return {"check": check.id, "passed": heard["passed"], "heard": heard, "said": ear.describe_chord(chord.name, heard),
            "stage_done": done["stage_done"]}


def _heard_tuning(context, program: Program, check: Check, payload) -> dict:
    """Verifier heard_tuning: one open string's pitch against standard tuning (payload {"wav", "string"}, 6 the low
    E); passed when all six have been heard in tune on the same day. The attempt is kept either way."""
    from core import guitar_ear as ear

    string = payload.get("string") if isinstance(payload, dict) else None
    if string not in (1, 2, 3, 4, 5, 6):
        raise ValueError("Which string? 6 is the low E, 1 the high E.")
    samples, rate = _wav(payload.get("wav"))
    try:
        result = ear.tuning(ear.pitch(samples, rate), string)
    except ear.EarError as problem:
        raise ValueError(str(problem)) from None
    book = context.paths
    today = date.today().isoformat()
    tuned = {int(a["detail"].split(":")[1]) for a in book.path(program.id)["attempts"]
             if a["check"] == check.id and a["date"] == today and str(a["detail"]).startswith("string:")
             and a["value"] is not None and abs(a["value"]) <= 10}
    if result["in_tune"]:
        tuned.add(string)
    all_six = tuned == {1, 2, 3, 4, 5, 6}
    done = book.attempt(program, check.id, all_six, value=result["cents"], how="heard", detail=f"string:{string}")
    if result["in_tune"]:
        said = f"String {string} is in tune ({result['target']})."
    else:
        fix = "loosen it a little" if result["cents"] > 0 else "tighten it a little"
        said = (f"String {string} should be {result['target']}; I hear {result['heard']}, "
                f"{abs(result['cents']):g} cents {'sharp' if result['cents'] > 0 else 'flat'}: {fix}.")
    said += " All six are in tune." if all_six else f" In tune so far today: {len(tuned)} of 6."
    return {"check": check.id, "passed": all_six, "tuning": result, "said": said, "stage_done": done["stage_done"]}


PROGRAM = register(Program(
    "guitar", "Guitar", SKILL, "🎸", "From holding a guitar to chords, rhythm, songs, barre chords and lead basics.",
    ("guitar", "chord", "strum", "fret"), STAGES,
    verifiers={"heard_chord": _heard_chord, "heard_tuning": _heard_tuning}, extra=_extra, plan=(15, 5)))
