"""
tests.test_specialties
========================

What MIA is trained for and built to do (core/capabilities.py `specialty_list`, Zac 2026-11-08): every line read
from the code that makes it true, numbers included; a specialty whose source is missing is left out instead of
claimed; painting is only "ready" when its engine runs; the person's own grow numbers join when they exist; and
"what are you trained for?" reaches the tool that says it.
"""

from pathlib import Path
from types import SimpleNamespace

import pytest

from core import capabilities
from core.capabilities import specialties, specialty_list

ROOT = Path(__file__).resolve().parent.parent


def _lines(context=None) -> dict:
    """The specialties as {title: line}."""
    return dict(specialty_list(context if context is not None else SimpleNamespace()))


def test_the_numbers_come_from_the_code():
    from core.curriculum import TRACKS
    from core.plan_library import BUILT_IN
    from core.specialists import SPECIALISTS

    lines = _lines()
    assert f"{len(SPECIALISTS)} specialists" in lines["Specialists"]
    assert f"{len(TRACKS)} tracks" in lines["Night School"]
    assert f"{len(BUILT_IN)} plans" in lines["Builder"]
    assert "pH" in lines["Aquaponics greenhouse scientist and manager"]


def test_mia_homestead_is_claimed_only_when_it_is_part_of_her():
    there = (ROOT / "homestead" / "drivers" / "simulator.py").exists()
    assert ("MIA Homestead" in _lines()["Aquaponics greenhouse scientist and manager"]) == there


def test_a_specialty_whose_source_breaks_is_left_out_not_claimed(monkeypatch):
    import core.specialists

    monkeypatch.setattr(core.specialists, "SPECIALISTS", None)  # len(None) raises inside its reader
    lines = _lines()
    assert "Specialists" not in lines and "Builder" in lines  # the rest still say themselves


def test_painting_is_ready_only_when_the_engine_runs(monkeypatch):
    import core.art_studio

    monkeypatch.setattr(core.art_studio, "status", lambda context: {"engine": {"available": False}})
    assert "once its art engine is set up" in _lines()["Painter"]
    monkeypatch.setattr(core.art_studio, "status", lambda context: {"engine": {"available": True}})
    assert "describe a scene" in _lines()["Painter"]


def test_their_own_grow_numbers_join_when_there_are_some():
    lab = SimpleNamespace(batches=[SimpleNamespace(status="Growing"), SimpleNamespace(status="Harvested")],
                          experiments=[SimpleNamespace(status="Running")])
    line = _lines(SimpleNamespace(grow_lab=lab))["Aquaponics greenhouse scientist and manager"]
    assert "1 batch growing, 1 experiment running" in line


def test_a_directive_written_to_her_is_said_in_her_own_voice():
    said = capabilities._first_person("Build yourself into a top-tier AI. Then do more.")
    assert said == "build myself into a top-tier AI"
    assert capabilities._soft("Software and AI engineering") == "software and AI engineering"


def test_the_answer_opens_plainly_and_lists_every_specialty():
    said = specialties(SimpleNamespace())
    assert said.startswith("Here's what I'm trained for and built to do.")
    assert all(f"{title}:" in said for title, _ in specialty_list(SimpleNamespace()))


@pytest.fixture(scope="module")
def registry():
    """The desktop's real tool registry."""
    from tests.assistant_registry import build_desktop_registry

    return build_desktop_registry()


def test_the_questions_reach_the_specialties_tool(registry):
    for q in ("What are you trained for?", "What are your specialties?", "What's your expertise?",
              "what are you programmed to do"):
        assert registry.direct_lookup(q).name == "get_specialties", q
    assert registry.direct_lookup("What can you do?").name == "what_can_you_do"  # the apps overview stays its own
