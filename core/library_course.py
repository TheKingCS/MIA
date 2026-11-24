"""
core.library_course
=====================

Courses from her offline library (Zac, 2026-11-24: "I want to be able to say MIA, I want to learn about x and have
offline coursework and instruction about any subject and it be quality information"). The knowledge comes from the
packs she keeps offline (core/offline_library.py: Wikipedia, the homestead, building, health and preparedness
shelves...), never from the model's memory; the model only teaches what a lesson's own article says.

**Making a course** (`outline`, `make`; the tool `learn_about`): the subject is searched in the library once for each
of `STAGES` (what it is, the basics, tools and materials, how it's done, safety, common problems, going further,
where it comes from), and each stage keeps the best article no earlier lesson used whose title or text holds the
subject's words. A stage the library has nothing for is left out; fewer than `MIN_LESSONS` lessons and there's no
course, said plainly. The course goes in Classroom (core/classroom_manager.py) under the subject "Library courses",
one lesson a stage, each lesson's notes naming its article, pack and reference so it can be read again. It's made
in one tool call, so one undo takes it all back.

**Being taught** (`teach`; the tool `library_lesson`): the next lesson not done in the course named (or the newest
library course) is read whole from its article (core/offline_library.read_further, framed as outside text) and
handed to the model with how to teach it: the key ideas in plain words, one example from the text, and one
question to check, nothing that isn't in the text. "Done with that lesson" marks it (Classroom's own tool).

**Without the library** (no packs, or a reader this computer can't run): it says so and points to a learning path
(core/paths.py) instead; nothing is made.
"""

from __future__ import annotations

import re
from typing import Optional

from core.logger import get_logger

log = get_logger(__name__)

SUBJECT = "Library courses"  # the Classroom subject the courses go under
MIN_LESSONS = 2
# (the lesson's stage, how the library is searched for it)
STAGES = (
    ("What it is", "{s}"),
    ("The basics", "{s} basics introduction"),
    ("Tools and materials", "{s} tools equipment materials"),
    ("How it's done", "{s} method technique how to"),
    ("Safety", "{s} safety hazards precautions"),
    ("Common problems", "{s} problems mistakes troubleshooting"),
    ("Going further", "{s} advanced"),
    ("Where it comes from", "{s} history"),
)
_STOP = {"a", "an", "the", "of", "and", "or", "to", "in", "on", "for", "about", "how", "my", "some", "more", "this",
         "that", "these", "those", "want", "learn", "winter", "summer", "spring", "fall", "year", "week", "today"}


def _words(text: str) -> set[str]:
    """Pure logic. A text's meaningful words, lower case, a plural the same as one."""
    return {w.rstrip("s") for w in re.findall(r"[a-z0-9]+", (text or "").lower()) if w not in _STOP and len(w) > 2}


def subject_of(said: str) -> str:
    """Pure logic. The subject in "I want to learn about beekeeping", "I'd like to learn more about knots", "teach me
    everything about solar power", "a course on knots"; the words as given otherwise."""
    m = re.search(r"\b(?:learn(?:ing)? (?:all |more )?about|everything about|course (?:on|about)|study up on|"
                  r"understand|teach me about)\s+(.+?)[.?!]*$", (said or "").strip(), re.I)
    return (m.group(1) if m else (said or "")).strip(" .?!").strip()


def _library(context):
    """Her offline library when it has packs, else None."""
    library = getattr(context, "reference_library", None)
    try:
        return library if library is not None and library.list_packs() else None
    except Exception:  # noqa: BLE001 - a reader this computer can't run is no library here
        log.exception("The offline library couldn't be read")
        return None


