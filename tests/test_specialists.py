"""
tests.test_specialists
========================

MIA's specialists (core/specialists.py, DEC-0109): their charters name real
skills, tracks and loops; a workbook keeps only sourced notes; a person
confirms or withdraws; study hall takes them in turn; and the answer always
says where a note came from and whether it's confirmed.
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
    unknown = sp.answer("what gauge wire for a 20 amp circuit on the deck", folder=tmp_path)
    assert "construction specialist doesn't have a note" in unknown
    assert "what gauge wire for a 20 amp circuit on the deck" in sp.book("construction", tmp_path)["questions"]
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
