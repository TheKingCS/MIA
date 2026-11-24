"""
core.picture_of_you
=====================

The picture of him (DEC-0290; Zac, 2026-11-23: "Yes, build it"; the personality plan's parked phase 3, the
self-knowledge map): one page of what MIA believes about him, each belief with where it came from and how she knows it,
and a way to correct or forget it. Nothing new is collected: it lays out what she already holds.

- **What she remembers** (core/user_memory_manager.py): his memories grouped by their category, each with how it's
  known (said, observed, inferred, computed: DEC-0281), where it came from (a conversation, an approved card), whether
  he confirmed it; Fix and Forget are the actions memory.fix and memory.forget (undoable).
- **His skills** (core/skill_manager.py): the ones with any XP, by level, from what he logged and finished.
- **What he's learning** (core/paths.py): the paths started and the stage each is on.
- **How he likes answers** (core/answer_compare.py): each dimension's lean and how settled it is.

`picture(context)` is the page's data (/api/picture, web/you.html); `say(context)` answers "what do you know about
me?" in a few sentences. Her answers already read his memories (core/assistant_chat.turn_memories); this page is where
he sees and corrects them, so she stops getting wrong what she should know.
"""

from __future__ import annotations

from core.logger import get_logger

log = get_logger(__name__)

HOW_SAID = {"said": "you told me", "observed": "I saw it in your records", "inferred": "my guess from what you said",
            "computed": "worked out from your records"}


def _memories(context) -> list[dict]:
    """His memories grouped by category, each {id, text, how, source, confirmed}, the categories in order."""
    store = getattr(context, "user_memories", None)
    if store is None:
        return []
    groups: dict = {}
    for m in store.all_memories():
        source = ("a conversation" if str(m.source).startswith("conversation:") or m.source_conversation_id
                  else "a card you approved" if m.source == "card" else "before I kept sources")
        groups.setdefault(m.category or "Other", []).append({
            "id": m.memory_id, "text": m.text, "how": HOW_SAID.get(m.how, m.how or "you told me"),
            "source": source, "confirmed": bool(m.confirmed_at), "since": (m.created_at or "")[:10]})
    return [{"category": c, "items": items} for c, items in sorted(groups.items())]


def _skills(context) -> list[dict]:
    """The skills he has any XP in, highest level first: {name, level, xp}."""
    from core.person_settings import person_id
    from core.skill_leveling import compute_skill_level_progress

    skills = getattr(context, "skills", None)
    who = person_id(context)
    if skills is None or who is None:
        return []
    out = []
    for p in skills.progress_for_profile(who):
        if not p.total_xp:
            continue
        definition = skills.get_skill(p.skill_id)
        level = compute_skill_level_progress(p.total_xp)[0]
        out.append({"name": definition.name if definition else p.skill_id, "level": level, "xp": p.total_xp})
    return sorted(out, key=lambda s: (-s["level"], -s["xp"]))


def _learning(context) -> list[dict]:
    """The learning paths he started, from his own path book (`context.paths`): {name, stage, of}."""
    from core import paths

    book = getattr(context, "paths", None)  # the person's own book (view_for), never the device's file
    if book is None:
        return []
    out = []
    for pid in book.started():
        program = paths.program_of(context, pid)
        record = book.path(pid) or {}
        if program is not None:
            out.append({"id": pid, "name": program.name, "stage": int(record.get("stage") or 1),
                        "of": len(program.stages)})
    return out


def _answers(context) -> list[dict]:
    """How he likes answers: each dimension's lean, as he's shown it by picking."""
    from core.answer_compare import screen

    got = screen(context)
    if not got.get("available"):
        return []
    out = []
    for d in got.get("dimensions", []):
        lean = next((o["label"] for o in d["options"] if o["value"] == d["preferred"]), "") if d["picks"] else ""
        out.append({"name": d["name"], "lean": lean, "word": d["word"]})
    return out


def picture(context) -> dict:
    """The page's data: memories, skills, learning and answers, each section that can't be read left empty."""
    out = {"memories": [], "skills": [], "learning": [], "answers": []}
    for key, read in (("memories", _memories), ("skills", _skills), ("learning", _learning), ("answers", _answers)):
        try:
            out[key] = read(context)
        except Exception:  # noqa: BLE001 - one record that can't be read never empties the page
            log.exception("Picture of you: %s couldn't be read", key)
    out["count"] = sum(len(g["items"]) for g in out["memories"])
    return out


def say(context) -> str:
    """For "what do you know about me?": a few sentences from the picture, and where to correct it."""
    got = picture(context)
    parts = []
    if got["count"]:
        cats = ", ".join(f"{g['category'].lower()} ({len(g['items'])})" for g in got["memories"][:6])
        parts.append(f"I remember {got['count']} things about you: {cats}.")
    if got["skills"]:
        parts.append("Your strongest skills: " + ", ".join(f"{s['name']} (level {s['level']})"
                                                          for s in got["skills"][:4]) + ".")
    if got["learning"]:
        parts.append("You're learning " + ", ".join(f"{p['name']} (stage {p['stage']} of {p['of']})"
                                                    for p in got["learning"][:4]) + ".")
    leans = [a for a in got["answers"] if a["lean"]]
    if leans:
        parts.append("For answers you lean to " + ", ".join(f"{a['lean'].lower()} {a['name'].lower()}"
                                                           for a in leans[:3]) + ".")
    if not parts:
        return "I don't hold much about you yet. As we talk and you log things, it shows on the You page."
    return " ".join(parts) + " Everything is on the You page, where you can fix or forget any of it."
