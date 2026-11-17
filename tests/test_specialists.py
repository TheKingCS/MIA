"""
tests.test_specialists
========================

MIA's specialists (core/specialists.py, DEC-0109): their charters name real
skills, tracks and loops; a workbook keeps only sourced notes; a person
confirms or withdraws; study hall takes them in turn; and the answer always
says where a note came from and whether it's confirmed. As agents (DEC-0197):
each has a department, task types and real reviewers, may call only tools that
change nothing, carries its caveat where its work can hurt someone, and the
embedded systems and homestead crafts specialists answer their own questions, as do the hoodie's four
(acoustics, audio DSP, textiles, portable power), each naming its dangers.
"""

from __future__ import annotations

import json

import pytest

from core import specialists as sp


def test_every_charter_is_whole_and_points_at_real_things():
    """Each area Zac named has a specialist, and every skill category, curriculum track and loop a charter names is
    real; each has limits and somewhere to start."""
    from core import curriculum
    from core.loops import LOOPS

    ids = {s.id for s in sp.SPECIALISTS}
    assert {"construction", "radio", "strategy", "homesteading", "research", "testing"} <= ids
    assert len(ids) == len(sp.SPECIALISTS)
    loops = {l.id for l in LOOPS}
    tracks = {t.id for t in curriculum.TRACKS}
    skill_areas = {"Body", "Construction", "Creative", "Homestead", "Maker", "Mind", "Outdoor", "Social", "Technology"}
    for s in sp.SPECIALISTS:
        assert set(s.loops) <= loops and set(s.tracks) <= tracks and set(s.skills) <= skill_areas, s.id
        assert s.limits and s.starts_from and s.words, s.id
    assert "never how to hurt people" in sp.BY_ID["strategy"].limits
    assert "on MIA herself only" in sp.BY_ID["testing"].limits


def test_a_workbook_keeps_only_sourced_notes(tmp_path):
    """A note needs a title, a body and a source, isn't a repeat, and isn't too long; answering an open question
    takes it off the list; confirm and withdraw change its status, and a withdrawn title can be written afresh."""
    with pytest.raises(ValueError, match="where it comes from"):
        sp.add_note("radio", "Dipoles", "Half a wavelength.", [], folder=tmp_path)
    with pytest.raises(ValueError):
        sp.add_note("radio", "Long", "x" * (sp.MAX_BODY + 1), ["ARRL Handbook"], folder=tmp_path)
    with pytest.raises(ValueError):
        sp.add_note("nobody", "T", "B", ["S"], folder=tmp_path)
    q = sp.BY_ID["radio"].starts_from[0]
    note = sp.add_note("radio", "Which licence for which radio", "FRS needs none; GMRS needs a licence.",
                       ["FCC Part 95"], answers=q, folder=tmp_path)
    assert note["status"] == "derived" and q not in sp.book("radio", tmp_path)["questions"]
    with pytest.raises(ValueError, match="already"):
        sp.add_note("radio", "which licence for which radio", "again", ["x"], folder=tmp_path)
    assert sp.confirm("radio", note["id"], tmp_path)["status"] == "confirmed"
    sp.withdraw("radio", note["id"], "out of date", tmp_path)
    assert sp.add_note("radio", "Which licence for which radio", "Updated.", ["FCC Part 95"], folder=tmp_path)
    sp.add_question("radio", "  How do repeaters work? ", tmp_path)
    sp.add_question("radio", "how do repeaters work?", tmp_path)
    assert sp.book("radio", tmp_path)["questions"].count("How do repeaters work?") == 1


