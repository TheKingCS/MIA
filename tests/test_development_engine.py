"""
tests.test_development_engine
===============================

The strategic layer (core/development_engine.py, DEC-0144). The heart of it is the **Zero-to-Something benchmark**
(the handoffs' §10/§12 acceptance test, made executable): someone with a small budget, few tools and an objective
should get a plan that assesses the start honestly, prioritises low-cost/high-unlock projects, respects dependencies
and season, and names a sensible logical next step — never "build the greenhouse first." Then the plan as the
Greenhouse page and the get_homestead_next_step tool show it: what they already have read from their records, why
each option isn't ready, a budget only from money words. Then the deep next steps: the infrastructure before
the payoff (selling starts only through cups, a shelf, a first batch and a stand), made before bought, a big build
waiting while cheap foundations remain, the checks with each step, and the catalog rules that hold it. The rest are
unit tests on
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


# --- the plan as the screen and the tool show it (DEC-0144, DEC-0125) ------

def test_an_unknown_budget_is_never_treated_as_zero():
    cat = de.homestead_catalog()
    s = de.score(next(c for c in cat if c.id == "compost_bin"), DevelopmentProfile(month=4), cat)
    assert DevelopmentProfile().budget is None and s["affordable"] is True


def test_what_they_already_have_is_read_from_their_records_and_left_out():
    ctx = SimpleNamespace(maintenance=SimpleNamespace(all_assets=lambda: [SimpleNamespace(name="Walipini Greenhouse")]),
                          grow_lab=SimpleNamespace(systems=["Raised bed 1"]))
    p = de.plan(ctx, month=6)
    have = {h["name"]: h["found_in"] for h in p["have"]}
    assert have == {"Greenhouse": "your assets", "Raised garden bed": "your grow lab"}
    assert not {o["id"] for o in p["options"]} & {"greenhouse", "raised_bed"}
    assert p["environment"] == SIMULATED


def test_each_option_says_why_it_is_not_ready_yet():
    cat = de.homestead_catalog()
    prof = DevelopmentProfile(budget=100, month=1)
    by_id = {c.id: c for c in cat}
    why = {r["id"]: de._why_not(r, prof, by_id) for r in de.ranked(prof, cat)}
    assert why["raised_bed"] == "best begun March to May"
    assert why["chickens"].startswith("about $300, more than the $100")
    assert why["plant_sales"] == "needs grown seedlings and sales outlet first"


def test_the_spoken_plan_names_the_move_and_asks_for_a_budget_when_none_was_given():
    said = de.describe(de.plan(SimpleNamespace(), month=4))
    assert said.startswith("Next on the homestead: Three-bay compost bin")
    assert said.endswith("Tell me your budget and I'll weigh it in.")
    assert "budget" not in de.describe(de.plan(SimpleNamespace(), budget=200, month=4)).split("After that")[-1]


def test_a_budget_is_read_from_money_words_only():
    from core.assistant_homestead_actions import _budget_from

    assert [_budget_from(x) for x in ("with $1,200", "300 bucks", "a budget of 150", "the next 3 projects", 45)] == \
        [1200.0, 300.0, 150.0, None, 45.0]


def test_the_greenhouse_page_carries_the_plan(tmp_path):
    from core.grow_lab import GrowLab
    from core.web_grow import grow_page

    ctx = SimpleNamespace(maintenance=None, data_logger=None)
    ctx.grow_lab = GrowLab(ctx, data_dir=tmp_path)
    page = grow_page(ctx)
    assert page["next"]["next"]["name"] and page["next"]["options"]


# --- deep next steps: the infrastructure before the payoff (Zac, 2026-11-08) ---

_FOUNDATIONS = frozenset({"raised_bed", "rain_barrel", "compost_bin"})


def test_selling_starts_is_reached_through_the_infrastructure_never_jumped_to():
    """Zac's example: with beds in and nothing else, the next step is never selling starts; it's the first piece of
    seed-starting infrastructure, said as step 1 of the path that ends in selling."""
    step = de.next_step(DevelopmentProfile(month=7), de.homestead_catalog(), _FOUNDATIONS)
    assert step["recommend"]["id"] == "seed_cups" and step["goal"]["id"] == "plant_sales"
    ids = [s["id"] for s in step["path"]]
    assert ids[-1] == "plant_sales" and ids.index("first_seedlings") < ids.index("sales_stand")
    assert {"seed_cups", "seedling_shelf", "seed_mix"} <= set(ids)


def test_made_and_upcycled_come_before_bought():
    goal = next(c for c in de.homestead_catalog() if c.id == "plant_sales")
    ids = [s.id for s in de.path_to(goal, DevelopmentProfile(month=7), de.homestead_catalog(), _FOUNDATIONS)]
    assert "seed_cups" in ids and "cell_trays" not in ids
    assert "seedling_shelf" in ids and "wire_shelf" not in ids
    checks = de.next_step(DevelopmentProfile(month=7), de.homestead_catalog(), _FOUNDATIONS)["checks"]
    assert any(c["check"] == "made_first" and c["ok"] for c in checks)


def test_a_big_build_waits_while_cheap_foundations_remain_even_without_a_budget():
    """An unknown budget never makes an $800 greenhouse look cheap: value is weighed against money and hours."""
    step = de.next_step(DevelopmentProfile(month=7), de.homestead_catalog(), _FOUNDATIONS)
    assert step["recommend"]["id"] != "greenhouse"


def test_each_recommendation_carries_its_checks():
    seedlings = _FOUNDATIONS | {"seed_cups", "seedling_shelf", "seed_mix", "first_seedlings", "sales_stand"}
    step = de.next_step(DevelopmentProfile(month=4), de.homestead_catalog(), seedlings)
    assert step["recommend"]["id"] == "plant_sales"
    checks = {c["check"]: c for c in step["checks"]}
    assert checks["ready"]["ok"] and checks["season"]["ok"] and checks["start_small"]["ok"]
    assert checks["budget"]["ok"] is None  # no budget given: said, not judged
    early = de.next_step(DevelopmentProfile(month=7), de.homestead_catalog(), _FOUNDATIONS)["checks"]
    assert any(c["check"] == "timing" and "February to April" in c["line"] for c in early)


def test_the_catalog_never_lets_selling_skip_proof_or_a_place_to_sell():
    """The rules behind the advice, held for every candidate: a revenue step needs proof and an outlet; an outlet is
    built only after proof; everything needed has a way to get it; every candidate has a path from scratch."""
    cat = de.homestead_catalog()
    provided = set().union(*(c.provides for c in cat))
    for c in cat:
        if c.sector == "business":
            assert c.requires & de.PROOF_TAGS and c.requires & de.OUTLET_TAGS, c.id
        if c.provides & de.OUTLET_TAGS:
            assert c.requires & de.PROOF_TAGS, c.id
        assert c.requires <= provided, c.id
        assert de.path_to(c, DevelopmentProfile(month=4), cat) is not None, c.id


def test_proof_and_supplies_are_read_from_their_records():
    ctx = SimpleNamespace(grow_lab=SimpleNamespace(systems=[], batches=[SimpleNamespace(crop="Tomato")]),
                          materials=SimpleNamespace(all_materials=lambda: [SimpleNamespace(name="Potting mix")]))
    have = {h["name"]: h["found_in"] for h in de.plan(ctx, month=4)["have"]}
    assert have["Start a first batch of seedlings"] == "your grow lab"
    assert have["Seed-starting mix"] == "your workshop shelf"
