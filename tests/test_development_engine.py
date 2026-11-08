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
waiting while cheap foundations remain, the checks with each step, and the catalog rules that hold it. And the budget
read from their own build targets when they don't give one. The flock and the compost by the same rules (a coop and
a feed bin before hens, eggs before selling them; slow compost only when nothing quicker), a step's share of the work
it unlocks, and what a flock in the records says exists. The year: preserving in summer, spring prepared in winter,
food sold only after the cottage-food rules, a payoff months away worth less than one now. The rest are
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
    flush = DevelopmentProfile(budget=2000, month=6, have=frozenset({"water", "greenhouse_site"}))  # water and a site
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
    assert have == {"Greenhouse": "your assets", "Raised garden bed": "your grow lab",
                    "Level and drain the greenhouse site": "needed for greenhouse"}  # a greenhouse stands on its site
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
    seed-starting infrastructure, said as step 1 of the path that ends in selling. (In March: in summer the better move
    is preserving the harvest, and that's tested too.)"""
    step = de.next_step(DevelopmentProfile(month=3), de.homestead_catalog(), _FOUNDATIONS)
    assert step["recommend"]["id"] == "seed_cups" and step["goal"]["id"] == "plant_sales"
    ids = [s["id"] for s in step["path"]]
    assert ids[-1] == "plant_sales" and ids.index("first_seedlings") < ids.index("sales_stand")
    assert {"seed_cups", "seedling_shelf", "seed_mix"} <= set(ids)


def test_made_and_upcycled_come_before_bought():
    goal = next(c for c in de.homestead_catalog() if c.id == "plant_sales")
    ids = [s.id for s in de.path_to(goal, DevelopmentProfile(month=7), de.homestead_catalog(), _FOUNDATIONS)]
    assert "seed_cups" in ids and "cell_trays" not in ids
    assert "seedling_shelf" in ids and "wire_shelf" not in ids
    checks = de.next_step(DevelopmentProfile(month=3), de.homestead_catalog(), _FOUNDATIONS)["checks"]
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
    early = de.next_step(DevelopmentProfile(month=2), de.homestead_catalog(), _FOUNDATIONS)["checks"]
    assert any(c["check"] == "timing" and "March to May" in c["line"] for c in early)


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


# --- the budget from their own targets ------------------------------------

def _budget_store(targets, spent):
    """A budget store with these (category, monthly amount, entity id) targets and this month's spending by category."""
    return SimpleNamespace(
        all_budget_targets=lambda: [SimpleNamespace(category=c, monthly_amount=a, entity_id=e) for c, a, e in targets],
        total_expenses_by_category=lambda start, end, entity_id=None: dict(spent))


def test_the_budget_is_what_is_left_of_their_build_targets_this_month():
    store = _budget_store([("Building Materials", 150, ""), ("Tools & Equipment", 50, ""),
                           ("Building Materials", 999, "biz1"), ("Groceries", 400, "")],
                          {"Building Materials": 70, "Groceries": 300})
    assert de.homestead_budget(SimpleNamespace(budget=store)) == 130.0  # 150 + 50 - 70; a business's and groceries' aside
    assert de.development_profile(SimpleNamespace(budget=store)).budget == 130.0
    assert de.development_profile(SimpleNamespace(budget=store), budget=300).budget == 300  # what they say wins


def test_no_build_target_means_no_budget_and_overspent_means_zero():
    assert de.homestead_budget(SimpleNamespace(budget=_budget_store([("Groceries", 400, "")], {}))) is None
    assert de.homestead_budget(SimpleNamespace()) is None
    over = _budget_store([("Building Materials", 100, "")], {"Building Materials": 160})
    assert de.homestead_budget(SimpleNamespace(budget=over)) == 0.0


def test_the_spoken_plan_says_which_budget_it_weighed():
    store = _budget_store([("Building Materials", 150, "")], {})
    p = de.plan(SimpleNamespace(budget=store), month=7)
    assert p["budget"] == 150 and p["budget_from"] == "your build budget"
    assert de.describe(p).endswith("Weighed against the $150 left in your build budget this month.")
    assert de.plan(SimpleNamespace(), budget=80, month=7)["budget_from"] == "you"



# --- the flock and the compost, the same deep rules (2026-11-08) ---------

def test_eggs_are_sold_only_after_a_coop_a_feed_bin_and_a_laying_flock():
    cat = de.homestead_catalog()
    goal = next(c for c in cat if c.id == "egg_sales")
    ids = [s.id for s in de.path_to(goal, DevelopmentProfile(month=4), cat, _FOUNDATIONS)]
    assert ids.index("chickens") < ids.index("flock") and ids.index("feed_bin") < ids.index("flock")
    assert ids.index("flock") < ids.index("sales_stand") < ids.index("egg_sales")


def test_with_the_coop_built_in_spring_the_next_step_is_toward_the_flock():
    step = de.next_step(DevelopmentProfile(month=5), de.homestead_catalog(), _FOUNDATIONS | {"chickens"})
    assert step["recommend"]["id"] == "feed_bin" and step["goal"]["id"] == "flock"


def test_a_step_earns_only_its_share_of_the_work_it_unlocks():
    """A $25 feed bin is a sliver of the way to a flock that also needs a $300 coop."""
    cat = de.homestead_catalog()
    by_id = {c.id: c for c in cat}
    alone = de.compounding_value(by_id["feed_bin"], cat)
    with_coop = de.compounding_value(by_id["feed_bin"], cat, done=frozenset({"chickens"}))
    assert alone < 0.1 * by_id["flock"].benefit < with_coop


def test_a_slow_provider_is_used_only_when_nothing_quicker_meets_the_need():
    cat = de.homestead_catalog()
    goal = next(c for c in cat if c.id == "first_seedlings")
    ids = [s.id for s in de.path_to(goal, DevelopmentProfile(month=3), cat, _FOUNDATIONS)]
    assert "seed_mix" in ids and "finished_compost" not in ids  # months of curing would miss the season
    no_bag = [c for c in cat if c.id != "seed_mix"]
    ids = [s.id for s in de.path_to(goal, DevelopmentProfile(month=3), no_bag, _FOUNDATIONS)]
    assert "finished_compost" in ids


def test_a_flock_means_a_coop_and_a_feed_bin_but_water_means_no_rain_barrel():
    ctx = SimpleNamespace(maintenance=SimpleNamespace(all_assets=lambda: [SimpleNamespace(name="Laying hens flock"),
                                                                          SimpleNamespace(name="Greenhouse")]))
    have = {h["name"]: h["found_in"] for h in de.plan(ctx, month=5)["have"]}
    assert have["Chicken coop and run"] == "needed for start a small laying flock"
    assert have["A rodent-proof feed bin"] == "needed for start a small laying flock"
    assert "Rain-barrel water collection" not in have  # a greenhouse's water could come from a hose



# --- the year: preserving in summer, food sold only after the rules (2026-11-08) ---

def test_in_summer_the_harvest_is_preserved_and_in_winter_spring_is_prepared():
    cat = de.homestead_catalog()
    assert de.next_step(DevelopmentProfile(month=7), cat, _FOUNDATIONS)["recommend"]["id"] == "canning_setup"
    assert de.next_step(DevelopmentProfile(month=3), cat, _FOUNDATIONS)["recommend"]["id"] == "seed_cups"


def test_food_is_sold_only_after_the_cottage_food_rules_are_checked_and_only_once_there_is_food():
    cat = de.homestead_catalog()
    for c in cat:
        if c.sector == "business" and c.id in ("egg_sales", "preserve_sales"):
            assert de.FOOD_SALE_TAG in c.requires, c.id
        if de.FOOD_SALE_TAG in c.provides:
            assert c.requires & de.PROOF_TAGS, c.id  # the check comes once there's something to sell
    jars = _FOUNDATIONS | {"canning_setup", "pantry_stock", "sales_stand"}
    step = de.next_step(DevelopmentProfile(month=9), cat, jars)
    assert step["recommend"]["id"] == "cottage_food_check" and step["goal"]["id"] == "preserve_sales"


def test_a_payoff_months_away_is_worth_less_than_one_now():
    """In September, preserves already put up beat seedling starts that can't sell until spring."""
    assert de._months_until((3, 4, 5), 9) == 6 and de._months_until((3, 4, 5), 4) == 0 and de._months_until((), 1) == 0
