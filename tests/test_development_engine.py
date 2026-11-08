"""
tests.test_development_engine
===============================

The strategic layer (core/development_engine.py, DEC-0144). The heart of it is the **Zero-to-Something benchmark**
(the handoffs' §10/§12 acceptance test, made executable): someone with a small budget, few tools and an objective
should get a plan that assesses the start honestly, prioritises low-cost/high-unlock projects, respects dependencies
and season, and names a sensible logical next step — never "build the greenhouse first." The rest are unit tests on
the scoring, the dependency gate, compounding value and the defensive profile reader.
"""

from types import SimpleNamespace

from core import development_engine as de
from core.development_engine import Candidate, DevelopmentProfile
from core.environment import SIMULATED


# --- unit: the pieces -------------------------------------------------------

def test_a_profile_is_a_simulated_planning_artifact_never_real():
    assert DevelopmentProfile().environment == SIMULATED


def test_the_dependency_gate_blocks_until_its_prerequisite_is_done():
    cat = de.homestead_catalog()
    drip = next(c for c in cat if c.id == "drip_irrigation")
    empty = DevelopmentProfile(budget=500, month=6)
    ok, missing = de.available(drip, empty, cat)
    assert not ok and "water" in missing
    # once the rain barrel is done, water is on hand and drip opens up
    ok2, _ = de.available(drip, empty, cat, done={"rain_barrel"})
    assert ok2


def test_compounding_value_rewards_what_a_project_unlocks():
    cat = de.homestead_catalog()
    compost = next(c for c in cat if c.id == "compost_bin")
    drip = next(c for c in cat if c.id == "drip_irrigation")
    # compost unlocks the bed and the greenhouse; drip unlocks nothing — compost compounds, drip doesn't
    assert de.compounding_value(compost, cat) > 0
    assert de.compounding_value(drip, cat) == 0


def test_safety_critical_candidates_carry_a_professional_flag():
    cat = de.homestead_catalog()
    greenhouse = next(c for c in cat if c.id == "greenhouse")
    s = de.score(greenhouse, DevelopmentProfile(budget=2000, month=6), cat)
    assert s["needs_professional"] is True


# --- the Zero-to-Something benchmark ---------------------------------------

def _starter_profile():
    """$200, no tools, spring, with a self-sufficiency objective — the handoffs' canonical starting position."""
    return DevelopmentProfile(budget=200, hours_per_week=10, month=4,
                              objectives=("Homestead independence",))


def test_zero_to_something_prioritises_cheap_high_unlock_not_the_greenhouse():
    cat = de.homestead_catalog()
    rows = de.ranked(_starter_profile(), cat)
    top = rows[0]
    # the greenhouse ($800) and chickens ($300) are out of budget and must not top the list
    assert top["id"] in {"compost_bin", "rain_barrel", "raised_bed"}
    greenhouse = next(r for r in rows if r["id"] == "greenhouse")
    assert greenhouse["affordable"] is False
    assert rows.index(greenhouse) > rows.index(top)  # it sinks below what's doable


def test_zero_to_something_next_step_is_doable_and_explained():
    step = de.next_step(_starter_profile(), de.homestead_catalog())
    assert step["kind"] == "do"
    rec = step["recommend"]
    assert rec["affordable"] and rec["available"] and rec["in_season"]
    assert rec["entry_cost"] <= 200
    assert step["reason"] and rec["name"].split()[0].lower() in step["reason"].lower()


def test_season_is_respected_in_the_next_step():
    cat = de.homestead_catalog()
    # the cold frame is an autumn job; in spring it must not be the pick over the spring-appropriate options
    step = de.next_step(_starter_profile(), cat)  # month=4 (spring)
    assert step["recommend"]["id"] != "cold_frame"


def test_the_plan_adapts_as_projects_get_done():
    cat = de.homestead_catalog()
    prof = DevelopmentProfile(budget=200, month=6)
    # after water + compost + a bed exist, the next step moves on to what they unlocked
    step = de.next_step(prof, cat, done={"rain_barrel", "compost_bin", "raised_bed"})
    assert step["recommend"]["id"] not in {"rain_barrel", "compost_bin", "raised_bed"}


def test_a_bigger_budget_brings_the_greenhouse_into_reach():
    cat = de.homestead_catalog()
    flush = DevelopmentProfile(budget=2000, month=6, have=frozenset({"water"}))  # water already on hand
    g = de.score(next(c for c in cat if c.id == "greenhouse"), flush, cat)
    assert g["affordable"] and g["available"]


# --- the defensive real-state reader ---------------------------------------

def test_the_profile_reader_degrades_quietly_on_a_bare_context():
    # no stores wired at all -> an empty-but-valid profile, never a crash
    prof = de.development_profile(SimpleNamespace())
    assert isinstance(prof, DevelopmentProfile) and prof.environment == SIMULATED


def test_the_profile_reader_pulls_from_the_stores_it_finds():
    ctx = SimpleNamespace(
        materials=SimpleNamespace(all_materials=lambda: [SimpleNamespace(name="Cedar")]),
        skills=SimpleNamespace(all_skills=lambda: [SimpleNamespace(name="Carpentry")]),
        intents=SimpleNamespace(all_intents=lambda: [SimpleNamespace(name="Homestead independence")]),
    )
    prof = de.development_profile(ctx)
    assert "cedar" in prof.have and "carpentry" in prof.skills
    assert "Homestead independence" in prof.objectives
