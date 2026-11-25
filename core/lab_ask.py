"""
core.lab_ask
==============

Ask MIA, on a course's page (Zac, 2026-11-25: "an ask MIA button or text bar where I can get more detailed info or
ask why something is done the way she says"). His question goes to the model with what he's looking at, assembled
here from core's own records, never from the page: the lab (why, steps, what to watch for, parts, wiring, the sketch,
its circuit's build steps and why each wire goes where it does) or the drill question in front of him (its choices
and why each is judged as it is). The model explains from that material, and says plainly when a question goes past
it. The question and answer go into his active conversation, so "and what about...?" in Talk follows on.

Who she is comes from core/personality.IDENTITY, with this page's teaching line after it.
`material(course, lesson, drill, n)`: the text the answer stands on. `ask(context, course, lesson, question, drill,
n)`: {answer, about}. Read only: nothing changes but the conversation. By voice too: "why does the watchdog lab refuse
a dose?" comes here from core/esp32_sim.reply, a lab named and a why asked.
"""

from __future__ import annotations

from typing import Optional

INSTRUCTION = (
    "Here you're teaching him one lesson of a course he's working through, on its page. Answer his question from the "
    "material below: explain the why, in plain words, as a patient expert at his elbow would; short paragraphs, "
    "specific to this lab or drill. Use what the material says for every number, pin and safety rule; if his question "
    "goes past the material, say so, give the general idea, and never invent a figure for food safety, voltage or "
    "current. Don't repeat the whole lesson back; answer what he asked.")


def material(course: str, lesson: str = "", drill: str = "", n: int = 0) -> tuple:
    """Pure logic. (what it's about, the material as text) for a lab of a course, or a drill's question n (from 1).
    ValueError for a course, lab or drill that isn't there.
    The Arduino course's labs too, with their circuits."""
    from core import drills, paths

    if drill:
        found = drills.by_id(drill)
        if found is None or found.program != course:
            raise ValueError("There's no such drill on this course.")
        n = max(1, min(int(n or 1), len(found.questions)))
        q = found.questions[n - 1]
        lines = [f"Drill: {found.title}. {found.situation}", f"Question {n}: {q.ask}"]
        lines += [f"- {c.text}: {c.verdict}. {c.why}" for c in q.choices]
        return f"the {found.title} drill, question {n}", "\n".join(lines)
    program = paths.program_of(None, course)
    if program is None:
        raise ValueError("There's no course by that name.")
    found = next(((s, l) for s in program.stages for l in s.lessons if l.id == lesson), None)
    if found is None:
        raise ValueError("Which lab? That one isn't in this course.")
    stage, the = found
    lines = [f"Course: {program.name}. Stage {stage.number}: {stage.name}.", f"Lab: {the.title}.", f"Why: {the.why}",
             "Steps: " + " ".join(f"{i}. {s}" for i, s in enumerate(the.steps, 1))]
    if the.watch:
        lines.append("Watch for: " + " ".join(the.watch))
    if course in ("esp32", "arduino"):
        from core import esp32_sim
        from core.esp32_lab import labs_of

        lab = labs_of(course).get(the.id)
        if lab:
            lines.append("Parts: " + ", ".join(lab["parts"]))
            if lab["wiring"]:
                lines.append("Wiring: " + "; ".join(f"{a} to {b}" for a, b in lab["wiring"]))
            lines.append("The sketch:\n" + lab["code"])
        circuit = esp32_sim.circuit_of(the.id, course=course)
        if circuit and circuit["steps"]:
            lines.append("The build, wire by wire: " + " ".join(f"{s['n']}. {s['words']} ({s['why']})"
                                                                 for s in circuit["steps"]))
        if circuit and circuit["note"]:
            lines.append(circuit["note"])
    return f"the {the.title} lab", "\n".join(lines)


def _conversation(context):
    """His active conversation (a new one when there's none), or None without a conversation store."""
    store = getattr(context, "conversations", None)
    if store is None:
        return None
    active = store.get_active_conversation_id()
    found = store.get_conversation(active) if active else None
    return found or store.start_new_active_conversation()


def ask(context, course: str, lesson: str, question: str, drill: str = "", n: int = 0, record: bool = True) -> dict:
    """His question answered from the material (`material`): {answer, about}. ValueError for an empty question or
    something that isn't there; the answer says so plainly when the model can't be reached. Kept in his active
    conversation unless `record` is False (a voice turn, which keeps its own: core/esp32_sim.reply)."""
    from core.llm_manager import without_role_label

    question = " ".join(str(question or "").split())[:600]
    if not question:
        raise ValueError("Ask something first.")
    from core.personality import IDENTITY

    about, text = material(course, lesson, drill, n)
    messages = [{"role": "system", "content": f"{IDENTITY} {INSTRUCTION}\n\nThe material ({about}):\n{text}"},
                {"role": "user", "content": question}]
    llm = getattr(context, "llm", None)
    reply = llm.chat_with_tools(messages, tools=[]) if llm is not None else None
    answer = without_role_label((getattr(reply, "content", "") or "").strip()) if reply is not None else ""
    if not answer:
        return {"answer": "I can't reach my model right now, so I can't explain it yet. Try again in a moment.",
                "about": about}
    conversation = _conversation(context) if record else None
    if conversation is not None:
        store = context.conversations
        store.add_message(conversation.conversation_id, "user", f"(On {about}) {question}")
        store.add_message(conversation.conversation_id, "assistant", answer)
    return {"answer": answer, "about": about}