def test_answers_say_where_they_come_from_and_whether_confirmed(tmp_path):
    """The best live note answers with its sources and status; a question nobody has a note for goes on the list of
    the specialist whose area it is; the tool picks a named specialist."""
    note = sp.add_note("homesteading", "Keeping hens laying in winter", "Hens need about 14 hours of light to lay.",
                       ["Storey's Guide to Raising Chickens"], folder=tmp_path)
    said = sp.answer("how do I keep my hens laying in winter", folder=tmp_path)
    assert said.startswith("From my homesteading specialist (written by a model, not confirmed yet): Keeping hens")
    assert "Sources: Storey's Guide to Raising Chickens." in said
    sp.confirm("homesteading", note["id"], tmp_path)
    assert "(confirmed by a person)" in sp.answer("hens laying winter", folder=tmp_path)
    unknown = sp.answer("what gauge wire for a 20 amp circuit on my neighbour's deck", folder=tmp_path)
    assert "electrical specialist doesn't have a note" in unknown  # a trade's own specialist (DEC-0149)
    book = sp.book("electrical", tmp_path)
    assert book["unanswered"] == 1 and not any("neighbour" in q for q in book["questions"])  # never their words
    assert sp.next_to_study(tmp_path).id == "electrical"  # asked and couldn't answer: it studies first
    sp.answer("what gauge wire for a 20 amp deck circuit", folder=tmp_path, keep_question=True)
    assert "what gauge wire for a 20 amp deck circuit" in sp.book("electrical", tmp_path)["questions"]
    assert [s.id for s in sp.who_knows("my meshtastic antenna")][0] == "radio"


def test_study_hall_takes_turns_and_keeps_good_notes(tmp_path):
    """The specialist that studied longest ago goes next; the teacher's good notes are kept as derived, a sourceless
    one is refused, new questions are added, and the pages are written."""
    asked = []

    def teacher(prompt):
        asked.append(prompt)
        return "Notes:\n" + json.dumps({"notes": [
            {"title": "Framing a header", "body": "Size it from the span and load tables.", "sources": ["IRC R602.7"],
             "answers": sp.BY_ID["construction"].starts_from[0]},
            {"title": "No source", "body": "Trust me.", "sources": []}],
            "questions": ["When do you need an engineer for a beam?"]})

    first = sp.study(teacher, folder=tmp_path, pages=tmp_path / "pages", use_library=False)
    assert first["specialist"] == "construction" and first["kept"] == ["Framing a header"] and len(first["refused"]) == 1
    assert "never how to hurt people" not in asked[0] and "safety first" in asked[0] and "Its open questions" in asked[0]
    book = sp.book("construction", tmp_path)
    assert book["studied"] and "When do you need an engineer for a beam?" in book["questions"]
    assert sp.next_to_study(tmp_path).id == "homesteading"
    page = (tmp_path / "pages" / "construction.md").read_text(encoding="utf-8")
    assert "## Notes, not confirmed yet" in page and "Sources: IRC R602.7" in page
    assert "[Construction](construction.md): 1 notes (0 confirmed)" in (tmp_path / "pages" / "README.md").read_text(
        encoding="utf-8")


def test_study_is_grounded_in_her_reference_library(tmp_path):
    """With packs, the teacher gets excerpts for the open questions, each labelled to cite; without, it's told
    there are none; a failing search is skipped."""
    from types import SimpleNamespace

    hit = SimpleNamespace(pack_title="Wikipedia (radio)", article_title="Dipole antenna", snippet="A dipole   is two")
    text = sp.grounding(["How long is a dipole?"], lambda q, n: [hit])
    assert text == "- Wikipedia (radio), 'Dipole antenna' (for: How long is a dipole?): A dipole is two"
    assert sp.grounding(["q"], None) == "(no reference packs installed)"
    assert sp.grounding(["q"], lambda q, n: 1 / 0) == "(nothing in the reference packs for these questions)"
    asked = []
    sp.study(lambda prompt: asked.append(prompt) or '{"notes": []}', "radio", folder=tmp_path, pages=None,
             search=lambda q, n: [hit])
    assert "Reference library: <pack>, '<article>'" in asked[0] and "'Dipole antenna'" in asked[0]


# ------------------------------------------------------------------ as agents (DEC-0198, T1)

def test_every_specialist_is_a_whole_agent_role_with_a_department_task_types_and_real_reviewers():
    for s in sp.SPECIALISTS:
        assert s.department in sp.DEPARTMENTS, s.id
        assert s.task_types and set(s.task_types) <= set(sp.TASK_TYPES), s.id
        assert s.reasoning in sp.REASONING and set(s.needs) <= set(sp.NEEDS), s.id
        assert set(s.reviews) <= set(sp.BY_ID) and s.id not in s.reviews, s.id
        if "review" in s.task_types or "safety_review" in s.task_types:
            pass  # a reviewer may also have reviewers of its own
    assert set(sp.ROLES) == set(sp.BY_ID)  # no role without a charter, no charter without a role