def outline(library, subject: str) -> list[dict]:
    """Reads the library. The course's lessons: [{stage, article, pack, ref, gist}], one a stage the library has a
    fitting article for (its title holds every word of the subject, or its text two thirds of them), never the same
    article twice."""
    from core.offline_library import passages

    want = _words(subject)
    used, lessons = set(), []
    for stage, query in STAGES:
        try:
            found = passages(library, query.format(s=subject), keep=4)
        except Exception:  # noqa: BLE001 - one search that fails leaves the stage out
            log.exception("The library search for %s failed", stage)
            continue
        for p in found:
            key = (p["pack"], p["article"])
            need = max(1, -(-len(want) * 2 // 3))  # two thirds of the subject's words, rounded up
            fits = want and (want <= _words(p["article"]) or len(want & _words(p["text"])) >= need)
            if key in used or not fits:
                continue
            used.add(key)
            gist = " ".join(p["text"].split())
            lessons.append({"stage": stage, "article": p["article"], "pack": p["pack"], "ref": p["ref"],
                            "gist": gist if len(gist) <= 240 else gist[:240].rsplit(" ", 1)[0] + "…"})
            break
    return lessons


def make(context, said: str) -> str:
    """Makes the course in Classroom from the library (see the module's opening) and says what it holds; or why
    there's none."""
    subject = subject_of(said)
    if not subject:
        return "What would you like to learn about?"
    library = _library(context)
    if library is None:
        return (f"I can't build a course on {subject} here: my offline library has no packs I can read on this "
                "computer (the Knowledge page says why). I can start a learning path for it instead: say \"start "
                f"learning {subject}\".")
    classroom = getattr(context, "classroom", None)
    if classroom is None:
        return "Classroom isn't on this MIA, so there's nowhere to keep a course."
    title = subject[:1].upper() + subject[1:]
    made = next((c for c in _courses(classroom) if c.name.lower() == title.lower()), None)
    if made is not None:
        return (f"There's already a course on {subject} in Classroom. Say \"teach me the next lesson on {subject}\" "
                "to carry on.")
    lessons = outline(library, subject)
    if len(lessons) < MIN_LESSONS:
        return (f"My offline library doesn't cover {subject} well enough for a course: "
                + (f"only \"{lessons[0]['article']}\" fits. Ask me about it and I'll read it with you."
                   if lessons else "nothing in it fits.") + " A learning path, or the library online, could fill it.")
    home = next((s for s in classroom.all_subjects() if s.name == SUBJECT), None) or classroom.add_subject(
        SUBJECT, category="Study", description="Courses built from MIA's offline library, each lesson from an article.")
    course = classroom.add_course(home.subject_id, title, description=f"From the offline library: {len(lessons)} "
                                                                     "lessons, each from one article.")
    for n, lesson in enumerate(lessons, 1):
        classroom.add_lesson(course.course_id, f"{n}. {lesson['stage']}: {lesson['article']}",
                             notes=f"Read: \"{lesson['article']}\" ({lesson['pack']}).\nref: {lesson['ref']}\n"
                                   f"What it covers: {lesson['gist']}")
    listed = "; ".join(f"{n}. {x['stage']} ({x['article']})" for n, x in enumerate(lessons, 1))
    return (f"I made a course on {subject} in Classroom from my offline library, {len(lessons)} lessons, each from "
            f"one article: {listed}. Say \"teach me the next lesson on {subject}\" to start.")


_REF = re.compile(r"^ref: (.+)$", re.M)
TEACH = ("Teach this lesson from the text above only: the key ideas in plain words, one example taken from the text, "
         "then one short question to check they understood. Never add facts the text doesn't have; if the text is "
         "thin, say so. When they've answered, they can say \"done with that lesson\".")


def _courses(classroom) -> list:
    """The library courses in Classroom, newest first."""
    home = next((s for s in classroom.all_subjects() if s.name == SUBJECT), None)
    if home is None:
        return []
    found = list(classroom.courses_for_subject(home.subject_id))
    return sorted(found, key=lambda c: c.created_at or "", reverse=True)


def teach(context, said: str = "") -> str:
    """The next lesson not done in the library course the words name (the best match; with no words, the newest),
    read from its article and framed for the model to teach (`TEACH`); words that name no course are said, never the
    newest taught quietly; or what's missing."""
    from core.offline_library import read_further

    classroom = getattr(context, "classroom", None)
    courses = _courses(classroom) if classroom is not None else []
    if not courses:
        return "There's no library course yet. Say \"I want to learn about\" something and I'll build one."
    want = _words(subject_of(said)) - {"next", "lesson", "teach", "course", "me", "continue"} if said else set()
    named = [c for c in courses if want and want & _words(c.name)]
    if want and not named:
        return ("There's no library course on that. Yours: " + ", ".join(c.name for c in courses) + ". Say \"I want "
                "to learn about\" something to build one.")
    course = max(named, key=lambda c: len(want & _words(c.name))) if named else courses[0]
    lessons = sorted(classroom.lessons_for_course(course.course_id), key=lambda x: x.created_at or "")
    lesson = next((x for x in lessons if not x.completed), None)
    if lesson is None:
        return f"You've finished every lesson in {course.name}. Ask me anything about it, or start another subject."
    ref = _REF.search(lesson.notes or "")
    library = _library(context)
    if ref is None or library is None:
        return (f"Next in {course.name}: {lesson.name}. I can't read its article here right now: "
                + ("my offline library isn't readable on this computer." if library is None else "its reference is missing."))
    text = read_further(library, ref.group(1).strip(), focus=course.name)
    done = sum(1 for x in lessons if x.completed)
    return f"{course.name}, lesson {done + 1} of {len(lessons)}: {lesson.name}.\n{text}\n{TEACH}"