def test_no_agent_may_call_a_tool_that_changes_anything():
    """The teams design's section 6: an agent's ceiling is reading and drafting; every tool it lists is real and
    tiered observe or suggest in its app's manifest. One whose answers rest on figures has the worksheet."""
    from core import grants

    tiers = grants.tiers()
    for s in sp.SPECIALISTS:
        for tool in s.tools:
            assert tiers.get(tool) in (grants.OBSERVE, grants.SUGGEST), (s.id, tool, tiers.get(tool))
        assert ("work_it_out" in s.tools) == ("numbers" in s.needs), s.id


def test_every_agent_whose_work_can_hurt_someone_carries_its_caveat():
    """Q-57: electrical, battery, structural, food and chemical work is a draft a qualified person checks."""
    for s in sp.SPECIALISTS:
        if s.department in sp.SAFETY_DEPARTMENTS:
            assert s.caveat, s.id
    for sid in ("electrical", "carpentry", "embedded", "crafts", "plumbing"):
        assert sp.BY_ID[sid].caveat, sid
    assert "lithium" in sp.BY_ID["embedded"].caveat and "lye" in sp.BY_ID["crafts"].caveat.lower()


def test_embedded_systems_and_homestead_crafts_specialists_answer_their_own_questions():
    """Zac, 2026-11-17 (Q-56): specialists for embedded systems projects and homestead crafts."""
    assert sp.who_knows("how do I power an esp32 sensor node from a battery")[0].id == "embedded"
    assert sp.who_knows("my i2c sensor isn't answering the microcontroller")[0].id == "embedded"
    assert sp.who_knows("cold process soap and how much lye")[0].id == "crafts"
    assert sp.who_knows("tanning a deer hide into leather")[0].id == "crafts"
    assert "never sized from memory" in sp.BY_ID["crafts"].limits
    assert "qualified person must check" in sp.BY_ID["embedded"].limits


def test_agents_are_found_by_task_and_department_and_reviewers_are_never_themselves():
    designers = {s.id for s in sp.agents_for("build_code")}
    assert {"embedded", "engineering", "testing"} <= designers and "music" not in designers
    assert {s.id for s in sp.agents_for(department="homestead")} == {"homesteading", "crafts"}
    assert "electrical" in {s.id for s in sp.reviewers_of("embedded")}
    for s in sp.SPECIALISTS:
        assert s not in sp.reviewers_of(s.id)


def test_she_says_which_specialists_she_has_by_department():
    said = sp.describe_registry()
    assert f"I have {len(sp.SPECIALISTS)} specialists" in said and "Embedded systems" in said
    assert "Homestead crafts" in said and "changes nothing" in said




def test_the_hoodies_specialists_answer_their_own_questions_and_name_their_dangers():
    """S4's second batch (DEC-0198 Q-55, the hoodie second): acoustics, audio DSP, textiles and portable power, each
    a whole agent whose worksheet has its own calculators; an acoustic guitar is still music's and a mahogany frame
    is never a battery question."""
    from core.eng_calcs import DISCIPLINES as CALC_DISCIPLINES
    from core.specialist_work import DISCIPLINES

    assert sp.who_knows("how loud is a speaker in a hood at 10 cm")[0].id == "acoustics"
    assert sp.who_knows("what sample rate and bit depth for voice")[0].id == "audio_dsp"
    assert sp.who_knows("how many yards of fleece for a hoodie")[0].id == "textiles"
    assert sp.who_knows("how long does a lipo battery pack take to charge")[0].id == "power"
    assert sp.who_knows("which acoustic guitar strings should I buy")[0].id == "music"
    assert "power" not in {s.id for s in sp.who_knows("refinishing a mahogany display frame")}
    for sid in ("acoustics", "audio_dsp", "textiles", "power"):
        spec = sp.BY_ID[sid]
        assert spec.caveat and "work_it_out" in spec.tools and len(spec.starts_from) == 3, sid
        assert DISCIPLINES[sid][0] == sid and sid in CALC_DISCIPLINES, sid
    assert "NIOSH" in sp.BY_ID["acoustics"].limits and "fire risk" in sp.BY_ID["power"].limits
    assert "burns" in sp.BY_ID["textiles"].limits and "qualified person" in sp.BY_ID["textiles"].limits
